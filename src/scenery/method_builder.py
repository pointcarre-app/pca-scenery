"""Building test methods dynamically based on manifest data."""

from typing import Callable

import django.http
import django.test
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

import scenery.manifest
from scenery.response_checker import Checker
from scenery.set_up_handler import SetUpHandler


            

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
    def build_setUpClass(instructions: list[scenery.manifest.SetUpInstruction], headless):

        def setUpClass(django_testcase_cls: type[django.test.TestCase] | type[StaticLiveServerTestCase]) -> None:
            super(django_testcase_cls, django_testcase_cls).setUpClass()



            if issubclass(django_testcase_cls, StaticLiveServerTestCase):

                print('SETTING UP CHROME')
                chrome_options = Options()
                # service = Service(executable_path='/usr/bin/google-chrome')
                if headless:
                    print("HEADLESS MODE")
                    chrome_options.add_argument("--headless=new")     # NOTE mad: For newer Chrome versions
                    # chrome_options.add_argument("--headless")           # NOTE mad: For older Chrome versions (Framework)
                django_testcase_cls.driver = webdriver.Chrome(options=chrome_options)
                django_testcase_cls.driver.implicitly_wait(10)

            for instruction in instructions:
                SetUpHandler.exec_set_up_instruction(django_testcase_cls, instruction)

        return classmethod(setUpClass)
    
    @staticmethod
    def build_tearDownClass() -> classmethod:

        def tearDownClass(django_testcase_cls: type[django.test.TestCase] | type[StaticLiveServerTestCase]) -> None:
            if issubclass(django_testcase_cls, StaticLiveServerTestCase):
                print("HERE I QUIT")
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
    def build_test_from_take(take: scenery.manifest.Take) -> Callable:
        """Build a test method from an Take object.

        This method creates a test function that sends an HTTP request
        based on the take's specifications and executes a series of checks
        on the response.

        Args:
            take (scenery.manifest.Take): An Take object specifying
                the request to be made and the checks to be performed.

        Returns:
            function: A test method that can be added to a Django test case.
        """

        def test(django_testcase: django.test.TestCase) -> None:

            # print("TEST", django_testcase)
            response = Checker.get_http_client_response(django_testcase, take)
            for i, check in enumerate(take.checks):
                with django_testcase.subTest(f"directive {i}"):
                    # print(">", check)

                    Checker.exec_check(django_testcase, response, check)

        return test
    

    @staticmethod
    def build_selenium_test_from_take(take: scenery.manifest.Take) -> Callable:

        def test(django_testcase: StaticLiveServerTestCase) -> None:

            # print("TEST", django_testcase.__class__.__name__)
            # print("TEST", django_testcase)
            response = Checker.get_selenium_response(django_testcase, take)

            for i, check in enumerate(take.checks):
                if check.instruction == scenery.manifest.DirectiveCommand.STATUS_CODE:
                    continue 
                with django_testcase.subTest(f"directive {i}"):
                    # print(">", check)
                    Checker.exec_check(django_testcase, response, check)

        return test