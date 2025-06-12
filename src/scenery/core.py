"""Build the tests from the Manifest, discover & run tests."""

import argparse
from functools import wraps
import os
import sys
from typing import Callable, Tuple
import time
import unittest

from scenery import logger
from scenery.manifest import Manifest
from scenery.method_builder import MethodBuilder
from scenery.manifest_parser import ManifestParser
from scenery.common import (
    DjangoFrontendTestCase,
    DjangoBackendTestCase,
    RemoteBackendTestCase,
    LoadTestCase,
    CustomDiscoverRunner,
    DjangoTestCase,
    get_selenium_driver,
)

from django.conf import settings
from django.test.utils import get_runner

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from urllib3.exceptions import MaxRetryError, NewConnectionError


# DECORATORS
############


# TODO mad: screenshot on error
# TODO: move this somewhere else, selenium utils


def retry_on_timeout(retries: int = 3, delay: int = 5) -> Callable:
    """Retry a function on specific timeout-related exceptions.

    This decorator will attempt to execute the decorated function multiple times if it encounters
    timeout-related exceptions (TimeoutException, MaxRetryError, NewConnectionError,
    ConnectionRefusedError). Between retries, it will wait for a specified delay period.

    Args:
        retries (int, optional): Maximum number of retry attempts. Defaults to 3.
        delay (int, optional): Time to wait between retries in seconds. Defaults to 5.

    Returns:
        Callable: A decorator function that wraps the original function with retry logic.

    Raises:
        TimeoutException: If all retry attempts fail with a timeout.
        MaxRetryError: If all retry attempts fail with max retries exceeded.
        NewConnectionError: If all retry attempts fail with connection errors.
        ConnectionRefusedError: If all retry attempts fail with connection refused.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):  # type: ignore # NOTE mad: as log_exec_bbar, this makes sense for a decorated function
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except (
                    TimeoutException,
                    MaxRetryError,
                    NewConnectionError,
                    ConnectionRefusedError,
                ):
                    if attempt == retries - 1:
                        raise
                    time.sleep(delay)
            return None

        return wrapper

    return decorator


# METACLASSES
#############


class MetaTest(type):
    """
    A metaclass for creating test classes dynamically based on a Manifest.

    This metaclass creates test methods for each combination of case and scene in the manifest,
    and adds setup methods to the test class.
    """

    def __new__(
        cls,
        clsname: str,
        bases: tuple[type],
        manifest: Manifest,
        # mode: str | None = None,
        only_case_id: str | None = None,
        only_scene_pos: str | None = None,
        only_url: str | None = None,
        driver=None,
    ) -> type[DjangoTestCase]:
        """Responsible for building the TestCase class.

        Args:
            clsname (str): The name of the class being created.
            bases (tuple): The base classes of the class being created.
            manifest (Manifest): The manifest containing test cases and scenes.

        Returns:
            type: A new test class with dynamically created test methods.

        Raises:
            ValueError: If the restrict argument is not in the correct format.
        """

        # if mode is None:
        #     raise ValueError("Mode cannot be None")

        # Build setUp and tearDown functions
        ####################################

        # TODO mad: setUpTestData
        setUpClass = MethodBuilder.build_setUpClass(manifest.set_up_class, driver)
        setUp = MethodBuilder.build_setUp(manifest.set_up)

        cls_attrs = {
            "setUpClass": setUpClass,
            "setUp": setUp,
            # "mode": mode,
        }

        if bases == (DjangoFrontendTestCase,):
            # NOTE mad: used to close the driver
            tearDownClass = MethodBuilder.build_tearDownClass()
            cls_attrs["tearDownClass"] = tearDownClass

        
        # Add test_* functions
        ####################################

        for case_id, scene_pos, take in manifest.iter_on_takes(
            only_url,
            only_case_id,
            only_scene_pos,
        ):
            if bases == (DjangoBackendTestCase,):
                test = MethodBuilder.build_dev_backend_test(take)
            elif bases == (DjangoFrontendTestCase,):
                test = MethodBuilder.build_dev_frontend_test(take)
            elif bases == (RemoteBackendTestCase,):
                test = MethodBuilder.build_remote_backend_test(take)
            elif bases == (LoadTestCase,):
                print("WE HERRE")
                test = MethodBuilder.build_remote_load_test_from_take(take)
            else:
                raise NotImplementedError
            cls_attrs.update({f"test_case_{case_id}_scene_{scene_pos}": test})

        test_cls = super().__new__(cls, clsname, bases, cls_attrs)
        return test_cls  # type: ignore [return-value]
        # FIXME mad: In member "__new__" of class "MetaBackTest":
        # src/scenery/core.py:195:16: error: Incompatible return value type (got "MetaBackTest", expected "type[DjangoTestCase]")



class TestsRunner:
    """
    A class for running discovered tests and collecting results.

    This class takes discovered tests, runs them using a Django test runner,
    and collects and formats the results.

    Attributes:
        runner (DiscoverRunner): A Django test runner instance.
        logger (Logger): A logger instance for this class.
        discoverer (MetaTestDiscoverer): An instance of MetaTestDiscoverer for discovering tests.
        stream (StringIO): A string buffer for capturing test output.
    """

    def __init__(self, failfast: bool = False) -> None:
        """Initialize the MetaTestRunner with a runner, logger, discoverer, and output stream."""
        # self.logger = logging.getLogger(__package__)

        # self.stream = io.StringIO()
        self.stream = sys.stdout
        self.runner = CustomDiscoverRunner(stream=self.stream, failfast=failfast)

        # TODO mad: this is PCA specific
        # app_logger = logging.getLogger("app.close_watch")
        # app_logger.propagate = False

    def __del__(self) -> None:
        """Clean up resources when the MetaTestRunner is deleted."""
        # TODO mad: a context manager would be ideal, let's wait v2
        # self.stream.close()
        # print(self.stream.flush())
        # app_logger = logging.getLogger("app.close_watch")
        # app_logger.propagate = True

    def run(self, tests_discovered: unittest.TestSuite) -> unittest.TestResult:
        """
        Run the discovered tests and collect results.

        Args:
            tests_discovered (list): A list of tuples, each containing a test name and a TestSuite.
            verbosity (int): The verbosity level for output.

        Returns:
            dict: A dictionary mapping test names to their serialized results.

        Note:
            This method logs test results and prints them to the console based on the verbosity level.
        """
        # TODO mad: could this just disappear?
        results = self.runner.run_suite(tests_discovered)
        return results


# TEST LOADER
#############

# NOTE mad: I redefine this for multithreading possibilities
# sadly this failed but I still think it is a better pattern


class TestsDiscoverer:
    """
    A class for discovering and loading test cases from manifest files.

    This class scans a directory for manifest files, creates test classes from these manifests,
    and loads the tests into test suites.

    Attributes:
        logger (Logger): A logger instance for this class.
        runner (DiscoverRunner): A Django test runner instance.
        loader (TestLoader): A test loader instance from the runner.
    """

    runner = get_runner(settings, test_runner_class="django.test.runner.DiscoverRunner")()
    loader: unittest.loader.TestLoader = runner.test_loader

    @property
    def folder(self):
        return os.environ["SCENERY_MANIFESTS_FOLDER"]

    def integration_tests_from_manifest(
        self,
        filename: str,
        mode: str,
        back: bool = False,
        front: bool = False,
        only_url: str | None = None,
        timeout_waiting_time: int = 5,
        only_case_id: str | None = None,
        only_scene_pos: str | None = None,
        driver: webdriver.Chrome | None = None,
        headless: bool = True,
    ) -> Tuple[unittest.TestSuite, unittest.TestSuite]:
        """Creates test suites from a manifest file for both backend and frontend testing.

        Parses a YAML manifest file and generates corresponding test suites for backend
        and frontend testing. Tests can be filtered based on various criteria like test type,
        specific views, or test cases.

        Args:
            filename (str): The name of the YAML manifest file to parse.
            only_back (bool, optional): Run only backend tests. Defaults to False.
            only_front (bool, optional): Run only frontend tests. Defaults to False.
            only_url (str, optional): Filter tests to run only for a specific view. Defaults to None.
            timeout_waiting_time (int, optional): Timeout duration for frontend tests in seconds. Defaults to 5.
            only_case_id (str, optional): Filter tests to run only for a specific case ID. Defaults to None.
            only_scene_pos (str, optional): Filter tests to run only for a specific scene position. Defaults to None.
            driver (webdriver.Chrome, optional): Selenium Chrome WebDriver instance. If None, creates new instance. Defaults to None.
            headless (bool, optional): Whether to run browser in headless mode. Defaults to True.

        Returns:
            Tuple[unittest.TestSuite, unittest.TestSuite]: A tuple containing:
                - Backend test suite (first element)
                - Frontend test suite (second element)

        Notes:
            - The manifest's testtype determines which suites are created (backend, frontend, or both)
            - Empty test suites are returned for disabled test types
            - The driver initialization can occur here or be passed in from external code
        """

        dev_backend_suite, dev_frontend_suite = unittest.TestSuite(), unittest.TestSuite()
        remote_backend_suite, remote_frontend_suite = unittest.TestSuite(), unittest.TestSuite()

        # Parse manifest
        # TODO: there should be a separation between reading file and parsing
        manifest = ManifestParser.parse_yaml_from_file(os.path.join(self.folder, filename))
        ttype = manifest.testtype
        manifest_name = filename.replace(".yml", "")

        # NOTE mad: manifests can indicate they are not to be ran in some mode
        back &= ttype is None or ttype == "backend"
        front &= ttype is None or ttype == "frontend"

        if back and mode == "dev":
            # cls = MetaDevBackendTest(
            cls = MetaTest(
                f"{manifest_name}.dev.backend",
                (DjangoBackendTestCase,),
                manifest,
                only_case_id=only_case_id,
                only_scene_pos=only_scene_pos,
                only_url=only_url,
            )
            # FIXME mad: type hinting mislead by metaclasses
            tests = self.loader.loadTestsFromTestCase(cls)  # type: ignore[arg-type]
            dev_backend_suite.addTests(tests)

        if back and mode in ["local", "staging", "prod"]:
            cls = MetaTest(
            # cls = MetaRemoteBackendTest(
                f"{manifest_name}.remote.backend",
                (RemoteBackendTestCase,),
                manifest,
                only_case_id=only_case_id,
                only_scene_pos=only_scene_pos,
                only_url=only_url,
            )
            # TODO mad: really not sure this is the right place
            cls.mode = mode
            tests = self.loader.loadTestsFromTestCase(cls)
            remote_backend_suite.addTests(tests)

        # Create frontend test
        if front and mode == "dev":
            # NOTE mad: this is here to be able to load driver in two places
            # See also scenery/__main__.py
            # Probably not a great pattern but let's FIXME this later
            if driver is None:
                driver = get_selenium_driver(headless=headless)

            cls = MetaTest(
                f"{manifest_name}.dev.frontend",
                (DjangoFrontendTestCase,),
                manifest,
                only_case_id=only_case_id,
                only_scene_pos=only_scene_pos,
                only_url=only_url,
                timeout_waiting_time=timeout_waiting_time,
                driver=driver,
                # headless=True,
            )
            # FIXME mad: type hinting mislead by metaclasses
            tests = self.loader.loadTestsFromTestCase(cls)  # type: ignore[arg-type]
            dev_frontend_suite.addTests(tests)

        if front and mode in ["local", "staging", "prod"]:
            raise NotImplementedError

        return dev_backend_suite, dev_frontend_suite, remote_backend_suite, remote_frontend_suite


    def load_tests_from_manifest(
        self,
        filename: str,
        mode: str,
        users: int,
        requests_per_user: int,
        only_url: str | None = None,
        timeout_waiting_time: int = 5,
        only_case_id: str | None = None,
        only_scene_pos: str | None = None,
    ):
        from .load_test import LoadTester
        import threading
        import collections

        test_suite = unittest.TestSuite()

        # Parse manifest
        # TODO: there should be a separation between reading file and parsing
        manifest = ManifestParser.parse_yaml_from_file(os.path.join(self.folder, filename))
        manifest_name = filename.replace(".yml", "")

        cls = MetaTest(
            f"{manifest_name}.load",
            (LoadTestCase,),
            manifest,
            # mode=mode,
            only_case_id=only_case_id,
            only_scene_pos=only_scene_pos,
            only_url=only_url,
        )

        cls.mode = mode
        cls.users = users
        cls.requests_per_user = requests_per_user

        # cls.tester = LoadTester(mode)
        tests = self.loader.loadTestsFromTestCase(cls) 
        test_suite.addTests(tests)

        return test_suite



def process_manifest_as_integration_test(
    manifest_filename: str, args: argparse.Namespace, driver: webdriver.Chrome | None
) -> Tuple[bool, dict, bool, dict]:
    """Process a test manifest file and executes both backend and frontend tests.

    Takes a manifest file and command line arguments to run the specified tests,
    collecting and summarizing the results for both backend and frontend test suites.

    Args:
        filename (str): The name of the YAML manifest file to process.
        args (argparse.Namespace): Command line arguments containing:
            - only_back (bool): Run only backend tests
            - only_front (bool): Run only frontend tests
            - only_url (str): Filter for specific view
            - only_case_id (str): Filter for specific case ID
            - only_scene_pos (str): Filter for specific scene position
            - timeout_waiting_time (int): Frontend test timeout duration
            - headless (bool): Whether to run browser in headless mode
        driver (webdriver.Chrome | None): Selenium Chrome WebDriver instance or None.

    Returns:
        Tuple[bool, dict, bool, dict]: A tuple containing:
            - Backend test success status (bool)
            - Backend test summary results (dict)
            - Frontend test success status (bool)
            - Frontend test summary results (dict)

    Notes:
        - Prints the manifest name (without .yml extension) during execution
        - Uses TestsLoader and TestsRunner for test execution
        - Test results are summarized with verbosity level 0
    """

    # logging.log(logging.INFO, f"{manifest_filename=}")
    logger.info(f"{manifest_filename=}")

    loader = TestsDiscoverer()
    runner = TestsRunner()

    dev_backend_suite, dev_frontend_suite, remote_backend_suite, remote_frontend_suite = (
        loader.integration_tests_from_manifest(
            manifest_filename,
            mode=args.mode,
            back=args.back,
            front=args.front,
            only_url=args.url,
            only_case_id=args.case_id,
            only_scene_pos=args.scene_pos,
            timeout_waiting_time=args.timeout_waiting_time,
            driver=driver,
            headless=args.headless,
        )
    )

    results = {
        "dev_backend": None,
        "dev_frontend": None,
        "remote_backend": None,
        "remote_frontend": None,
    }

    # dev_backend_result, dev_frontend_result, remote_backend_result, remote_frontend_result = None, None, None, None
    if args.back and args.mode == "dev":
        results["dev_backend"] = runner.run(dev_backend_suite)

    if args.back and args.mode in ["local", "staging", "prod"]:
        results["remote_backend"] = runner.run(remote_backend_suite)

    if args.front and args.mode == "dev":
        results["dev_frontend"] = runner.run(dev_frontend_suite)

    # if args.front and args.mode in ["local", "staging", "prod"]:
    #     remote_frontend_result = runner.run(dev_frontend_suite)

    return results


def process_manifest_as_load_test(
    manifest_filename: str, args: argparse.Namespace
) -> Tuple[bool, dict, bool, dict]:
    results = {}

    logger.info(f"{manifest_filename=}")

    loader = TestsDiscoverer()
    runner = TestsRunner()

    tests_suite = loader.load_tests_from_manifest(
        manifest_filename,
        mode=args.mode,
        only_url=args.url,
        only_case_id=args.case_id,
        only_scene_pos=args.scene_pos,
        users=args.users,
        requests_per_user=args.requests,
    )

    for test in tests_suite:
        test_result = runner.run(test)
        assert len(test_result.errors) == 0
        results.update(test.data)

    # results = {
    # }

    # results["load"] = runner.run(tests_suite)

    return results



###################################################################################
# TRASH


# class MetaDevBackendTest(type):
#     """
#     A metaclass for creating test classes dynamically based on a Manifest.

#     This metaclass creates test methods for each combination of case and scene in the manifest,
#     and adds setup methods to the test class.
#     """

#     def __new__(
#         cls,
#         clsname: str,
#         bases: tuple[type],
#         manifest: Manifest,
#         only_case_id: str | None = None,
#         only_scene_pos: str | None = None,
#         only_url: str | None = None,
#     ) -> type[DjangoTestCase]:
#         """Responsible for building the TestCase class.

#         Args:
#             clsname (str): The name of the class being created.
#             bases (tuple): The base classes of the class being created.
#             manifest (Manifest): The manifest containing test cases and scenes.

#         Returns:
#             type: A new test class with dynamically created test methods.

#         Raises:
#             ValueError: If the restrict argument is not in the correct format.
#         """
#         # TODO mad: setUpTestData
#         # setUpTestData = MethodBuilder.build_setUpTestData(manifest.set_up_test_data)
#         setUpClass = MethodBuilder.build_setUpClass(manifest.set_up_class, None)
#         setUp = MethodBuilder.build_setUp(manifest.set_up)

#         # Add SetupData and SetUp as methods of the Test class
#         cls_attrs = {
#             "setUpClass": setUpClass,
#             "setUp": setUp,
#         }
#         for case_id, scene_pos, take in manifest.iter_on_takes(
#             only_url,
#             only_case_id,
#             only_scene_pos,
#         ):
#             test = MethodBuilder.build_dev_backend_test(take)
#             # test = log_exec_bar(test)
#             cls_attrs.update({f"test_case_{case_id}_scene_{scene_pos}": test})

#         test_cls = super().__new__(cls, clsname, bases, cls_attrs)
#         return test_cls  # type: ignore [return-value]
#         # FIXME mad: In member "__new__" of class "MetaBackTest":
#         # src/scenery/core.py:195:16: error: Incompatible return value type (got "MetaBackTest", expected "type[DjangoTestCase]")


# class MetaDevFrontendTest(type):
#     """A metaclass for creating frontend test classes dynamically based on a Manifest.

#     This metaclass creates test methods for each combination of case and scene in the manifest,
#     and adds setup and teardown methods to the test class. It specifically handles frontend testing
#     setup including web driver configuration.
#     """

#     def __new__(
#         cls,
#         clsname: str,
#         bases: tuple[type],
#         manifest: Manifest,
#         driver: webdriver.Chrome,
#         only_case_id: str | None = None,
#         only_scene_pos: str | None = None,
#         only_url: str | None = None,
#         timeout_waiting_time: int = 5,
#     ) -> type[FrontendDjangoTestCase]:
#         """Responsible for building the TestCase class.

#         Args:
#             clsname (str): The name of the class being created.
#             bases (tuple): The base classes of the class being created.
#             manifest (Manifest): The manifest containing test cases and scenes.
#             driver (webdriver.Chrome): Chrome webdriver instance for frontend testing.
#             only_case_id (str, optional): Restrict tests to a specific case ID.
#             only_scene_pos (str, optional): Restrict tests to a specific scene position.
#             only_url (str, optional): Restrict tests to a specific view.
#             timeout_waiting_time (int, optional): Time in seconds to wait before timeout. Defaults to 5.

#         Returns:
#             type: A new test class with dynamically created frontend test methods.

#         Raises:
#             ValueError: If the restrict arguments are not in the correct format.
#         """
#         setUpClass = MethodBuilder.build_setUpClass(manifest.set_up_class, driver)
#         setUp = MethodBuilder.build_setUp(manifest.set_up)
#         tearDownClass = MethodBuilder.build_tearDownClass()

#         # NOTE mad: setUpClass and tearDownClass are important for the driver
#         cls_attrs = {
#             "setUpClass": setUpClass,
#             "setUp": setUp,
#             "tearDownClass": tearDownClass,
#         }

#         for case_id, scene_pos, take in manifest.iter_on_takes(
#             only_url,
#             only_case_id,
#             only_scene_pos,
#         ):
#             test = MethodBuilder.build_dev_frontend_test(take)
#             # test = retry_on_timeout(delay=timeout_waiting_time)(test)
#             # test = screenshot_on_error(test)
#             # test = log_exec_bar(test)
#             cls_attrs.update({f"test_case_{case_id}_scene_{scene_pos}": test})

#         test_cls = super().__new__(cls, clsname, bases, cls_attrs)

#         return test_cls  # type: ignore[return-value]
#         # FIXME mad: mypy is struggling with the metaclass,
#         # I just ignore here instead of casting which does not do the trick


# class MetaRemoteBackendTest(type):
#     def __new__(
#         cls,
#         clsname: str,
#         bases: tuple[type],
#         manifest: Manifest,
#         only_case_id: str | None = None,
#         only_scene_pos: str | None = None,
#         only_url: str | None = None,
#     ) -> type[DjangoTestCase]:
#         """Responsible for building the TestCase class.

#         Args:
#             clsname (str): The name of the class being created.
#             bases (tuple): The base classes of the class being created.
#             manifest (Manifest): The manifest containing test cases and scenes.

#         Returns:
#             type: A new test class with dynamically created test methods.

#         Raises:
#             ValueError: If the restrict argument is not in the correct format.
#         """
#         # NOTE mad: right now everything is in the setup
#         # TODO mad: setUpTestData and setUpClass
#         # setUpTestData = MethodBuilder.build_setUpTestData(manifest.set_up_test_data)
#         setUpClass = MethodBuilder.build_setUpClass(manifest.set_up_class, None)
#         setUp = MethodBuilder.build_setUp(manifest.set_up)

#         # Add SetupData and SetUp as methods of the Test class
#         cls_attrs = {
#             # "setUpTestData": setUpTestData,
#             "setUpClass": setUpClass,
#             "setUp": setUp,
#         }
#         for case_id, scene_pos, take in manifest.iter_on_takes(
#             only_url,
#             only_case_id,
#             only_scene_pos,
#         ):
#             test = MethodBuilder.build_remote_backend_test(take)
#             # test = log_exec_bar(test)
#             cls_attrs.update({f"test_case_{case_id}_scene_{scene_pos}": test})

#         test_cls = super().__new__(cls, clsname, bases, cls_attrs)

#         return test_cls



    # def load_tests_from_manifest(
    #     self,
    #     filename: str,
    #     mode: str,
    #     users: int,
    #     requests_per_user: int,
    #     only_url: str | None = None,
    #     timeout_waiting_time: int = 5,
    #     only_case_id: str | None = None,
    #     only_scene_pos: str | None = None,
    # ):
    #     from .load_test import LoadTester
    #     import threading
    #     import collections

    #     test_suite = unittest.TestSuite()

    #     # Parse manifest
    #     # TODO: there should be a separation between reading file and parsing
    #     manifest = ManifestParser.parse_yaml_from_file(os.path.join(self.folder, filename))
    #     manifest_name = filename.replace(".yml", "")

    #     for case_id, scene_pos, take in manifest.iter_on_takes(
    #         only_url,
    #         only_case_id,
    #         only_scene_pos,
    #     ):

    #         class _LoadTestCase(LoadTestCase):
    #             def setUp(self):
    #                 # super().setUp()
    #                 # self.tester = LoadTester(self.base_url)
    #                 self.tester = LoadTester(manifest, mode)
    #                 # self.manifest = manifest
    #                 self.data = collections.defaultdict(list)
    #                 self.lock = threading.Lock()  # Thread synchronization
    #                 self.mode = mode

    #                 setUp = MethodBuilder.build_setUp(manifest.set_up)
    #                 setUp(self)

    #             def test(self):
    #                 # logger.info(f"{ramp_up=}")
    #                 logger.info(f"{users=}")
    #                 logger.info(f"{requests_per_user=}")
    #                 logger.info(f"{take.url=}")
    #                 logger.info(f"{take.method=}")
    #                 logger.info(f"{take.data=}")

    #                 # Create threads for each simulated user
    #                 threads = []
    #                 for i in range(users):
    #                     thread = threading.Thread(
    #                         target=self.tester._worker_task,
    #                         args=(self, take, requests_per_user),
    #                     )
    #                     threads.append(thread)

    #                     # Optional: implement ramp-up by staggering thread starts
    #                     thread.start()
    #                     # if ramp_up > 0 and users > 1:
    #                     #     time.sleep(ramp_up / (users - 1))

    #                 # Wait for all threads to complete
    #                 for thread in threads:
    #                     thread.join()


    #         cls = _LoadTestCase
    #         tests = self.loader.loadTestsFromTestCase(cls)
    #         test_suite.addTests(tests)

    #     return test_suite

