import importlib
import logging
import os

import scenery.manifest

import django.test


class SetUpHandler:
    """
    Responsible for executing instructions used in `TestCase.setUp` and `TestCase.setUpTestData`
    provided in the manifest.

    This class dynamically imports and executes setup instructions specified in the test manifest.
    It is typically used by the MethodBuilder to construct setup methods for test cases.

    Attributes:
        module: The imported module containing setup instruction implementations.
        logger: A logger instance for debug output.
    """

    module = importlib.import_module(
        os.getenv("SCENERY_SET_UP_INSTRUCTIONS"),
    )

    @staticmethod
    def exec_set_up_instruction(
        django_testcase: django.test.TestCase,
        instruction: scenery.manifest.SetUpInstruction,
    ):
        """
        Execute the method corresponding to the SetUpInstruction.

        This method dynamically retrieves and executes the setup function specified
        by the SetUpInstruction. It logs the execution for debugging purposes.

        Args:
            django_testcase (django.test.TestCase): The Django test case instance.
            instruction (scenery.manifest.SetUpInstruction): The setup instruction to execute.

        Raises:
            AttributeError: If the specified setup function is not found in the imported module.
        """

        func = getattr(SetUpHandler.module, instruction.command)
        func(django_testcase, **instruction.args)

        logger = logging.getLogger(__package__)
        logger.debug(f"Applied {instruction}")
