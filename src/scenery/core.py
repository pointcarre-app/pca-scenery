"""Build the tests from the Manifest, discover & run tests."""

import argparse
import os
import sys
# import io
from typing import Tuple #, cast, Type
import unittest

from scenery import logger
from scenery.manifest import Manifest
from scenery.method_builder import MethodBuilder
from scenery.manifest_parser import ManifestParser
from scenery.common import (
    DjangoFrontendTestCase,
    DjangoBackendTestCase,
    RemoteBackendTestCase,
    RemoteFrontendTestCase,
    LoadTestCase,
    CustomDiscoverRunner,
    # SceneryTestCase,
    get_selenium_driver,
)



from django.conf import settings
from django.test.utils import get_runner

from selenium import webdriver




# METACLASS
#######################



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
        mode: str | None = None,
        only_case_id: str | None = None,
        only_scene_pos: str | None = None,
        only_url: str | None = None,
        driver: webdriver.Chrome | None=None,
        users: int | None=None,
        requests_per_user: int | None=None,
    ) -> "MetaTest":
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

        # Build setUp and tearDown functions
        ####################################

        # NOTE mad: setUpTestData would be a pain since LoadTestCase and RemoteTestCase 
        # are not suppoesed to work with
        setUpClass = MethodBuilder.build_setUpClass(manifest.set_up_class, driver)
        setUp = MethodBuilder.build_setUp(manifest.set_up)

        cls_attrs = {
            "setUpClass": setUpClass,
            "setUp": setUp,
            "mode": mode,
        }
        if users:
            cls_attrs["users"] = users
        if requests_per_user:
            cls_attrs["requests_per_user"] = requests_per_user

        if bases == (DjangoFrontendTestCase,) or bases == (RemoteFrontendTestCase,):
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
            if bases in [
                (DjangoBackendTestCase,),
                (DjangoFrontendTestCase,),
                (RemoteBackendTestCase,),
                (RemoteFrontendTestCase,),
            ] :
                test = MethodBuilder.build_test_integration(take)
            elif bases == (LoadTestCase,):
                test = MethodBuilder.build_test_load(take)
            else:
                raise NotImplementedError(bases)
            cls_attrs.update({f"test_case_{case_id}_scene_{scene_pos}": test})

        test_cls = super().__new__(cls, clsname, bases, cls_attrs)
        return test_cls  


# TEST LOADER AND RUNNER
########################



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
    # NOTE mad: this was done to potentially shut down the original stream (see also the CustomDiscoverRunner)

    def __init__(self, failfast: bool = False) -> None:
        """Initialize the MetaTestRunner with a runner, logger, discoverer, and output stream."""

        # self.stream = io.StringIO()
        self.stream = sys.stdout
        self.runner = CustomDiscoverRunner(stream=self.stream, failfast=failfast)

    def __del__(self) -> None:
        """Clean up resources when the MetaTestRunner is deleted."""
        # NOTE mad: do not erase
        # self.stream.close()
        # print(self.stream.flush())
        # app_logger = ...
        # app_logger.propagate = True

    def run(self, tests_discovered: unittest.TestSuite | unittest.TestCase) -> unittest.TestResult:
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
        if isinstance(tests_discovered, unittest.TestCase):
            # NOTE mad: done for type checking
            tests_discovered = unittest.TestSuite((tests_discovered,))
        results = self.runner.run_suite(tests_discovered)
        return results




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

    # NOTE mad: I redefine this for multithreading possibilities
    # sadly this failed but I still think it is a better pattern


    runner = get_runner(settings, test_runner_class="django.test.runner.DiscoverRunner")()
    loader: unittest.loader.TestLoader = runner.test_loader

    @property
    def folder(self) -> str:
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
    ) -> Tuple[unittest.TestSuite, unittest.TestSuite, unittest.TestSuite, unittest.TestSuite]:
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
            - The manifest's ttype determines which suites are created (backend, frontend, or both)
            - Empty test suites are returned for disabled test types
            - The driver initialization can occur here or be passed in from external code
        """

        dev_backend_suite, dev_frontend_suite = unittest.TestSuite(), unittest.TestSuite()
        remote_backend_suite, remote_frontend_suite = unittest.TestSuite(), unittest.TestSuite()

        # Parse manifest
        manifest = ManifestParser.parse_yaml_from_file(os.path.join(self.folder, filename))
        ttype = manifest.ttype
        manifest_name = filename.replace(".yml", "")

        # NOTE mad: manifests can indicate they are not to be ran in some mode
        back &= ttype is None or ttype == "backend"
        front &= ttype is None or ttype == "frontend"

        if back and mode == "dev":
            cls = MetaTest(
                f"{manifest_name}.dev.backend",
                (DjangoBackendTestCase,),
                manifest,
                only_case_id=only_case_id,
                only_scene_pos=only_scene_pos,
                only_url=only_url,
                mode=mode,
            )
            # FIXME mad: type hinting mislead by metaclasses
            tests = self.loader.loadTestsFromTestCase(cls)  # type: ignore[arg-type]
            dev_backend_suite.addTests(tests)

        if back and mode in ["local", "staging", "prod"]:
            cls = MetaTest(
                f"{manifest_name}.remote.backend",
                (RemoteBackendTestCase,),
                manifest,
                only_case_id=only_case_id,
                only_scene_pos=only_scene_pos,
                only_url=only_url,
                mode=mode
            )

            # FIXME mad: type hinting mislead by metaclasses
            tests = self.loader.loadTestsFromTestCase(cls) # type: ignore[arg-type]
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
                driver=driver,
                mode=mode,
            )
            # FIXME mad: type hinting mislead by metaclasses
            tests = self.loader.loadTestsFromTestCase(cls)  # type: ignore[arg-type]
            dev_frontend_suite.addTests(tests)


        if front and mode in ["local", "staging", "prod"]:
            cls = MetaTest(
                f"{manifest_name}.remote.frontend",
                (RemoteFrontendTestCase,),
                manifest,
                only_case_id=only_case_id,
                only_scene_pos=only_scene_pos,
                only_url=only_url,
                driver=driver,
                mode=mode
            )

            # FIXME mad: type hinting mislead by metaclasses
            tests = self.loader.loadTestsFromTestCase(cls) # type: ignore[arg-type]
            remote_frontend_suite.addTests(tests)

        return dev_backend_suite, dev_frontend_suite, remote_backend_suite, remote_frontend_suite


    def load_tests_from_manifest(
        self,
        filename: str,
        mode: str,
        users: int,
        requests_per_user: int,
        only_url: str | None = None,
        only_case_id: str | None = None,
        only_scene_pos: str | None = None,
    ) -> unittest.TestSuite:

        test_suite = unittest.TestSuite()

        # Parse manifest
        manifest = ManifestParser.parse_yaml_from_file(os.path.join(self.folder, filename))
        manifest_name = filename.replace(".yml", "")

        cls = MetaTest(
            f"{manifest_name}.load",
            (LoadTestCase,),
            manifest,
            only_case_id=only_case_id,
            only_scene_pos=only_scene_pos,
            only_url=only_url,
            mode=mode,
            users=users,
            requests_per_user=requests_per_user
        )

        # FIXME mad: type hinting mislead by metaclasses
        tests = self.loader.loadTestsFromTestCase(cls)  # type: ignore[arg-type]
        test_suite.addTests(tests)

        return test_suite



def process_manifest_as_integration_test(
    manifest_filename: str, args: argparse.Namespace, driver: webdriver.Chrome | None
) -> dict:
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

    results: dict[str, unittest.TestResult | None] = {
        "dev_backend": None,
        "dev_frontend": None,
        "remote_backend": None,
        "remote_frontend": None,
    }

    if args.back and args.mode == "dev":
        results["dev_backend"] = runner.run(dev_backend_suite)

    if args.back and args.mode in ["local", "staging", "prod"]:
        results["remote_backend"] = runner.run(remote_backend_suite)

    if args.front and args.mode == "dev":
        results["dev_frontend"] = runner.run(dev_frontend_suite)

    if args.front and args.mode in ["local", "staging", "prod"]:
        results["remote_frontend"] = runner.run(remote_frontend_suite)

    return results


def process_manifest_as_load_test(
    manifest_filename: str, args: argparse.Namespace
) -> dict:
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
        # NOTE mad: we build the suite in order to satisfy this
        assert isinstance(test, LoadTestCase)

        test_result = runner.run(test)
        if len(test_result.errors) == 0:
            results.update(test.data)
        else:
            print(test_result.errors)
            raise Exception

    return results



