import os
import io
import logging
import itertools
import unittest
import typing

from scenery.manifest import Manifest
from scenery.method_builder import MethodBuilder
from scenery.manifest_parser import ManifestParser
import scenery.common

import django.test
from django.test.utils import get_runner

from django.conf import settings


##############################
# META TESTING
##############################


class MetaTest(type):
    """
    A metaclass for creating test classes dynamically based on a Manifest.

    This metaclass creates test methods for each combination of case and scene in the manifest,
    and adds setup methods to the test class.

    Args:
        clsname (str): The name of the class being created.
        bases (tuple): The base classes of the class being created.
        manifest (Manifest): The manifest containing test cases and scenes.
        restrict (str, optional): A string to restrict which tests are created, in the format "case_id.scene_pos".

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
        restrict: typing.Optional[str] = None,
    ) -> "MetaTest":
        if restrict is not None:
            restrict_args = restrict.split(".")
            if len(restrict_args) == 1:
                restrict_case_id, restrict_scene_pos = restrict_args[0], None
            elif len(restrict_args) == 2:
                restrict_case_id, restrict_scene_pos = restrict_args[0], restrict_args[1]
            else:
                raise ValueError(f"Wrong restrict argmuent {restrict}")

        # Build setUpTestData and SetUp
        setUpTestData = MethodBuilder.build_setUpTestData(manifest.set_up_test_data)
        setUp = MethodBuilder.build_setUp(manifest.set_up)

        # Add SetupData and SetUp as methods of the Test class
        cls_attrs = {
            "setUpTestData": setUpTestData,
            "setUp": setUp,
        }

        for (case_id, case), (scene_pos, scene) in itertools.product(
            manifest.cases.items(), enumerate(manifest.scenes)
        ):
            if restrict is not None:
                if case_id != restrict_case_id:
                    continue
                elif restrict_scene_pos is not None and str(scene_pos) != restrict_scene_pos:
                    continue

            take = scene.shoot(case)
            test = MethodBuilder.build_test_from_take(take)
            cls_attrs.update({f"test_case_{case_id}_scene_{scene_pos}": test})

        return super().__new__(cls, clsname, bases, cls_attrs)


class MetaTestDiscoverer:
    """
    A class for discovering and loading test cases from manifest files.

    This class scans a directory for manifest files, creates test classes from these manifests,
    and loads the tests into test suites.

    Attributes:
        logger (Logger): A logger instance for this class.
        runner (DiscoverRunner): A Django test runner instance.
        loader (TestLoader): A test loader instance from the runner.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(__package__)
        self.runner = get_runner(settings, test_runner_class="django.test.runner.DiscoverRunner")()
        self.loader = self.runner.test_loader

    def discover(
        self, restrict: typing.Optional[str] = None, verbosity: int = 2
    ) -> list[tuple[str, unittest.TestSuite]]:
        """
        Discover and load tests from manifest files.

        Args:
            restrict (str, optional): A string to restrict which manifests and tests are loaded,
                                      in the format "manifest.case_id.scene_pos".
            verbosity (int, optional): The verbosity level for output. Defaults to 2.

        Returns:
            list: A list of tuples, each containing a test name and a TestSuite with a single test.

        Raises:
            ValueError: If the restrict argument is not in the correct format.
        """

        # handle manifest/test restriction
        if restrict is not None:
            restrict_args = restrict.split(".")
            if len(restrict_args) == 1:
                restrict_manifest, restrict_test = (
                    restrict_args[0],
                    None,
                )
            elif len(restrict_args) == 2:
                restrict_manifest, restrict_test = (restrict_args[0], restrict_args[1])
            elif len(restrict_args) == 3:
                restrict_manifest, restrict_test = (
                    restrict_args[0],
                    restrict_args[1] + "." + restrict_args[2],
                )
        else:
            restrict_manifest, restrict_test = None, None

        out = []

        suite_cls = self.runner.test_suite

        folder = os.getenv("SCENERY_MANIFESTS_FOLDER")

        if verbosity >= 1:
            print("Manifests discovered:")

        for filename in os.listdir(folder):
            manifest_name = filename.replace(".yml", "")

            if restrict is not None and restrict_manifest != manifest_name:
                continue

            self.logger.debug(f"Discovered manifest '{folder}/{filename}'")

            manifest = ManifestParser.parse_yaml(os.path.join(folder, filename))

            # Create class
            cls = MetaTest(manifest_name, (django.test.TestCase,), manifest, restrict=restrict_test)

            # Log / verbosity
            if verbosity >= 2:
                print(f"> {cls.__qualname__}")

            # Load
            tests = self.loader.loadTestsFromTestCase(cls)
            for test in tests:
                test_name = scenery.common.pretty_test_name(test)
                suite = suite_cls()
                suite.addTest(test)
                out.append((test_name, suite))

        msg = f"Resulting in {len(out)} tests."
        if verbosity >= 1:
            print(f"{msg}\n")
        return out


class MetaTestRunner:
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

    def __init__(self) -> None:
        """Initialize the MetaTestRunner with a runner, logger, discoverer, and output stream."""

        self.runner = get_runner(settings, test_runner_class="django.test.runner.DiscoverRunner")()
        self.logger = logging.getLogger(__package__)

        self.stream = io.StringIO()

        def overwrite(runner):
            return scenery.common.overwrite_get_runner_kwargs(runner, self.stream)

        self.runner.get_test_runner_kwargs = overwrite.__get__(self.runner)
        app_logger = logging.getLogger("app.close_watch")
        app_logger.propagate = False

    def __del__(self) -> None:
        """Clean up resources when the MetaTestRunner is deleted."""
        # TODO: a context manager would be ideal, let's wait v2
        self.stream.close()
        app_logger = logging.getLogger("app.close_watch")
        app_logger.propagate = True

    def run(self, tests_discovered, verbosity) -> dict[str, dict[str, typing.Any]]:
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
        if verbosity > 0:
            print("Tests runs:")

        results = {}
        for test_name, suite in tests_discovered:
            result = self.runner.run_suite(suite)

            result_serialized = scenery.common.serialize_unittest_result(result)

            test_name = test_name.replace("test_case_", "")
            test_name = test_name.replace("_scene_", ".")

            results[test_name] = result_serialized

            if result.errors or result.failures:
                log_lvl, color = logging.ERROR, "red"
            else:
                log_lvl, color = logging.INFO, "green"
            self.logger.log(log_lvl, f"{test_name}\n{scenery.common.tabulate(result_serialized)}")
            if verbosity > 0:
                print(
                    f">> {scenery.common.colorize(color, test_name)}\n{scenery.common.tabulate({key: val for key, val in result_serialized.items() if val > 0})}"
                )

            # Log / verbosity
            for head, traceback in result.failures + result.errors:
                msg = f"{test_name}\n{head}\n{traceback}"
                self.logger.error(msg)
                if verbosity > 0:
                    print(msg)

        return results
