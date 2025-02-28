"""Build the tests from the Manifest, discover & run tests."""
import argparse
import io
import itertools
import logging
import os
import unittest
from typing import Iterable, Callable, Any, Tuple
from functools import wraps
import time

from scenery.manifest import Manifest, Case, Scene
from scenery.method_builder import MethodBuilder
from scenery.manifest_parser import ManifestParser
from scenery.common import FrontendDjangoTestCase, BackendDjangoTestCase, CustomDiscoverRunner, DjangoTestCase, summarize_test_result, get_selenium_driver

from django.conf import settings
from django.test.utils import get_runner

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from urllib3.exceptions import MaxRetryError, NewConnectionError


# DECORATORS
############


def log_exec_bar(func: Callable) -> Any:
    """Log the execution of a function with a progress bar."""
    def wrapper(*args, **kwargs): # type: ignore 
        # NOTE mad: this type ignore makes sense as we can take any function
        out = func(*args, **kwargs)
        print(".", end="")
        return out
    # TODO mad: copy unittest style ca marche pas comme ca je crois
    #     try:
    #         out = func(*args, **kwargs)
    #         print(".", end="")
    #         return out
    #     except AssertionError:
    #         print("F", end="")
    #         raise
    #     except Exception:
    #         print("E", end="")
    #         raise
    return wrapper


# TODO mad: screenshot on error
# import datetime
# def screenshot_on_error(driver):
#     
#     screenshot_dir = "scenery-screenshots"
#     def decorator(func):
#         @wraps(func)
#         def wrapper(*args, **kwargs):

#             # Create screenshots directory if it doesn't exist
#             os.makedirs(screenshot_dir, exist_ok=True)

#             try:
#                 return func(*args, **kwargs)
#             except Exception as e:
#                 # Create more detailed filename
#                 timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
#                 error_type = e.__class__.__name__
#                 function_name = func.__name__

#                 screenshot_name = os.path.join(
#                     screenshot_dir,
#                     f"{error_type}-{function_name}-{timestamp}.png"
#                 )

#                 driver.save_screenshot(screenshot_name)

#                     # Get current URL and page source for debugging
#                     # current_url = driver.current_url

#     #                 # Log error context
#     #                 print(f"""
#     # Error occurred during test execution:
#     # - Function: {function_name}
#     # - Error Type: {error_type}
#     # - Error Message: {str(e)}
#     # - URL: {current_url}
#     # - Screenshot: {screenshot_name}
#     #                 """)

#                 # except WebDriverException as screenshot_error:
#                 #     print(f"Failed to capture error context: {screenshot_error}")

#                 # Re-raise the original exception
#                 raise e

#         return wrapper

#     return decorator


def retry_on_timeout(retries: int=3, delay: int=5) -> Callable:
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
        def wrapper(*args, **kwargs): # type: ignore # NOTE mad: as log_exec_bbar, this makes sense for a decorated function
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except (TimeoutException, MaxRetryError, NewConnectionError, ConnectionRefusedError):
                    if attempt == retries - 1:
                        raise
                    time.sleep(delay)
            return None

        return wrapper

    return decorator


# METACLASSES
#############

# NOTE mad: this code is used both in banckend and
# frontend metaclasses

def iter_on_takes_from_manifest(
        manifest: Manifest, 
        only_view: str | None, 
        only_case_id: str | None, 
        only_scene_pos: str | None
    ) -> Iterable[Tuple[str, Case, int, Scene]]:
    """Iterate over takes from the manifest based on the provided filters."""
    for (case_id, case), (scene_pos, scene) in itertools.product(
        manifest.cases.items(), enumerate(manifest.scenes)
    ):
        if only_case_id is not None and case_id != only_case_id:
            continue
        elif only_scene_pos is not None and str(scene_pos) != only_scene_pos:
            continue
        if only_view is not None and only_view != scene.url:
            continue
        yield case_id, case, scene_pos, scene


# BACKEND TEST


class MetaBackTest(type):
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
        only_case_id: str | None = None,
        only_scene_pos: str | None = None,
        only_view: str | None = None,
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
        # NOTE mad: right now everything is in the setup
        # TODO mad: setUpTestData and setUpClass
        # setUpTestData = MethodBuilder.build_setUpTestData(manifest.set_up_test_data)
        setUp = MethodBuilder.build_setUp(manifest.set_up)

        # Add SetupData and SetUp as methods of the Test class
        cls_attrs = {
            # "setUpTestData": setUpTestData,
            "setUp": setUp,
        }
        for case_id, case, scene_pos, scene in iter_on_takes_from_manifest(
            manifest, only_view, only_case_id, only_scene_pos
        ):
            take = scene.shoot(case)
            test = MethodBuilder.build_backend_test_from_take(take)
            test = log_exec_bar(test)
            cls_attrs.update({f"test_case_{case_id}_scene_{scene_pos}": test})

        test_cls = super().__new__(cls, clsname, bases, cls_attrs)
        return test_cls  # type: ignore [return-value]
        # FIXME mad: In member "__new__" of class "MetaBackTest": 
        # src/scenery/core.py:195:16: error: Incompatible return value type (got "MetaBackTest", expected "type[DjangoTestCase]")


# FRONTEND TEST

class MetaFrontTest(type):
    """A metaclass for creating frontend test classes dynamically based on a Manifest.

    This metaclass creates test methods for each combination of case and scene in the manifest,
    and adds setup and teardown methods to the test class. It specifically handles frontend testing
    setup including web driver configuration.
    """

    def __new__(
        cls,
        clsname: str,
        bases: tuple[type],
        manifest: Manifest,
        driver: webdriver.Chrome,
        only_case_id: str | None = None,
        only_scene_pos: str | None = None,
        only_view: str | None = None,
        timeout_waiting_time: int=5,
    ) -> type[FrontendDjangoTestCase]:
        """Responsible for building the TestCase class.
        
        Args:
            clsname (str): The name of the class being created.
            bases (tuple): The base classes of the class being created.
            manifest (Manifest): The manifest containing test cases and scenes.
            driver (webdriver.Chrome): Chrome webdriver instance for frontend testing.
            only_case_id (str, optional): Restrict tests to a specific case ID.
            only_scene_pos (str, optional): Restrict tests to a specific scene position.
            only_view (str, optional): Restrict tests to a specific view.
            timeout_waiting_time (int, optional): Time in seconds to wait before timeout. Defaults to 5.

        Returns:
            type: A new test class with dynamically created frontend test methods.

        Raises:
            ValueError: If the restrict arguments are not in the correct format.
        """
        setUpClass = MethodBuilder.build_setUpClass(manifest.set_up_test_data, driver)
        setUp = MethodBuilder.build_setUp(manifest.set_up)
        tearDownClass = MethodBuilder.build_tearDownClass()


        # NOTE mad: setUpClass and tearDownClass are important for the driver
        cls_attrs = {
            "setUpClass": setUpClass,
            "setUp": setUp,
            "tearDownClass": tearDownClass,
        }

        for case_id, case, scene_pos, scene in iter_on_takes_from_manifest(
            manifest, only_view, only_case_id, only_scene_pos
        ):
            take = scene.shoot(case)
            test = MethodBuilder.build_frontend_test_from_take(take)
            test = retry_on_timeout(delay=timeout_waiting_time)(test)
            # test = screenshot_on_error(test)
            test = log_exec_bar(test)
            cls_attrs.update({f"test_case_{case_id}_scene_{scene_pos}": test})

        test_cls = super().__new__(cls, clsname, bases, cls_attrs)
        
        return test_cls # type: ignore[return-value]
        # FIXME mad: mypy is struggling with the metaclass,
        # I just ignore here instead of casting which does not do the trick


# DISCOVERER AND RUNNER
#######################

# TODO mad: this will disappear, as this approach is not compatible with parallelization


# class TestsDiscoverer:
#     """
#     A class for discovering and loading test cases from manifest files.

#     This class scans a directory for manifest files, creates test classes from these manifests,
#     and loads the tests into test suites.

#     Attributes:
#         logger (Logger): A logger instance for this class.
#         runner (DiscoverRunner): A Django test runner instance.
#         loader (TestLoader): A test loader instance from the runner.
#     """

#     def __init__(self) -> None:
#         self.logger = logging.getLogger(__package__)
#         self.runner = get_runner(settings, test_runner_class="django.test.runner.DiscoverRunner")()
#         self.loader: unittest.loader.TestLoader = self.runner.test_loader

#     def discover(
#         self,
#         restrict_manifest_test: typing.Optional[str] = None,
#         verbosity: int = 2,
#         skip_back=False,
#         skip_front=False,
#         restrict_view=None,
#         headless=True,
#     ) -> list[tuple[str, unittest.TestSuite]]:
#         """
#         Discover and load tests from manifest files.

#         Args:
#             restrict (str, optional): A string to restrict which manifests and tests are loaded,
#                                       in the format "manifest.case_id.scene_pos".
#             verbosity (int, optional): The verbosity level for output. Defaults to 2.

#         Returns:
#             list: A list of tuples, each containing a test name and a TestSuite with a single test.

#         Raises:
#             ValueError: If the restrict argument is not in the correct format.
#         """
#         # TODO mad: this should take an iterable of files or of yaml string would be even better

#         # handle manifest/test restriction
#         if restrict_manifest_test is not None:
#             restrict_args = restrict_manifest_test.split(".")
#             if len(restrict_args) == 1:
#                 restrict_manifest, restrict_test = (
#                     restrict_args[0],
#                     None,
#                 )
#             elif len(restrict_args) == 2:
#                 restrict_manifest, restrict_test = (restrict_args[0], restrict_args[1])
#             elif len(restrict_args) == 3:
#                 restrict_manifest, restrict_test = (
#                     restrict_args[0],
#                     restrict_args[1] + "." + restrict_args[2],
#                 )
#         else:
#             restrict_manifest, restrict_test = None, None

#         backend_parrallel_suites, frontend_parrallel_suites = [], []
#         suite_cls: type[unittest.TestSuite] = self.runner.test_suite
#         backend_suite, frontend_suite = suite_cls(), suite_cls()

#         folder = os.environ["SCENERY_MANIFESTS_FOLDER"]

#         if verbosity > 0:
#             print("Manifests discovered.")

#         for filename in os.listdir(folder):
#             manifest_name = filename.replace(".yml", "")

#             # Handle manifest restriction
#             if restrict_manifest_test is not None and restrict_manifest != manifest_name:
#                 continue
#             self.logger.debug(f"{folder}/{filename}")

#             # Parse manifest
#             manifest = ManifestParser.parse_yaml(os.path.join(folder, filename))
#             ttype = manifest.testtype

#             # Create backend test
#             if not skip_back and (ttype is None or ttype == "backend"):
#                 backend_test_cls = MetaBackTest(
#                     f"{manifest_name}.backend",
#                     (BackendDjangoTestCase,),
#                     manifest,
#                     restrict_test=restrict_test,
#                     restrict_view=restrict_view,
#                 )
#                 backend_tests = self.loader.loadTestsFromTestCase(backend_test_cls)
#                 # backend_parrallel_suites.append(backend_tests)
#                 backend_suite.addTests(backend_tests)

#             # Create frontend test
#             if not skip_front and (ttype is None or ttype == "frontend"):
#                 frontend_test_cls = MetaFrontTest(
#                     f"{manifest_name}.frontend",
#                     (FrontendDjangoTestCase,),
#                     manifest,
#                     restrict_test=restrict_test,
#                     restrict_view=restrict_view,
#                     headless=headless,
#                 )
#                 frontend_tests = self.loader.loadTestsFromTestCase(frontend_test_cls)
#                 # frontend_parrallel_suites.append(frontend_tests)

#                 # print(frontend_tests)
#                 frontend_suite.addTests(frontend_tests)

#         # msg = f"Resulting in {len(backend_suite._tests)} backend and {len(frontend_suite._tests)} frontend tests."
#         n_backend_tests = sum(len(test_suite._tests) for test_suite in backend_parrallel_suites)
#         n_fonrtend_tests = sum(len(test_suite._tests) for test_suite in frontend_parrallel_suites)
#         msg = f"Resulting in {n_backend_tests} backend and {n_fonrtend_tests} frontend tests."

#         if verbosity >= 1:
#             print(f"{msg}\n")
#         return backend_suite, frontend_suite
#         # return backend_parrallel_suites, frontend_parrallel_suites


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

    def __init__(self, failfast: bool=False) -> None:
        """Initialize the MetaTestRunner with a runner, logger, discoverer, and output stream."""
        self.logger = logging.getLogger(__package__)
        self.stream = io.StringIO()
        # self.stream = sys.stdout
        self.runner = CustomDiscoverRunner(stream=self.stream, failfast=failfast)

        app_logger = logging.getLogger("app.close_watch")
        app_logger.propagate = False

    def __del__(self) -> None:
        """Clean up resources when the MetaTestRunner is deleted."""
        # TODO mad: a context manager would be ideal, let's wait v2
        # self.stream.close()
        app_logger = logging.getLogger("app.close_watch")
        app_logger.propagate = True

    def run(self, tests_discovered: unittest.TestSuite, verbosity: int) -> unittest.TestResult:
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


class TestsLoader:
    """
    A class for discovering and loading test cases from manifest files.

    This class scans a directory for manifest files, creates test classes from these manifests,
    and loads the tests into test suites.

    Attributes:
        logger (Logger): A logger instance for this class.
        runner (DiscoverRunner): A Django test runner instance.
        loader (TestLoader): A test loader instance from the runner.
    """

    folder = os.environ["SCENERY_MANIFESTS_FOLDER"]
    logger = logging.getLogger(__package__)
    runner = get_runner(settings, test_runner_class="django.test.runner.DiscoverRunner")()
    loader: unittest.loader.TestLoader = runner.test_loader

    def tests_from_manifest(
        self,
        filename: str,
        only_back: bool=False,
        only_front: bool=False,
        only_view: str | None=None,
        timeout_waiting_time: int=5,
        only_case_id: str | None=None,
        only_scene_pos: str | None=None,
        driver: webdriver.Chrome | None = None,
        headless: bool=True,
    ) -> Tuple[unittest.TestSuite, unittest.TestSuite]:
        """Creates test suites from a manifest file for both backend and frontend testing.

        Parses a YAML manifest file and generates corresponding test suites for backend
        and frontend testing. Tests can be filtered based on various criteria like test type,
        specific views, or test cases.

        Args:
            filename (str): The name of the YAML manifest file to parse.
            only_back (bool, optional): Run only backend tests. Defaults to False.
            only_front (bool, optional): Run only frontend tests. Defaults to False.
            only_view (str, optional): Filter tests to run only for a specific view. Defaults to None.
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
        # NOTE mad: this is here to be able to load driver in two places
        # See also scenery/__main__.py
        # Probably not a great pattern but let's fix this later
        if driver is None:
            driver = get_selenium_driver(headless=headless)

        backend_suite, frontend_suite = unittest.TestSuite(), unittest.TestSuite()

        # Parse manifest
        manifest = ManifestParser.parse_yaml(os.path.join(self.folder, filename))
        ttype = manifest.testtype
        manifest_name = filename.replace(".yml", "")

        # Create backend test
        if not only_front and (ttype is None or ttype == "backend"):
            backend_test_cls = MetaBackTest(
                f"{manifest_name}.backend",
                (BackendDjangoTestCase,),
                manifest,
                only_case_id=only_case_id,
                only_scene_pos=only_scene_pos,
                only_view=only_view,
            )
            # FIXME mad: type hinting mislead by metaclasses
            backend_tests = self.loader.loadTestsFromTestCase(backend_test_cls) # type: ignore[arg-type]
            backend_suite.addTests(backend_tests)

        # Create frontend test
        if not only_back and (ttype is None or ttype == "frontend"):
            frontend_test_cls = MetaFrontTest(
                f"{manifest_name}.frontend",
                (FrontendDjangoTestCase,),
                manifest,
                only_case_id=only_case_id,
                only_scene_pos=only_scene_pos,
                only_view=only_view,
                timeout_waiting_time=timeout_waiting_time,
                driver=driver,
                # headless=True,
            )
            # FIXME mad: type hinting mislead by metaclasses
            frontend_tests = self.loader.loadTestsFromTestCase(frontend_test_cls) # type: ignore[arg-type]
            frontend_suite.addTests(frontend_tests)

        return backend_suite, frontend_suite


def process_manifest(filename: str, args: argparse.Namespace, driver: webdriver.Chrome | None) -> Tuple[bool, dict, bool, dict]:
    """Process a test manifest file and executes both backend and frontend tests.

    Takes a manifest file and command line arguments to run the specified tests,
    collecting and summarizing the results for both backend and frontend test suites.

    Args:
        filename (str): The name of the YAML manifest file to process.
        args (argparse.Namespace): Command line arguments containing:
            - only_back (bool): Run only backend tests
            - only_front (bool): Run only frontend tests
            - only_view (str): Filter for specific view
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
    manifest_name = filename.replace(".yml", "")
    print(f"\n{manifest_name}", end=" ")

    loader = TestsLoader()
    runner = TestsRunner()

    backend_suite, frontend_suite = loader.tests_from_manifest(
        filename, 
        only_back=args.only_back, 
        only_front=args.only_front, 
        only_view=args.only_view, 
        only_case_id=args.only_case_id, 
        only_scene_pos=args.only_scene_pos, 
        timeout_waiting_time=args.timeout_waiting_time, 
        driver = driver,
        headless=args.headless,
    )


    backend_result = runner.run(backend_suite, verbosity=0)
    backend_success, backend_summary = summarize_test_result(backend_result, verbosity=0)

    frontend_result = runner.run(frontend_suite, verbosity=0)
    frontend_success, frontend_summary = summarize_test_result(frontend_result, verbosity=0)

    return backend_success, backend_summary, frontend_success, frontend_summary
