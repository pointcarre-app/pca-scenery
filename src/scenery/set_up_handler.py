"""Execute instructions used in `TestCase.setUp` and `TestCase.setUpTestData` provided in the manifest."""

import importlib
import logging
import os

import scenery.manifest

import django.test
from django.contrib.staticfiles.testing import StaticLiveServerTestCase


class SetUpHandler:
    """Responsible for executing instructions used in `TestCase.setUp` and `TestCase.setUpTestData` provided in the manifest.

    This class dynamically imports and executes setup instructions specified in the test manifest.
    It is typically used by the MethodBuilder to construct setup methods for test cases.

    Attributes:
        module: The imported module containing setup instruction implementations.
        logger: A logger instance for debug output.
    """

    instructions_module = importlib.import_module(os.environ["SCENERY_SET_UP_INSTRUCTIONS"])
    # selenium_module = importlib.import_module(os.environ["SCENERY_SET_UP_INSTRUCTIONS_SELENIUM"])

    @staticmethod
    def exec_set_up_instruction(
        # NOTE: it either takes the instance or the class
        # depending whether it is class method or not
        # (setUp vs. setUpTestData)
        django_testcase: django.test.TestCase | type[django.test.TestCase] | StaticLiveServerTestCase | type[StaticLiveServerTestCase],
        instruction: scenery.manifest.SetUpInstruction,
    ) -> None:
        """Execute the method corresponding to the SetUpInstruction.

        This method dynamically retrieves and executes the setup function specified
        by the SetUpInstruction. It logs the execution for debugging purposes.

        Args:
            django_testcase (django.test.TestCase): The Django test case instance.
            instruction (scenery.manifest.SetUpInstruction): The setup instruction to execute.

        Raises:
            AttributeError: If the specified setup function is not found in the imported module.
        """

        # if isinstance(django_testcase, django.test.TestCase) or (isinstance(django_testcase, type) and issubclass(django_testcase, django.test.TestCase)):
        #     func = getattr(SetUpHandler.http_module, instruction.command)
        #     func(django_testcase, **instruction.args)

        # elif isinstance(django_testcase, StaticLiveServerTestCase) or (isinstance(django_testcase, type) and issubclass(django_testcase, StaticLiveServerTestCase)):
        #     # TODO: this is not needed anymore I think
        #     try:
        #         func = getattr(SetUpHandler.selenium_module, instruction.command)
        #     except AttributeError as e1:
        #         try:
        #             func = getattr(SetUpHandler.http_module, instruction.command)
        #         except AttributeError  as e2:
        #             raise ExceptionGroup("", [e1, e2])
        #     func(django_testcase, **instruction.args)
               
            

        # else:
        #     raise ValueError

        func = getattr(SetUpHandler.instructions_module, instruction.command)
        func(django_testcase, **instruction.args)


        logger = logging.getLogger(__package__)
        logger.debug(f"Applied {instruction}")
