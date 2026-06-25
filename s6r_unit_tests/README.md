Scalizer Unit Tests
===================

This module helps to manage unit tests on Odoo.sh platform.

This is a technical module. This requires a custom module to inherit it.

## Table of contents

* [Usage](#usage)
  * [Skip failing python unit tests](skip-failing-python-unit-tests)
  * [Trim the always-invisible-fields whitelist](trim-the-always-invisible-fields-whitelist)
  * [Avoid warnings on fields](avoid-warnings-on-fields)
* [Contributors](#contributors)
* [Maintainers](#maintainers)

## Usage

### Create a custom module

Create a custom module (s6r_my_project_unit_tests for example) add `s6r_unit_tests` in the dependencies. 

In the manifest, set `'auto_install': True`


### Skip failing python unit tests

In the custom module, in `tests` directory, add a file `runner.py` and override the `get_excluded_tests` function like in the example bellow.

- `class` can take the value `all` to skip all the test classes of the module.
- `method` can take the value `all` to skip all the test methods of the class.

```python
from odoo.addons.s6r_unit_tests.tests.runner import OdooTestResult
def get_excluded_tests():
    return [
        {'module': 'auth_totp', 'class': 'TestTOTP', 'method': 'test_totp'},
        {'module': 'website', 'class': 'Crawler', 'method': 'all'},
    ]

OdooTestResult.get_excluded_tests = get_excluded_tests
```


### Trim the always-invisible-fields whitelist

`s6r_unit_tests` patches the standard `TestInvisibleField.test_uncommented_invisible_field` test (see `tests/test_patch_invisible_fields.py`). The patched test downgrades the standard / enterprise modules listed in the module-level `ONLY_LOG_MODULES` tuple from errors to log entries, and conversely raises an error for any whitelisted module that no longer has any uncommented always-invisible field:

```
Please remove this module names from the white list of this current test: [...]
```

`ONLY_LOG_MODULES` is intentionally exposed as a module-level constant so that project-specific overrides can shrink (or extend) it without touching the upstream module. In your custom module, in the `tests` directory, add a file `test_patch_invisible_fields.py` and reassign `ONLY_LOG_MODULES` like in the example below.

```python
from odoo.addons.s6r_unit_tests.tests import test_patch_invisible_fields

# Modules to drop from the upstream ONLY_LOG_MODULES whitelist for this
# project (e.g. modules that no longer have any uncommented always-invisible
# field in the target version).
REMOVE_FROM_WHITELIST = frozenset({
    'mrp_workorder_expiry',
    'mrp_workorder_iot',
})

test_patch_invisible_fields.ONLY_LOG_MODULES = tuple(
    module
    for module in test_patch_invisible_fields.ONLY_LOG_MODULES
    if module not in REMOVE_FROM_WHITELIST
)
```

To **add** project-specific modules to the whitelist instead, append to the tuple:

```python
test_patch_invisible_fields.ONLY_LOG_MODULES += (
    'my_project_module_with_legit_always_invisible_fields',
)
```

The override must be imported from the custom module's `tests/__init__.py` (guarded by `config["test_enable"]`) so that the reassignment happens before the test runs.


### Avoid warnings on fields

In the custom module, in `models` directory, add a file `logging.py` and override the `get_fields_message_to_skip` function like in the example bellow.

`msg` must be contained in the warning message to skip. 

```python
from odoo.fields import _logger as fields_logger
def get_fields_message_to_skip():
    return [{
        'msg': "overrides existing selection; use selection_add instead",
        'fields': ['res.partner.my_selection_field',
                   'sale.order.other_selection_field']
    }]

fields_logger.get_fields_message_to_skip = get_fields_message_to_skip
```


### Avoid warning or error messages from Chrome browser tests

In the custom module, in `tests` directory, add a file `common.py` and override the `get_console_message_to_skip` function like in the example bellow.

`type` can be 'warning' or 'error'. 
`msg` must be contained in the browser message to skip. 

```python
from odoo.addons.s6r_unit_tests.tests.common import ChromeBrowser
def get_console_message_to_skip(self)::
    return [
        {'type': 'warning',
         'msg': 'Smartlook is stopped'}
    ]

ChromeBrowser.get_console_message_to_skip = get_console_message_to_skip
```

## Authors

* Scalizer

## Contributors

* Michel Perrocheau

## Maintainers

This module is maintained by [Scalizer](https://www.scalizer.fr).

![Scalizer](./static/description/logo.png)


