"""General functions and classes used by other modules"""

import os
import importlib
import importlib.util
import re
import types
import typing
import unittest
import numbers

import django
from django.test.runner import DiscoverRunner

import yaml

########################
# SETTINGS
########################


def scenery_setup(settings_location: str) -> None:
    """
    Read the settings module and set the corresponding environment variables.
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

    # Load from module
    settings = importlib.import_module(settings_location)

    # Env variables
    os.environ["SCENERY_COMMON_ITEMS"] = settings.SCENERY_COMMON_ITEMS
    os.environ["SCENERY_SET_UP_INSTRUCTIONS"] = settings.SCENERY_SET_UP_INSTRUCTIONS
    os.environ["SCENERY_TESTED_APP_NAME"] = settings.SCENERY_TESTED_APP_NAME
    os.environ["SCENERY_MANIFESTS_FOLDER"] = settings.SCENERY_MANIFESTS_FOLDER


########
# YAML #
########


def read_yaml(filename: str) -> typing.Any:
    """
    Read and parse a YAML file.

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
    """
    Transform a string from snake_case to CamelCase.

    This function assumes the input string is in snake_case format and converts it to CamelCase.
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


def floor(n: numbers.Real) -> int:
    """
    Return the floor of a number.

    If the input is an integer, it returns the input unchanged.
    For floating-point numbers, it returns the largest integer less than or equal to the input.

    Args:
        n (int or float): The number to floor.

    Returns:
        int: The floor of the input number.
    """
    # NOTE: this was just to avoid another dependency
    if isinstance(n, int):
        return n
    else:
        return int(n // 1)


def ceil(n: numbers.Real) -> int:
    """
    Return the ceiling of a number.

    If the input is an integer, it returns the input unchanged.
    For floating-point numbers, it returns the smallest integer greater than or equal to the input.

    Args:
        n (int or float): The number to ceil.

    Returns:
        int: The ceiling of the input number.
    """
    # NOTE: this was just to avoid another dependency
    if isinstance(n, int):
        return n
    else:
        return int(n // 1) + 1


class colorize:
    """
    A context manager for colorizing text in the console.

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
    """
    Return an ASCII table for a dictionary with columns [key, value].

    Args:
        d (dict): The dictionary to tabulate.
        color (str or callable, optional): The color to use for the values.
        delim (str, optional): The delimiter to use between keys and values. Defaults to ':'.

    Returns:
        str: A string representation of the tabulated dictionary.
    """
    width = max(len(key) for key in d.keys())
    table: list = [(key, val) for key, val in d.items()]
    if color:
        table = [(key, colorize(color, val)) for key, val in table]
    table = [("\t", key.ljust(width), delim, str(val)) for key, val in table]
    table = ["".join(line) for line in table]
    return "\n".join(table)


##################
# UNITTEST
##################


def serialize_unittest_result(result: unittest.TestResult) -> dict:
    """
    Serialize a unittest.TestResult object into a dictionary.

    Args:
        result (unittest.TestResult): The TestResult object to serialize.

    Returns:
        dict: A dictionary containing the serialized TestResult data.
    """
    d: dict = {
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
    return d


def pretty_test_name(test: unittest.TestCase) -> str:
    """
    Generate a pretty string representation of a unittest.TestCase.

    Args:
        test (unittest.TestCase): The test case to generate a name for.

    Returns:
        str: A string in the format "module.class.method" representing the test case.
    """
    return f"{test.__module__}.{test.__class__.__qualname__}.{test._testMethodName}"


###################
# DJANGO CONFIG
###################


def django_setup(settings_module: str) -> None:
    """
    Set up the Django environment.

    This function sets the DJANGO_SETTINGS_MODULE environment variable and calls django.setup().

    Args:
        settings_module (str): The import path to the Django settings module.
    """
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)
    django.setup()


###################
# DJANGO TEST
###################


def overwrite_get_runner_kwargs(django_runner: DiscoverRunner, stream: typing.IO) -> dict:
    """
    Overwrite the get_runner_kwargs method of Django's DiscoverRunner.

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
    }
    kwargs.update({"stream": stream})
    return kwargs
