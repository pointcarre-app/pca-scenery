"""General functions and classes used by other modules."""
import argparse
from collections import Counter
import os
import importlib
import importlib.util
import io
import logging
import re
import types
import typing
import unittest
from typing import TypeVar, Union

import django
from django.test.runner import DiscoverRunner as DjangoDiscoverRunner
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

import yaml

#################
# PARSE ARGUMENTS
#################


def parse_arg_test_restriction(restrict_str):
    # TODO mad: could this be in the discoverer please? or rather argparser to give to discover as arguments
    if restrict_str is not None:
        restrict_args = restrict_str.split(".")
        if len(restrict_args) == 1:
            manifest_name, case_id, scene_pos = restrict_args[0], None, None
        elif len(restrict_args) == 2:
            manifest_name, case_id, scene_pos = restrict_args[0], restrict_args[1], None
        elif len(restrict_args) == 3:
            manifest_name, case_id, scene_pos = restrict_args[0], restrict_args[1], restrict_args[2]
        else:
            raise ValueError(f"Wrong restrict argmuent {restrict_str}")
        return manifest_name, case_id, scene_pos
    else:
        return None, None, None


def parse_args():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--restrict-test",
        nargs="?",
        default=None,
        help="Optional test restriction <manifest>.<case>.<scene>",
    )

    parser.add_argument(
        "--restrict-view",
        nargs="?",
        default=None,
        help="Optional view restriction",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbosity",
        type=int,
        default=2,
        help="Verbose output",
    )

    parser.add_argument(
        "-s",
        "--scenery_settings",
        dest="scenery_settings_module",
        type=str,
        default="scenery_settings",
        help="Location of scenery settings module",
    )

    parser.add_argument(
        "-ds",
        "--django_settings",
        dest="django_settings_module",
        type=str,
        default=None,
        help="Location of django settings module",
    )

    parser.add_argument(
        "--timeout",
        dest="timeout_waiting_time",
        type=int,
        default=5,
    )

    parser.add_argument('--failfast', action='store_true')
    parser.add_argument('--skip-back', action='store_true')
    parser.add_argument('--skip-front', action='store_true')
    parser.add_argument('--not-headless', action='store_true')

    # parser.add_argument(
    #     "--output",
    #     default=None,
    #     dest="output",
    #     action="store",
    #     help="Export output",
    # )

    args = parser.parse_args()

    args.headless = not args.not_headless

    args.restrict_manifest, args.restrict_case_id, args.restrict_scene_pos = parse_arg_test_restriction(args.restrict_test)


    return args



# CLASSES
#########

class BackendDjangoTestCase(django.test.TestCase):
    """A Django TestCase for backend testing"""

class FrontendDjangoTestCase(StaticLiveServerTestCase):
    """A Django TestCase for frontend testing"""


DjangoTestCaseTypes = Union[BackendDjangoTestCase, FrontendDjangoTestCase]
DjangoTestCase = TypeVar('DjangoTestCase', bound=DjangoTestCaseTypes)       


class ResponseProtocol(typing.Protocol):
    @property
    def status_code(self) -> int: ...

    @property
    def headers(self) -> typing.Mapping[str, str]: ...

    @property
    def content(self) -> bytes: ...

    @property
    def charset(self) -> str: ...

    def has_header(self, header_name: str) -> bool: ...

    def __getitem__(self, header_name: str) -> str: ...

    def __setitem__(self, header_name: str, value: str) -> None: ...


########################
# SETTINGS
########################


def scenery_setup(settings_location: str) -> None:
    """Read the settings module and set the corresponding environment variables.

    This function imports the specified settings module and sets environment variables
    based on its contents. The following environment variables are set:

    SCENERY_COMMON_ITEMS
    SCENERY_SET_UP_INSTRUCTIONS
    SCENERY_TESTED_APP_NAME
    SCENERY_MANIFESTS_FOLDER

    Args:
        settings_location (str): The location (import path) of the settings module.

    Raises:
        ImportError: If the settings module cannot be imported.
    """
    # TODO: at-root-folder
    # Load from module
    settings = importlib.import_module(settings_location)

    # Env variables
    os.environ["SCENERY_COMMON_ITEMS"] = settings.SCENERY_COMMON_ITEMS
    os.environ["SCENERY_SET_UP_INSTRUCTIONS"] = settings.SCENERY_SET_UP_INSTRUCTIONS
    os.environ["SCENERY_POST_REQUESTS_INSTRUCTIONS_SELENIUM"] = (
        settings.SCENERY_POST_REQUESTS_INSTRUCTIONS_SELENIUM
    )
    os.environ["SCENERY_TESTED_APP_NAME"] = settings.SCENERY_TESTED_APP_NAME
    os.environ["SCENERY_MANIFESTS_FOLDER"] = settings.SCENERY_MANIFESTS_FOLDER


########
# YAML #
########


def read_yaml(filename: str) -> typing.Any:
    """Read and parse a YAML file.

    Args:
        filename (str): The path to the YAML file to be read.

    Returns:
        Any: The parsed content of the YAML file.

    Raises:
        yaml.YAMLError: If there's an error parsing the YAML file.
        IOError: If there's an error reading the file.
    """
    with open(filename, "r") as f:
        return yaml.safe_load(f)


#######################
# STRING MANIPULATION #
#######################


def snake_to_camel_case(s: str) -> str:
    """Transform a string from snake_case to CamelCase.

    If the input string respect snake_case format, transform into camelCase format, else raises an error.
    It also handles strings containing '/' and '-' characters.

    Args:
        s (str): The input string in snake_case format.

    Returns:
        str: The input string converted to CamelCase.

    Raises:
        ValueError: If the input string is not in valid snake_case format.
    """
    s = s.replace("/", "_")
    s = s.replace("-", "")
    if not re.fullmatch(r"[a-z0-9_]+", s):
        raise ValueError(f"'{s}' is not snake_case")
    words = s.split("_")
    camel_case = "".join(word.capitalize() for word in words)
    return camel_case


##################
# TERMINAL OUTPUT
##################


class colorize:
    """A context manager for colorizing text in the console.

    This class can be used either as a context manager or called directly to wrap text in color codes.

    Attributes:
        colors (dict): A dictionary mapping color names to ANSI color codes.

    Methods:
        __init__(self, color, text=None): Initialize the colorize object.
        __enter__(self): Set the color when entering the context.
        __exit__(self, exc_type, exc_val, exc_tb): Reset the color when exiting the context.
        __str__(self): Return the colorized text if text was provided.

    Args:
        color (str or callable): The color to use, either as a string or a function that returns a color.
        text (str, optional): The text to colorize. If provided, the object can be used directly as a string.

    Raises:
        Exception: If a color mapping function is provided without text.
    """

    colors = {
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
        "white": "\033[37m",
        "reset": "\033[0m",
    }

    def __init__(self, color: str | typing.Callable, text: typing.Optional[str] = None) -> None:
        if callable(color):
            if text is None:
                raise ValueError("Cannot provide a color mapping without text")
            self.color = color(text)

        else:
            self.color = color
        self.text = text

    def __enter__(self) -> "colorize":
        print(self.colors[self.color], end="")  # Set the color
        return self  # Return context manager itself if needed

    def __exit__(
        self,
        exc_type: typing.Optional[typing.Type[BaseException]],
        exc_val: typing.Optional[BaseException],
        exc_tb: typing.Optional[types.TracebackType],
    ) -> None:
        print(self.colors["reset"], end="")  # Reset the color

    def __str__(self) -> str:
        if self.text is not None:
            return f"{self.colors[self.color]}{self.text}{self.colors['reset']}"
        else:
            return ""


def tabulate(d: dict, color: typing.Callable | str | None = None, delim: str = ":") -> str:
    """Return an ASCII table for a dictionary with columns [key, value].

    Args:
        d (dict): The dictionary to tabulate.
        color (str or callable, optional): The color to use for the values.
        delim (str, optional): The delimiter to use between keys and values. Defaults to ':'.

    Returns:
        str: A string representation of the tabulated dictionary.
    """
    if len(d) == 0:
        width = 0
    else:
        width = max(len(key) for key in d.keys())
    table: list = [(key, val) for key, val in d.items()]
    if color:
        table = [(key, colorize(color, val)) for key, val in table]
    table = [("\t", key.ljust(width), delim, str(val)) for key, val in table]
    table = ["".join(line) for line in table]
    return "\n".join(table)

# import psutil
# import time
# from datetime import datetime

# def get_chrome_memory_usage():
#     """
#     Get memory usage of all Chrome processes.
    
#     Returns:
#         dict: Dictionary containing various memory metrics in MB
#     """
#     chrome_processes = []
#     total_memory = 0
    
#     # Iterate through all running processes
#     for proc in psutil.process_iter(['name', 'memory_info']):
#         try:
#             # Check if process name contains 'chrome'
#             if 'chrome' in proc.info['name'].lower():
#                 memory = proc.info['memory_info'].rss / (1024 * 1024)  # Convert to MB
#                 chrome_processes.append({
#                     'pid': proc.pid,
#                     'memory_mb': round(memory, 2)
#                 })
#                 total_memory += memory
#         except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
#             pass
    
#     return {
#         'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
#         'total_memory_mb': round(total_memory, 2),
#         'process_count': len(chrome_processes),
#         'processes': chrome_processes
#     }


##################
# UNITTEST
##################


def serialize_unittest_result(result: unittest.TestResult) -> Counter:
    """Serialize a unittest.TestResult object into a dictionary.

    Args:
        result (unittest.TestResult): The TestResult object to serialize.

    Returns:
        dict: A dictionary containing the serialized TestResult data.
    """
    d = {
        attr: getattr(result, attr)
        for attr in [
            "failures",
            "errors",
            "testsRun",
            "skipped",
            "expectedFailures",
            "unexpectedSuccesses",
        ]
    }
    d = {key: len(val) if isinstance(val, list) else val for key, val in d.items()}
    return Counter(d)



def summarize_test_result(result, verbosity=1) -> tuple[bool, Counter]:
    """Returns true if the tests all succeded, false otherwise"""

    # logger = logging.getLogger("scenery")

    for failed_test, traceback in result.failures:
        test_name = failed_test.id()
        log_lvl, color = logging.ERROR, "red"
        print(f"\n{colorize(color, test_name)}\n{traceback}")


    for failed_test, traceback in result.errors:
        test_name = failed_test.id()
        log_lvl, color = logging.ERROR, "red"
        print(f"{colorize(color, test_name)}\n{traceback}")

    success = True
    summary = serialize_unittest_result(result)
    if summary["errors"] > 0 or summary["failures"] > 0:
        success = False

    if success:
        log_lvl, msg, color = logging.INFO, "\n🟢 OK", "green"
    else:
        log_lvl, msg, color = logging.ERROR, "\n❌ FAIL", "red"

    if verbosity > 1:
        print(f"\nSummary:\n{tabulate(summary)}\n")
    if verbosity > 0:
        print(f"{colorize(color, msg)}\n\n")

    return success, summary


###################
# DJANGO CONFIG
###################


def django_setup(settings_module: str) -> None:
    """Set up the Django environment.

    This function sets the DJANGO_SETTINGS_MODULE environment variable and calls django.setup().

    Args:
        settings_module (str): The import path to the Django settings module.
    """
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)
    django.setup()


###################
# DJANGO TEST
###################


def overwrite_get_runner_kwargs(
    django_runner: DjangoDiscoverRunner, stream: typing.IO
) -> dict[str, typing.Any]:
    """Overwrite the get_runner_kwargs method of Django's DiscoverRunner.

    This function is used to avoid printing Django test output by redirecting the stream.

    Args:
        django_runner (DiscoverRunner): The Django test runner instance.
        stream: The stream to redirect output to.

    Returns:
        dict: A dictionary of keyword arguments for the test runner.

    Notes:
        see django.test.runner.DiscoverRunner.get_runner_kwargs
    """
    kwargs = {
        "failfast": django_runner.failfast,
        "resultclass": django_runner.get_resultclass(),
        "verbosity": django_runner.verbosity,
        "buffer": django_runner.buffer,
        # NOTE: this is the line below that changes compared to the original
        "stream": stream,
    }
    return kwargs





# NOTE mad: this is done to shut down the original  stream of the 
class CustomDiscoverRunner(DjangoDiscoverRunner):
    """Custom test runner that allows for stream capture."""

    def __init__(self, stream: io.StringIO, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        self.stream = stream

    def get_test_runner_kwargs(self) -> dict[str, typing.Any]:
        """Overwrite the original from django.test.runner.DiscoverRunner."""
        return overwrite_get_runner_kwargs(self, self.stream)
