# Copyright 2023 Scalizer (<https://www.scalizer.fr>)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo.tests.result import OdooTestResult
import logging

_logger = logging.getLogger(__name__)
starTest_origin = OdooTestResult.startTest
addSubTest_origin = OdooTestResult.addSubTest


def get_excluded_tests():
    """
    Returns a list of dict of excluded tests.
    If class value is 'all', all unit tests of the module are skipped.
    If method value is 'all', all unit tests of the class are skipped.
        [
            {'module': 'auth_totp', 'class': 'TestTOTP', 'method': 'test_totp'},
            {'module': 'website', 'class': 'Crawler', 'method': 'all'},
        ]
    """
    return []


OdooTestResult.get_excluded_tests = get_excluded_tests


def skip_unit_test(test):
    excluded_tests = OdooTestResult.get_excluded_tests()
    for excluded_test in excluded_tests:
        if hasattr(test, 'test_module') and excluded_test['module'] == test.test_module:
            if excluded_test['class'] == 'all':
                return True
            elif excluded_test['class'] == test.test_class:
                if excluded_test['method'] in ['all', test._testMethodName]:
                    return True


def startTest(self, test):
    if skip_unit_test(test):
        self.log(logging.INFO, 'Skipping %s ...', self.getDescription(test), test=test)
        return
    starTest_origin(self, test)


def addSubTest(self, test, subtest, err):
    if skip_unit_test(test):
        self.log(logging.INFO, 'Skipping %s ...', self.getDescription(test), test=test)
        return
    addSubTest_origin(self, test, subtest, err)


OdooTestResult.startTest = startTest
OdooTestResult.addSubTest = addSubTest
