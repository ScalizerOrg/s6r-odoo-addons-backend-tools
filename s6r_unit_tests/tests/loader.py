# Copyright 2023 Scalizer (<https://www.scalizer.fr>)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo.tests import loader
import logging
from .runner import skip_unit_test

_logger = logging.getLogger(__name__)
run_suite_origin = loader.run_suite


def run_suite(suite, module_name=None, global_report=None):
    suite._tests = list(filter(lambda t: not skip_unit_test(t), suite._tests))
    return run_suite_origin(suite, module_name)


loader.run_suite = run_suite
