# Copyright 2026 Scalizer (<https://www.scalizer.fr>)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
"""Restrict the unit tests to the modules impacted by the current branch.

The impacted modules are computed from ``git diff <base>...HEAD`` on the
project repository, then injected into ``config['test_tags']``. Odoo reads
this option each time it builds a test suite (``odoo.tests.loader.make_suite``),
so every test suite built after this module is imported is filtered natively,
before any ``setUpClass`` is executed.

Scope of a branch:

* the modules whose files changed (submodule bumps included);
* the repository modules depending on them, recursively (reverse dependencies);
* the direct ``depends`` of the changed modules, i.e. the standard / OCA modules
  they override, except ``IGNORED_DEPENDS``.

A module whose changes are limited to its ``tests/`` directory does not
propagate to its reverse dependencies nor to its ``depends``.

Activation (environment variables):

* ``S6R_UT_SCOPE``: ``1`` forces the targeted mode, ``0`` disables it.
  When unset, it is enabled on Odoo.sh development builds only
  (``ODOO_STAGE=dev``).
* ``S6R_UT_BASE_REF``: git reference to diff against. When unset, the first
  existing reference of ``DEFAULT_BASE_REFS`` is used.
* ``S6R_UT_REPO``: path of the project repository. When unset, it is the git
  superproject of this module (or its own repository).
* ``S6R_UT_SCOPE_DEPENDS``: ``0`` to skip the direct ``depends`` of the
  changed modules.

The full suite is run whenever the scope cannot be computed reliably (no git,
unknown base reference, changes in ``FULL_SUITE_FILES``), or when the last
commit message contains ``FULL_SUITE_MARKER``.
"""

import ast
import logging
import os
import subprocess

_logger = logging.getLogger(__name__)

DEFAULT_BASE_REFS = [
    "origin/staging",
    "origin/main",
    "origin/master",
    "staging",
    "main",
    "master",
]
FULL_SUITE_MARKER = "[full-tests]"
FULL_SUITE_FILES = {"requirements.txt"}
SUBMODULE_MODE = "160000"
# Fallback scope when no module changed: keep a minimal sanity run.
EMPTY_SCOPE = {"s6r_unit_tests"}
# Framework modules nearly every module depends on: testing them for each
# branch would cancel the benefit of the targeted mode. Their regressions are
# caught by the full suite (staging, daily testing branch).
IGNORED_DEPENDS = {"base", "web"}


class ScopeUnavailable(Exception):
    """Raised when the targeted scope cannot be computed reliably."""


def _git(repo, *args):
    """Run a git command in ``repo`` and return its stripped output.

    :param str repo: path of the git working tree
    :param args: git arguments
    :return: command output
    :rtype: str
    :raises ScopeUnavailable: if git fails
    """
    try:
        return subprocess.check_output(
            ["git", "-C", repo, *args], text=True, stderr=subprocess.DEVNULL, timeout=60
        ).strip()
    except (OSError, subprocess.SubprocessError) as error:
        raise ScopeUnavailable(f"git {' '.join(args)} failed in {repo}: {error}") from error


def find_repo_root(start):
    """Return the project repository containing ``start``.

    When ``start`` lives in a git submodule, the superproject is returned.

    :param str start: path inside the repository
    :return: absolute path of the repository root
    :rtype: str
    """
    superproject = _git(start, "rev-parse", "--show-superproject-working-tree")
    return superproject or _git(start, "rev-parse", "--show-toplevel")


def resolve_base_ref(repo, candidates):
    """Return the first reference of ``candidates`` existing in ``repo``.

    :param str repo: path of the git working tree
    :param list[str] candidates: references to try, in order
    :return: the existing reference
    :rtype: str
    :raises ScopeUnavailable: if none exists
    """
    for ref in candidates:
        try:
            _git(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
            return ref
        except ScopeUnavailable:
            continue
    raise ScopeUnavailable(f"none of the base references {candidates} exists in {repo}")


def find_manifests(root):
    """Return the modules found under ``root`` with their dependencies.

    Modules are searched at any depth (submodules included), without
    descending into a module directory.

    :param str root: directory to scan
    :return: ``{module_name: (relative_path, [depends])}``
    :rtype: dict
    """
    modules = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith((".", "__"))]
        if "__manifest__.py" not in filenames:
            continue
        dirnames[:] = []
        try:
            with open(os.path.join(dirpath, "__manifest__.py"), encoding="utf-8") as manifest_file:
                manifest = ast.literal_eval(manifest_file.read())
        except (OSError, SyntaxError, ValueError):
            _logger.warning("UT scope: cannot parse the manifest of %s", dirpath)
            continue
        modules[os.path.basename(dirpath)] = (
            os.path.relpath(dirpath, root),
            list(manifest.get("depends", [])),
        )
    return modules


def changed_files(repo, base_ref, head="HEAD"):
    """Return the files changed between the merge base of ``base_ref`` and ``head``.

    Submodule bumps are expanded into the files changed inside the submodule.
    If the submodule commits are not available, the submodule directory itself
    is returned so that all its modules are considered as changed.

    :param str repo: path of the git working tree
    :param str base_ref: reference to diff against
    :param str head: reference of the branch
    :return: paths relative to ``repo``
    :rtype: set[str]
    """
    files = set()
    raw = _git(repo, "diff", "--raw", "--no-abbrev", "--no-renames", f"{base_ref}...{head}")
    for line in raw.splitlines():
        meta, path = line.split("\t", 1)
        old_mode, new_mode, old_sha, new_sha = meta.lstrip(":").split()[:4]
        if SUBMODULE_MODE not in (old_mode, new_mode):
            files.add(path)
            continue
        sub_repo = os.path.join(repo, path)
        try:
            if old_mode != SUBMODULE_MODE or new_mode != SUBMODULE_MODE:
                raise ScopeUnavailable("submodule added or removed")
            sub_files = _git(sub_repo, "diff", "--name-only", old_sha, new_sha)
            files.update(os.path.join(path, f) for f in sub_files.splitlines())
        except ScopeUnavailable:
            files.add(os.path.join(path, ""))
    return files


def compute_scope(files, modules, with_depends=True):
    """Return the modules whose tests must run for the given changed files.

    :param set[str] files: changed paths, relative to the repository root
    :param dict modules: result of :func:`find_manifests`
    :param bool with_depends: include the direct ``depends`` of the changed modules
    :return: module names
    :rtype: set[str]
    :raises ScopeUnavailable: if a file requires the full suite
    """
    if FULL_SUITE_FILES & {os.path.basename(f) for f in files}:
        raise ScopeUnavailable(f"changes in {FULL_SUITE_FILES} require the full suite")

    touched = set()  # any change in the module
    propagating = set()  # change outside tests/: impacts dependents
    for name, (path, _depends) in modules.items():
        prefix = path.rstrip("/") + "/"
        for changed in files:
            if changed.startswith(prefix):
                touched.add(name)
                if not changed[len(prefix) :].startswith("tests/"):
                    propagating.add(name)
                    break
            elif prefix.startswith(changed) and changed.endswith("/"):
                # whole directory changed (unavailable submodule bump)
                touched.add(name)
                propagating.add(name)
                break

    scope = set(touched)
    impacted = set(propagating)
    while True:
        dependents = {
            name for name, (_path, depends) in modules.items() if impacted & set(depends)
        } - impacted
        if not dependents:
            break
        impacted |= dependents
    scope |= impacted
    if with_depends:
        for name in propagating:
            scope.update(set(modules[name][1]) - IGNORED_DEPENDS)
    return scope


def build_test_tags(scope, existing=None):
    """Combine ``scope`` with the existing ``test_tags`` option.

    Exclusions are kept. Inclusions without module are restricted to the
    scope (``tag`` becomes ``tag/module``), inclusions with a module are kept
    when the module is in the scope.

    :param set[str] scope: module names
    :param str existing: current value of ``test_tags``
    :return: the new ``test_tags`` value
    :rtype: str
    """
    specs = [s.strip() for s in (existing or "").split(",") if s.strip()]
    excludes = [s for s in specs if s.startswith("-")]
    includes = [s.lstrip("+") for s in specs if not s.startswith("-")]
    if not includes:
        includes = ["standard"]
    result = []
    for spec in includes:
        if "/" in spec:
            module = spec.split("/", 1)[1].split(":", 1)[0].split(".", 1)[0]
            if module in scope:
                result.append(spec)
            continue
        tag, sep, rest = spec.partition(":")
        result.extend(f"{tag}/{module}{sep}{rest}" for module in sorted(scope))
    return ",".join(result + excludes)


def is_enabled(environ=None):
    """Tell whether the targeted mode must be used.

    :param dict environ: environment, ``os.environ`` by default
    :rtype: bool
    """
    environ = os.environ if environ is None else environ
    forced = environ.get("S6R_UT_SCOPE")
    if forced is not None:
        return forced.strip().lower() in ("1", "true", "yes")
    return environ.get("ODOO_STAGE") == "dev"


def apply_scope(config, environ=None):
    """Restrict ``config['test_tags']`` to the modules impacted by the branch.

    Does nothing (full suite) when the targeted mode is disabled or the scope
    cannot be computed.

    :param config: Odoo configuration manager
    :param dict environ: environment, ``os.environ`` by default
    :return: the applied ``test_tags``, or ``None`` when the full suite runs
    :rtype: str | None
    """
    environ = os.environ if environ is None else environ
    if not is_enabled(environ):
        return None
    try:
        repo = environ.get("S6R_UT_REPO") or find_repo_root(os.path.dirname(os.path.abspath(__file__)))
        if FULL_SUITE_MARKER in _git(repo, "log", "-1", "--format=%B"):
            _logger.info("UT scope: %s found in the last commit, running the full suite", FULL_SUITE_MARKER)
            return None
        base_ref = environ.get("S6R_UT_BASE_REF")
        base_ref = resolve_base_ref(repo, [base_ref] if base_ref else DEFAULT_BASE_REFS)
        files = changed_files(repo, base_ref)
        scope = compute_scope(
            files, find_manifests(repo), with_depends=environ.get("S6R_UT_SCOPE_DEPENDS", "1") != "0"
        )
    except ScopeUnavailable as error:
        _logger.warning("UT scope: %s, running the full suite", error)
        return None
    if not scope:
        scope = set(EMPTY_SCOPE)
    test_tags = build_test_tags(scope, config["test_tags"])
    config["test_tags"] = test_tags
    _logger.info(
        "UT scope: %d changed file(s) since %s, %d module(s) to test: %s",
        len(files),
        base_ref,
        len(scope),
        ", ".join(sorted(scope)),
    )
    _logger.info("UT scope: test_tags=%s", test_tags)
    return test_tags
