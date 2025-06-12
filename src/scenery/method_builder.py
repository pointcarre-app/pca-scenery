"""Building test methods dynamically based on manifest data."""
import collections
import os
import requests
from typing import Callable
import threading
import time
import http

from scenery import logger
from scenery.manifest import SetUpInstruction, Take, DirectiveCommand
from scenery.response_checker import Checker, ResponseProtocol
from scenery.set_up_handler import SetUpHandler
from scenery.common import (
    SceneryTestCase,
    DjangoBackendTestCase,
    DjangoFrontendTestCase,
    RemoteBackendTestCase,
    RemoteFrontendTestCase,
    LoadTestCase,
    get_selenium_driver,
)

from selenium import webdriver

################
# METHOD BUILDER
################




class MethodBuilder:
    """A utility class for building test methods dynamically based on manifest data.

    This class provides static methods to create setup and test methods
    that can be added to Django test cases.
    """

    # NOTE mad: do not erase, but this is unused right now, but tested
    @staticmethod
    def build_setUpTestData(instructions: list[SetUpInstruction]) -> classmethod:
        """Build a setUpTestData class method for a Django test case.

        This method creates a class method that executes a series of setup
        instructions before any test methods are run.

        Args:
            instructions (list[str]): A list of setup instructions to be executed.

        Returns:
            classmethod: A class method that can be added to a Django test case.
        """

        def setUpTestData(testcase_cls: type[SceneryTestCase]) -> None:
            # TODO mad: not sure why this is needed
            super(testcase_cls, testcase_cls).setUpTestData() # type: ignore[misc]

            for instruction in instructions:
                SetUpHandler.exec_set_up_instruction(testcase_cls, instruction)

        return classmethod(setUpTestData)

    @staticmethod
    def build_setUpClass(
        instructions: list[SetUpInstruction], driver: webdriver.Chrome | None, headless: bool = True
    ) -> classmethod:
        """
        Build and return a class method for setup operations before any tests in a test case are run.

        This method generates a setUpClass that:
        - Sets up the test environment using Django's setup
        - For FrontendDjangoTestCase subclasses, initializes a Selenium WebDriver
        - Executes a list of setup instructions

        Args:
            instructions: A list of SetUpInstruction objects to be executed during setup
            driver: An optional pre-configured Selenium Chrome WebDriver. If None, a new driver
                will be created with the specified headless setting
            headless: Boolean flag to run Chrome in headless mode (default: True)

        Returns:
            classmethod: A class method that handles test case setup operations
        """

        def setUpClass(testcase_cls: type[SceneryTestCase]) -> None:
            logger.debug(setUpClass)
            # TODO mad: not sure why this is needed
            super(testcase_cls, testcase_cls).setUpClass()  # type: ignore[misc]

            if issubclass(testcase_cls, (DjangoFrontendTestCase, RemoteFrontendTestCase)):
                if driver is None:
                    testcase_cls.driver = get_selenium_driver(headless)
                else:
                    testcase_cls.driver = driver

                # chrome_options = Options()
                # # NOTE mad: service does not play well with headless mode
                # # service = Service(executable_path='/usr/bin/google-chrome')
                # if headless:
                #     chrome_options.add_argument("--headless=new")     # NOTE mad: For newer Chrome versions
                #     # chrome_options.add_argument("--headless")           # NOTE mad: For older Chrome versions (Framework)
                # testcase_cls.driver = webdriver.Chrome(options=chrome_options) #  service=service
                # testcase_cls.driver.implicitly_wait(10)

            for instruction in instructions:
                SetUpHandler.exec_set_up_instruction(testcase_cls, instruction)

        return classmethod(setUpClass)

    @staticmethod
    def build_tearDownClass() -> classmethod:
        """
        Build and return a class method for teardown operations after all tests in a test case have completed.

        The generated tearDownClass method performs cleanup operations, specifically:
        - For FrontendDjangoTestCase subclasses, it quits the Selenium WebDriver
        - Calls the parent class's tearDownClass method

        Returns:
            classmethod: A class method that handles test case teardown operations
        """

        def tearDownClass(testcase_cls: type[SceneryTestCase]) -> None:
            if issubclass(testcase_cls, DjangoFrontendTestCase):
                testcase_cls.driver.quit()
            # TODO mad: not sure why this is needed

            super(testcase_cls, testcase_cls).tearDownClass()  # type: ignore[misc]

        return classmethod(tearDownClass)
    

    @staticmethod
    def build_setUp(
        instructions: list[SetUpInstruction]
    ) -> Callable[[SceneryTestCase], None]:
        """Build a setUp instance method for a Django test case.

        This method creates an instance method that executes a series of setup
        instructions before each test method is run.

        Args:
            instructions (list[str]): A list of setup instructions to be executed.

        Returns:
            function: An instance method that can be added to a Django test case.
        """
        def setUp(testcase: SceneryTestCase) -> None:

            logger.debug(setUp)

            # if isinstance(testcase, (RemoteBackendTestCase, LoadTestCase, DjangoFrontendTestCase)):
            #     testcase.session = requests.Session()
            if isinstance(testcase, (RemoteBackendTestCase, LoadTestCase,)):
                testcase.session = requests.Session()
                testcase.headers = {}
            if isinstance(testcase, (RemoteBackendTestCase, RemoteFrontendTestCase, LoadTestCase)) :
                testcase.base_url = os.environ[f"SCENERY_{testcase.mode.upper()}_URL"]
            if isinstance(testcase, (DjangoFrontendTestCase,)) :
                testcase.base_url = testcase.live_server_url
            if isinstance(testcase, (LoadTestCase,)):
                testcase.data = collections.defaultdict(list)


            for instruction in instructions:
                SetUpHandler.exec_set_up_instruction(testcase, instruction)

        return setUp



    @staticmethod
    def build_test_integration(take: Take) -> Callable:
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

        # print("ON EST AL")

        def test(testcase: SceneryTestCase) -> None:
            logger.debug(test)

            response: ResponseProtocol
            if isinstance(testcase, DjangoBackendTestCase):
                response = Checker.get_django_client_response(testcase, take)

            elif isinstance(testcase, (DjangoFrontendTestCase, RemoteFrontendTestCase)):
                response = Checker.get_selenium_response(testcase, take)

            elif isinstance(testcase, RemoteBackendTestCase):
                response = Checker.get_http_response(testcase, take)
            else:
                raise ValueError(f"Unsupported test case type: {type(testcase)}")
            

            for i, check in enumerate(take.checks):

                if isinstance(testcase, (DjangoFrontendTestCase, RemoteFrontendTestCase)) and check.instruction == DirectiveCommand.STATUS_CODE:
                    continue

                if isinstance(testcase, RemoteBackendTestCase) and check.instruction in [
                        DirectiveCommand.COUNT_INSTANCES,
                        DirectiveCommand.FIELD_OF_INSTANCE,
                    ]:
                        continue

                with testcase.subTest(f"directive {i}"):
                    Checker.exec_check(testcase, response, check)

        return test

    @staticmethod
    def build_test_load(take: Take) -> Callable:
        def test(testcase: LoadTestCase) -> None:
            
            lock = threading.Lock()  # Thread synchronization

            def make_request(testcase: LoadTestCase, session: requests.Session, take: Take, headers: dict[str, str]) -> dict[str, int|float]:
                """Execute a single request and return response time and status"""

                start_time = time.time()

                if take.method == http.HTTPMethod.GET:
                    response = session.get(
                        testcase.base_url + take.url,
                        data=take.data,
                        headers=headers,
                    )
                elif take.method == http.HTTPMethod.POST:
                    response = session.post(
                        testcase.base_url + take.url,
                        take.data,
                        headers=headers,
                    )
                else:
                    raise NotImplementedError(take.method)

                        
                elapsed_time = time.time() - start_time

                # print(response.status_code)


                if not (200 <= response.status_code < 300):
                    logger.warning(f"{response.status_code=}")
                    logger.debug(f"{response.content.decode("utf8")=}")
                return {
                    'elapsed_time': elapsed_time,
                    'status_code': response.status_code,
                    'success': 200 <= response.status_code < 300
                }

            def _worker_task(testcase: LoadTestCase, take: Take, num_requests: int) -> None:
                """Worker function executed by each thread"""
                for _ in range(num_requests):
                    result = make_request(testcase, testcase.session, take, testcase.headers)
                    
                    with lock:
                        testcase.data[take.url].append(result)

            # logger.info(f"{ramp_up=}")
            logger.info(f"{testcase.users=}")
            logger.info(f"{testcase.requests_per_user=}")
            logger.info(f"{take.url=}")
            logger.info(f"{take.method=}")
            logger.info(f"{take.data=}")

            # Create threads for each simulated user
            threads = []
            for i in range(testcase.users):
                thread = threading.Thread(
                    target=_worker_task,
                    args=(testcase, take, testcase.requests_per_user),
                )
                threads.append(thread)

                # Optional: implement ramp-up by staggering thread starts
                thread.start()
                # if ramp_up > 0 and users > 1:
                #     time.sleep(ramp_up / (users - 1))

            # Wait for all threads to complete
            for thread in threads:
                thread.join()


        return test