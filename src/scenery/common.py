"""General functions and classes used by other modules."""
from collections import Counter

import io
import logging
import re
import typing
import unittest
from typing import TypeVar, Union

import django
from django.test.runner import DiscoverRunner as DjangoDiscoverRunner
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.chrome.service import Service

import yaml


###################
# SELENIUM
###################

def get_selenium_driver(headless: bool) -> webdriver.Chrome:
    """Return a Selenium WebDriver instance configured for Chrome."""
    chrome_options = Options()
    # NOTE mad: service does not play well with headless mode
    # service = Service(executable_path='/usr/bin/google-chrome')
    if headless:
        chrome_options.add_argument("--headless=new")     # NOTE mad: For newer Chrome versions
        # chrome_options.add_argument("--headless")           # NOTE mad: For older Chrome versions (Framework)
    driver = webdriver.Chrome(options=chrome_options) #  service=service
    driver.implicitly_wait(10)
    return driver


# CLASSES
#########

class BackendDjangoTestCase(django.test.TestCase):
    """A Django TestCase for backend testing."""

class FrontendDjangoTestCase(StaticLiveServerTestCase):
    """A Django TestCase for frontend testing."""

    driver: webdriver.Chrome


DjangoTestCaseTypes = Union[BackendDjangoTestCase, FrontendDjangoTestCase]
DjangoTestCase = TypeVar('DjangoTestCase', bound=DjangoTestCaseTypes)       


class ResponseProtocol(typing.Protocol):
    """A protocol for HTTP responses, covering both basic Django http response and from Selenium Driver."""
    
    @property
    def status_code(self) -> int:
        """The HTTP status code of the response."""

    @property
    def headers(self) -> typing.Mapping[str, str]:
        """The headers of the response."""

    @property
    def content(self) -> typing.Any: 
        """The content of the response."""

    @property
    def charset(self) -> str | None: 
        """The charset of the response."""

    def has_header(self, header_name: str) -> bool: 
        """Check if the response has a specific header."""
    
    def __getitem__(self, header_name: str) -> str: ...

    def __setitem__(self, header_name: str, value: str) -> None: ...




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
    # TODO: there must be an even more built-in solution
    s = s.replace("/", "_")
    s = s.replace("-", "")
    if not re.fullmatch(r"[a-z0-9_]+", s):
        raise ValueError(f"'{s}' is not snake_case")
    words = s.split("_")
    camel_case = "".join(word.capitalize() for word in words)
    return camel_case


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



def summarize_test_result(result: unittest.TestResult, test_label) -> tuple[bool, Counter]:
    """Return true if the tests all succeeded, false otherwise."""

    for failed_test, traceback in result.failures:
        test_name = failed_test.id()
        emojy, msg, color, log_lvl = interpret(False)
        logging.log(log_lvl, f"[{color}]{test_name} {msg}[/{color}]\n{traceback}")


    for failed_test, traceback in result.errors:
        test_name = failed_test.id()
        emojy, msg, color, log_lvl = interpret(False)
        logging.log(log_lvl, f"[{color}]{test_name} {msg}[/{color}]\n{traceback}")

    success = True
    summary = serialize_unittest_result(result)
    if summary["errors"] > 0 or summary["failures"] > 0:
        success = False

    emojy, msg, color, log_lvl = interpret(success)

    msg = f"[{color}]{test_label} {msg}[/{color}]"
    logging.log(log_lvl, msg)


    return success, summary


def interpret(success):
    if success:
        emojy, msg, color, log_lvl = "🟢", "passed", "green", logging.INFO
    else:
        emojy, msg, color, log_lvl = "❌", "failed", "red", logging.ERROR
    return emojy, msg, color, log_lvl



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


    # def __del__(self):
    #     print("HEHEHE")
    #     print(self.stream.getvalue())

    def get_test_runner_kwargs(self) -> dict[str, typing.Any]:
        """Overwrite the original from django.test.runner.DiscoverRunner."""
        return overwrite_get_runner_kwargs(self, self.stream)
