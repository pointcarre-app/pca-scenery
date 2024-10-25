import io
import os
import logging
from types import TracebackType
import unittest
import pprint

import scenery.common

import django.test
from django.apps import apps as django_apps
from django.conf import settings as django_settings
from django.test.runner import DiscoverRunner
from django.test.utils import get_runner


####################################
# UNITTEST AUGMENTATION
####################################


class CustomTestResult(unittest.TestResult):
    """
    Modify the addError method just to store the type of exception caught
    to be able to have a nice self.assertTestRaises wich has
    the expected_exception as argument
    """

    def addError(
        self,
        test: unittest.TestCase,
        err: (tuple[type[BaseException], BaseException, TracebackType] | tuple[None, None, None]),
    ) -> None:
        super().addError(test, err)
        self.caught_exception = err


class CustomTestCase(unittest.TestCase):
    """This class augment unittest.TestCase for logging puposes"""

    @classmethod
    def log_db(cls):
        # NOTE: this depends on Django
        app_config = django_apps.get_app_config(os.getenv("SCENERY_TESTED_APP_NAME"))
        for model in app_config.get_models():
            cls.logger.debug(f"{model.__name__}: {model.objects.count()} instances.")

    @classmethod
    def setUpClass(cls):
        cls.logger = logging.getLogger(__package__ + ".rehearsal")
        cls.logger.debug(f"{cls.__module__}.{cls.__qualname__}.setUpClass")
        cls.log_db()

    @classmethod
    def tearDownClass(cls):
        cls.logger.debug(f"{cls.__module__}.{cls.__qualname__}.tearDownClass")
        cls.log_db()

    def setUp(self):
        self.logger.debug(f"{self.__module__}.{self.__class__.__qualname__}.setUp")
        self.log_db()

    def tearDown(self):
        self.logger.debug(f"{self.__module__}.{self.__class__.__qualname__}.tearDown")
        self.log_db()


####################################
# DJANGO TESTCASE AUGMENTATION
####################################


class TestCaseOfDjangoTestCase(CustomTestCase):
    """
    This class augments the unittest.TestCase such that it is able to:
    - take a django.test.TestCase and run it via the django test runner
    - make assertions on the result of the django TestCase (sucess ,failures and errors)
    - customize the output of the django.test.TestCase
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.django_loader = unittest.TestLoader()
        TestRunner = get_runner(django_settings)
        cls.django_runner: DiscoverRunner = TestRunner()
        # Customized for better exception catching
        cls.django_runner.test_runner.resultclass = CustomTestResult

        # We customize the django testrunner to avoid confusion in the output and django vs unittest
        cls.django_stream = io.StringIO()

        # Bind the new method
        def overwrite(runner):
            return scenery.common.overwrite_get_runner_kwargs(runner, cls.django_stream)

        cls.django_runner.get_test_runner_kwargs = overwrite.__get__(cls.django_runner)

        cls.logger_django = logging.getLogger(__package__ + ".rehearsal.django")

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.django_stream.close()

    def setUp(self):
        super().setUp()
        # We create a django TestCase (customized) to which we will dynamically add setUpTestData, setUp and test_* functions
        self.django_testcase = type("DjangoTestCase", (django.test.TestCase,), {})

    def tearDown(self):
        super().tearDown()
        msg = self.django_stream.getvalue()
        self.logger_django.debug(f"{scenery.common.pretty_test_name(self)}\n{msg}")
        self.django_stream.seek(0)
        self.django_stream.truncate()

    def run_django_testcase(self):
        suite = unittest.TestSuite()
        tests = self.django_loader.loadTestsFromTestCase(self.django_testcase)

        suite.addTests(tests)
        result = self.django_runner.run_suite(suite)
        self.logger_django.info(f"{repr(self)} {result}")
        return result

    def run_django_test(self, django_test) -> CustomTestResult:
        suite = unittest.TestSuite()
        suite.addTest(django_test)
        result = self.django_runner.run_suite(suite)
        return result

    def assertTestPasses(self, django_test):
        result = self.run_django_test(django_test)
        if result.errors:
            pprint.pprint(result.errors)
        self.assertTrue(result.wasSuccessful(), f"{django_test} was not succesfull")

    def assertTestFails(self, django_test):
        result = self.run_django_test(django_test)
        self.assertFalse(result.wasSuccessful(), f"{django_test} was not succesfull")
        self.assertEqual(len(result.errors), 0, f"{django_test} did not raise any error")

    def assertTestRaises(self, django_test, expected: BaseException):
        result = self.run_django_test(django_test)
        self.assertGreater(len(result.errors), 0, f"{django_test} did not raise any error")
        self.assertIsNotNone(result.caught_exception, f"{django_test} did not caught any exception")
        with self.assertRaises(
            expected, msg=f"{django_test} did not raise expected exception {expected}"
        ):
            raise result.caught_exception[0](result.caught_exception[1])


#####################################
# DISCOVERER AND RUNNER
#####################################


class RehearsalDiscoverer:
    def __init__(self) -> None:
        self.logger = logging.getLogger("rehearsal")
        self.loader = unittest.TestLoader()

    def discover(self, verbosity):
        """Returns a list of pair (test_name, suite), each suite contains a single test"""

        import rehearsal.tests

        tests_discovered = []

        if verbosity >= 1:
            print("Tests discovered:")

        testsuites = self.loader.loadTestsFromModule(rehearsal.tests)

        for testsuite in testsuites:
            for test in testsuite:
                test_name = scenery.common.pretty_test_name(test)

                # Log / verbosity
                msg = f"Discovered {test_name}"
                self.logger.debug(msg)
                if verbosity >= 2:
                    print(f"> {test_name}")

                suite = unittest.TestSuite(tests=(test,))
                tests_discovered.append((test_name, suite))

        msg = f"{len(tests_discovered)} tests."
        if verbosity >= 1:
            print(f"{msg}\n")

        return tests_discovered


class RehearsalRunner:
    def __init__(self):
        self.runner = unittest.TextTestRunner(stream=io.StringIO())
        self.logger = logging.getLogger(__package__ + ".rehearsal")

    def run(self, tests_discovered, verbosity):
        results = {}
        for test_name, suite in tests_discovered:
            # with redirect_stdout():
            result = self.runner.run(suite)

            result_serialized = scenery.common.serialize_unittest_result(result)
            results[test_name] = result_serialized

            if result.errors or result.failures:
                log_lvl, color = logging.ERROR, "red"
            else:
                log_lvl, color = logging.INFO, "green"
            self.logger.log(log_lvl, f"{test_name}\n{scenery.common.tabulate(result_serialized)}")
            if verbosity > 0:
                print(
                    f"{scenery.common.colorize(color, test_name)}\n{scenery.common.tabulate({key: val for key, val in result_serialized.items() if val > 0})}"
                )

            # Log / verbosity
            for head, traceback in result.failures + result.errors:
                msg = f"{test_name}\n{head}\n{traceback}"
                self.logger.error(msg)
                if verbosity > 0:
                    print(msg)

        return results
