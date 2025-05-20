import io
import os
import logging
from types import TracebackType
import typing
import unittest
import pprint


from scenery.common import BackendDjangoTestCase, CustomDiscoverRunner, DjangoTestCase


from django.apps import apps as django_apps


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

    logger: typing.ClassVar[logging.Logger]

    @classmethod
    def log_db(cls) -> None:
        app_config = django_apps.get_app_config(os.environ["SCENERY_TESTED_APP_NAME"])
        for model in app_config.get_models():
            cls.logger.debug(f"{model.__name__}: {model.objects.count()} instances.")

    @classmethod
    def setUpClass(cls) -> None:
        cls.logger = logging.getLogger(__package__ + ".rehearsal")
        cls.logger.debug(f"{cls.__module__}.{cls.__qualname__}.setUpClass")
        cls.log_db()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.logger.debug(f"{cls.__module__}.{cls.__qualname__}.tearDownClass")
        cls.log_db()

    def setUp(self) -> None:
        self.logger.debug(f"{self.__module__}.{self.__class__.__qualname__}.setUp")
        self.log_db()

    def tearDown(self) -> None:
        self.logger.debug(f"{self.__module__}.{self.__class__.__qualname__}.tearDown")
        self.log_db()


####################################
# DJANGO TESTCASE AUGMENTATION
####################################


class TestCaseOfBackendDjangoTestCase(CustomTestCase):
    """
    This class augments the unittest.TestCase such that it is able to:
    - take a BackendDjangoTestCase and run it via the django test runner
    - make assertions on the result of the django TestCase (sucess ,failures and errors)
    - customize the output of the DjangoTestCase
    """

    django_loader: typing.ClassVar[unittest.TestLoader]
    django_runner: typing.ClassVar[CustomDiscoverRunner]
    django_stream: typing.ClassVar[io.StringIO]
    django_logger: typing.ClassVar[logging.Logger]

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.django_loader = unittest.TestLoader()
        # NOTE mad: We customize the django testrunner to avoid confusion in the output and django vs unittest
        cls.django_stream = io.StringIO()
        cls.django_runner = CustomDiscoverRunner(cls.django_stream)
        # FIXME: this does not pass type checking
        cls.django_runner.test_runner.resultclass = CustomTestResult  # type: ignore[assignment]
        cls.django_logger = logging.getLogger(__package__ + ".rehearsal.django")
        
    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        cls.django_stream.close()

    def setUp(self) -> None:
        super().setUp()
        # NOTE mad: We create a django TestCase (customized) to which we will dynamically add setUpTestData, setUp and test_* functions
        self.django_testcase = type("BackendDjangoTestCase", (BackendDjangoTestCase,), {})

    def tearDown(self) -> None:
        super().tearDown()
        # msg = self.django_stream.getvalue()
        # self.django_logger.debug(f"{scenery.common.pretty_test_name(self)}\n{msg}")
        self.django_stream.seek(0)
        self.django_stream.truncate()

    def run_django_testcase(self) -> CustomTestResult:
        suite = unittest.TestSuite()
        tests = self.django_loader.loadTestsFromTestCase(self.django_testcase)
        suite.addTests(tests)
        result = self.django_runner.run_suite(suite)
        # NOTE: type casting  because mypy miss "cls.django_runner.test_runner.resultclass = CustomTestResult"
        #  (see setUpClass)
        # self.django_logger.info(f"{repr(self)} {result}")


        return typing.cast(CustomTestResult, result)

    def run_django_test(self, django_test: DjangoTestCase) -> CustomTestResult:
        suite = unittest.TestSuite()
        suite.addTest(django_test)
        result = self.django_runner.run_suite(suite)
        # NOTE: type casting  because mypy miss "cls.django_runner.test_runner.resultclass = CustomTestResult"
        #  (see setUpClass)
        # self.django_logger.info(f"{repr(self)} {result}")

        return typing.cast(CustomTestResult, result)

    def assertTestPasses(self, django_test: DjangoTestCase) -> None:
        result = self.run_django_test(django_test)
        if result.errors:
            pprint.pprint(result.errors)
        self.assertTrue(result.wasSuccessful(), f"{django_test} was not succesfull")

    def assertTestFails(self, django_test: DjangoTestCase) -> None:
        result = self.run_django_test(django_test)
        self.assertFalse(result.wasSuccessful(), f"{django_test} was not succesfull")
        self.assertEqual(len(result.errors), 0, f"{django_test} did not raise any error")

    def assertTestRaises(
        self, django_test: DjangoTestCase, expected: type[BaseException]
    ) -> None:
        result = self.run_django_test(django_test)
        self.assertGreater(len(result.errors), 0, f"{django_test} did not raise any error")
        self.assertIsNotNone(result.caught_exception, f"{django_test} did not caught any exception")
        with self.assertRaises(
            expected, msg=f"{django_test} did not raise expected exception {expected}"
        ):
            # NOTE: type casting as I expect some error to be caught here
            result.caught_exception = typing.cast(
                tuple[type[BaseException], BaseException, TracebackType], result.caught_exception
            )
            raise result.caught_exception[0](result.caught_exception[1])


