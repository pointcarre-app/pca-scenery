"""Build the tests from the Manifest, discover & run tests."""

import os
import io
import sys
import logging
import itertools
import unittest
import typing
from functools import wraps
import time

from scenery.manifest import Manifest
from scenery.method_builder import MethodBuilder
from scenery.manifest_parser import ManifestParser
from scenery.common import FrontendDjangoTestCase, BackendDjangoTestCase, CustomDiscoverRunner, DjangoTestCase, summarize_test_result, get_selenium_driver

from django.conf import settings
from django.test.utils import get_runner

from selenium.common.exceptions import TimeoutException
# from selenium.webdriver.common import WebDriEver
from urllib3.exceptions import MaxRetryError, NewConnectionError


# DECORATORS
############


def log_exec_bar(func):
    def wrapper(*args, **kwargs):
        out = func(*args, **kwargs)
        print(".", end="")
        return out

    # TODO mad: en esprit mais ca marche pas comme ca je crois
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


# TODO mad: screenshot on error (v2)
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


def retry_on_timeout(retries=3, delay=5):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
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

# COMMON CODE BETWEEN BACKEND AND FRONTEND METACLASS
# TODO: Dry again a little bit

def iter_on_takes_from_manifest(manifest, only_view, only_case_id, only_scene_pos):
    for (case_id, case), (scene_pos, scene) in itertools.product(
        manifest.cases.items(), enumerate(manifest.scenes)
    ):
        if only_case_id is not None and case_id != only_case_id:
            continue
        elif only_scene_pos is not None and str(scene_pos) != only_scene_pos:
            continue
        if only_view is not None and only_view != scene.url:
            continue
        yield (case_id, case), (scene_pos, scene)


# BACKEND TEST


class MetaBackTest(type):
    """
    A metaclass for creating test classes dynamically based on a Manifest.

    This metaclass creates test methods for each combination of case and scene in the manifest,
    and adds setup methods to the test class.

    Args:
        clsname (str): The name of the class being created.
        bases (tuple): The base classes of the class being created.
        manifest (Manifest): The manifest containing test cases and scenes.

    Returns:
        type: A new test class with dynamically created test methods.

    Raises:
        ValueError: If the restrict argument is not in the correct format.
    """

    def __new__(
        cls,
        clsname: str,
        bases: tuple[type],
        manifest: Manifest,
        only_case_id: typing.Optional[str] = None,
        only_scene_pos: typing.Optional[str] = None,
        only_view: typing.Optional[str] = None,
    ) -> type[DjangoTestCase]:
        """Responsible for building the TestCase class."""

        # Build setUpTestData and SetUp
        # TODO mad: do I want setUpTestData or setUpClass?
        # NOTE mad: right now everything is in the setup
        # setUpTestData = MethodBuilder.build_setUpTestData(manifest.set_up_test_data)
        setUp = MethodBuilder.build_setUp(manifest.set_up)

        # Add SetupData and SetUp as methods of the Test class
        cls_attrs = {
            # "setUpTestData": setUpTestData,
            "setUp": setUp,
        }
        for (case_id, case), (scene_pos, scene) in iter_on_takes_from_manifest(
            manifest, only_view, only_case_id, only_scene_pos
        ):
            take = scene.shoot(case)
            test = MethodBuilder.build_backend_test_from_take(take)
            test = log_exec_bar(test)
            cls_attrs.update({f"test_case_{case_id}_scene_{scene_pos}": test})

        test_cls = super().__new__(cls, clsname, bases, cls_attrs)
        return test_cls
        # # NOTE: mypy is struggling with the metaclass,
        # # I just ignore here instead of casting which does not do the trick
        # return test_cls  # type: ignore[return-value]


# FRONTEND TEST


class MetaFrontTest(type):
    def __new__(
        cls,
        clsname: str,
        bases: tuple[type],
        manifest: Manifest,
        driver,
        only_case_id: typing.Optional[str] = None,
        only_scene_pos: typing.Optional[str] = None,
        only_view: typing.Optional[str] = None,
        timeout_waiting_time: int=5,
        # headless: bool=True,
    ) -> type[FrontendDjangoTestCase]:
        """Responsible for building the TestCase class."""


        # Build setUpTestData and SetUp
        setUpClass = MethodBuilder.build_setUpClass(manifest.set_up_test_data, driver)
        setUp = MethodBuilder.build_setUp(manifest.set_up)
        tearDownClass = MethodBuilder.build_tearDownClass()

        # Add SetupData and SetUp as methods of the Test class
        # NOTE mad: setUpClass and tearDownClass are important for the driver
        cls_attrs = {
            "setUpClass": setUpClass,
            "setUp": setUp,
            "tearDownClass": tearDownClass,
        }

        for (case_id, case), (scene_pos, scene) in iter_on_takes_from_manifest(
            manifest, only_view, only_case_id, only_scene_pos
        ):
            take = scene.shoot(case)
            test = MethodBuilder.build_frontend_test_from_take(take)
            test = retry_on_timeout(delay=timeout_waiting_time)(test)
            # test = screenshot_on_error(test)
            test = log_exec_bar(test)
            cls_attrs.update({f"test_case_{case_id}_scene_{scene_pos}": test})

        test_cls = super().__new__(cls, clsname, bases, cls_attrs)

        return test_cls  


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

    def __init__(self, failfast=False) -> None:
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

    def run(self, tests_discovered: unittest.TestSuite, verbosity: int) -> dict[str, dict[str, int]]:
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
        filename,
        only_back=False,
        only_front=False,
        only_view=None,
        timeout_waiting_time=5,
        only_case_id=None,
        only_scene_pos=None,
        driver = None,
        headless=True,
    ):

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
            backend_tests = self.loader.loadTestsFromTestCase(backend_test_cls)
            # backend_parrallel_suites.append(backend_tests)
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
            frontend_tests = self.loader.loadTestsFromTestCase(frontend_test_cls)
            # frontend_parrallel_suites.append(frontend_tests)
            frontend_suite.addTests(frontend_tests)

        return backend_suite, frontend_suite


def process_manifest(filename, args, driver):

    print(f"\n{filename.replace(".yml", " ")}", end="")

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
        # driver=args.driver,
        driver = driver,
        headless=args.headless,
    )


    backend_result = runner.run(backend_suite, verbosity=0)
    backend_success, backend_summary = summarize_test_result(backend_result, verbosity=0)

    frontend_result = runner.run(frontend_suite, verbosity=0)
    frontend_success, frontend_summary = summarize_test_result(frontend_result, verbosity=0)

    return backend_success, backend_summary, frontend_success, frontend_summary
