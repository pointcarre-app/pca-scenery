"""General functions and classes used by other modules."""

import argparse
from collections import Counter
import os
import logging
import typing
import unittest
from typing import TypeVar, Union
import requests

import django
from django.test.runner import DiscoverRunner as DjangoDiscoverRunner
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.chrome.service import Service

from scenery import console, logger

import yaml


###################
# SELENIUM
###################


def get_selenium_driver(headless: bool) -> webdriver.Chrome:
    """Return a Selenium WebDriver instance configured for Chrome."""
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    if headless:
        chrome_options.add_argument("--headless=new")         # NOTE mad: For newer Chrome versions
        # chrome_options.add_argument("--headless")           
    driver = webdriver.Chrome(options=chrome_options)  #  service=service
    driver.implicitly_wait(10)
    return driver


###################
# CLASSES
###################

# NOTE mad: this is here to prevent circular import and still use those types
# in reponse_checker and toher scripts for instance. 

class DjangoBackendTestCase(django.test.TestCase):
    """A Django TestCase for backend testing."""


class DjangoFrontendTestCase(StaticLiveServerTestCase):
    """A Django TestCase for frontend testing."""
    base_url: str
    driver: webdriver.Chrome

class RemoteBackendTestCase(unittest.TestCase):
    """A TestCase for backend testing on a remote server."""
    mode: str
    session: requests.Session
    base_url: str
    headers: dict[str, str]

class RemoteFrontendTestCase(unittest.TestCase):
    """A TestCase for backend testing on a remote server."""
    mode: str
    driver: webdriver.Chrome
    # session: requests.Session
    base_url: str
    headers: dict[str, str]



class LoadTestCase(unittest.TestCase):
    """A TestCase for load testing on a remote server."""
    mode: str
    session: requests.Session
    headers: dict[str, str]
    base_url: str
    data: dict[str, typing.List[dict[str, int|float]]]
    users:int
    requests_per_user:int


SceneryTestCaseTypes = Union[DjangoBackendTestCase, DjangoFrontendTestCase, RemoteBackendTestCase, RemoteFrontendTestCase, LoadTestCase]
SceneryTestCase = TypeVar("SceneryTestCase", bound=SceneryTestCaseTypes)


# NOTE mad: could be useful when we fit FastAPI
# DjangoTestCaseTypes = Union[DjangoBackendTestCase, DjangoFrontendTestCase]
# DjangoTestCase = TypeVar("DjangoTestCase", bound=DjangoTestCaseTypes)

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


def iter_on_manifests(args: argparse.Namespace) -> typing.Iterable[str]:
    for filename in os.listdir(os.environ["SCENERY_MANIFESTS_FOLDER"]):
        if args.manifest is not None and filename.replace(".yml", "") != args.manifest:
            continue

        yield filename



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


def summarize_test_result(result: unittest.TestResult, test_label: str) -> tuple[bool, Counter]:
    """Return true if the tests all succeeded, false otherwise."""
    for failed_test, traceback in result.failures:
        test_name = failed_test.id()
        emojy, msg, color, log_lvl = interpret(False)
        # logger.log(log_lvl, f"[{color}]{test_name} {msg}[/{color}]\n{traceback}")
        logger.log(log_lvl, f"{test_name} {msg}", style=color)
        # console.print_exception(
        #     exc_info=(None, None, traceback),
        #     show_locals=True
        # )
        console.print(traceback)

    for failed_test, traceback in result.errors:
        test_name = failed_test.id()
        emojy, msg, color, log_lvl = interpret(False)
        # logger.log(log_lvl, f"[{color}]{test_name} {msg}[/{color}]\n{traceback}")
        logger.log(log_lvl, f"{test_name} {msg}", style=color)
        console.print(traceback)

    success = True
    summary = serialize_unittest_result(result)
    if summary["errors"] > 0 or summary["failures"] > 0:
        success = False
    if summary["testsRun"] == 0:
        pass

    else:
        emojy, msg, color, log_lvl = interpret(success)
        msg = f"{test_label} {msg}"
        logger.log(log_lvl, msg, style=color)

    return success, summary


def interpret(success: bool) -> typing.Tuple[str, str, str, int]:
    """Return emojy, success/failure message, color and log level corresponding to the succes of an execution."""
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


class CustomDiscoverRunner(DjangoDiscoverRunner):
    """Custom test runner that allows for stream capture."""
    
    # NOTE mad: this was done to potentially shut down the original stream
    # NOTE mad: used both in rehearsal and core module (for the runner
    # TODO mad: once we fit FastAPI, this runner should only be used 
    # for the django backend and frontend test

    def __init__(self, stream: typing.Any , *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        self.stream = stream

    # def __del__(self):
    #     print(self.stream.getvalue())

    def get_test_runner_kwargs(self) -> dict[str, typing.Any]:
        """Overwrite the original from django.test.runner.DiscoverRunner."""
        return overwrite_get_runner_kwargs(self, self.stream)
