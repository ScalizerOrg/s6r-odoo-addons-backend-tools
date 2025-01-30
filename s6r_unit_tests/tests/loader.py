# Copyright 2023 Scalizer (<https://www.scalizer.fr>)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from odoo.tests import loader
import logging
from .runner import skip_unit_test

_logger = logging.getLogger(__name__)
run_suite_origin = loader.run_suite


def run_suite(suite):
    tests_to_skip = list(filter(lambda t: skip_unit_test(t), suite._tests))
    for test in tests_to_skip:
        _logger.info(f"Skipping unit test: {test}")
        suite._tests.remove(test)
    return run_suite_origin(suite)

loader.run_suite = run_suite
