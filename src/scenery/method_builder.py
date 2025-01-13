"""Building test methods dynamically based on manifest data."""

from typing import Callable

import django.test
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
import scenery.manifest
from scenery.http_checker import HttpChecker
from scenery.set_up_handler import SetUpHandler

from selenium import webdriver


################
# METHOD BUILDER
################


class MethodBuilder:
    """A utility class for building test methods dynamically based on manifest data.

    This class provides static methods to create setup and test methods
    that can be added to Django test cases.
    """

    # TODO mad: I should build the get_response methode of the testcase here

    @staticmethod
    def build_setUpTestData(instructions: list[scenery.manifest.SetUpInstruction]) -> classmethod:
        """Build a setUpTestData class method for a Django test case.

        This method creates a class method that executes a series of setup
        instructions before any test methods are run.

        Args:
            instructions (list[str]): A list of setup instructions to be executed.

        Returns:
            classmethod: A class method that can be added to a Django test case.
        """


        def setUpTestData(django_testcase_cls: type[django.test.TestCase]) -> None:
            super(django_testcase_cls, django_testcase_cls).setUpTestData()

            for instruction in instructions:
                SetUpHandler.exec_set_up_instruction(django_testcase_cls, instruction)

        return classmethod(setUpTestData)
    
    @staticmethod
    def build_setUpClass(instructions: list[scenery.manifest.SetUpInstruction]):

        def setUpClass(django_testcase_cls: type[django.test.TestCase] | type[StaticLiveServerTestCase]) -> None:
            super(django_testcase_cls, django_testcase_cls).setUpClass()



            if issubclass(django_testcase_cls, StaticLiveServerTestCase):
                django_testcase_cls.driver = webdriver.Chrome()
                django_testcase_cls.driver.implicitly_wait(10)

            # Get CSRF token
            csrf_token = django_testcase_cls.driver.get_cookie('csrftoken')
            print("HERE", csrf_token)

            for instruction in instructions:
                SetUpHandler.exec_set_up_instruction(django_testcase_cls, instruction)

        return classmethod(setUpClass)
    
    @staticmethod
    def build_tearDownClass() -> classmethod:

        def tearDownClass(django_testcase_cls: type[django.test.TestCase] | type[StaticLiveServerTestCase]) -> None:
            if issubclass(django_testcase_cls, StaticLiveServerTestCase):
                django_testcase_cls.driver.quit()
            super(django_testcase_cls, django_testcase_cls).tearDownClass()


        return classmethod(tearDownClass)

    @staticmethod
    def build_setUp(
        instructions: list[scenery.manifest.SetUpInstruction],
    ) -> Callable[[django.test.TestCase], None]:
        """Build a setUp instance method for a Django test case.

        This method creates an instance method that executes a series of setup
        instructions before each test method is run.

        Args:
            instructions (list[str]): A list of setup instructions to be executed.

        Returns:
            function: An instance method that can be added to a Django test case.
        """

        def setUp(django_testcase: django.test.TestCase) -> None:
            for instruction in instructions:
                SetUpHandler.exec_set_up_instruction(django_testcase, instruction)

        return setUp

    @staticmethod
    def build_http_test_from_take(take: scenery.manifest.HttpTake) -> Callable:
        """Build a test method from an HttpTake object.

        This method creates a test function that sends an HTTP request
        based on the take's specifications and executes a series of checks
        on the response.

        Args:
            take (scenery.manifest.HttpTake): An HttpTake object specifying
                the request to be made and the checks to be performed.

        Returns:
            function: A test method that can be added to a Django test case.
        """

        def test(django_testcase: django.test.TestCase) -> None:
            response = HttpChecker.get_http_client_response(django_testcase, take)
            for i, check in enumerate(take.checks):
                with django_testcase.subTest(i=i):
                    HttpChecker.exec_check(django_testcase, response, check)

        return test
    

    @staticmethod
    def build_selenium_test_from_take(take: scenery.manifest.HttpTake) -> Callable:

        def test(django_testcase: StaticLiveServerTestCase) -> None:
            response = HttpChecker.get_selenium_response(django_testcase, take)



            for i, check in enumerate(take.checks):
                with django_testcase.subTest(i=i):
                    HttpChecker.exec_check(django_testcase, response, check)

        return test