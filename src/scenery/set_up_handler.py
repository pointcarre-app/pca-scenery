"""Execute instructions used in `TestCase.setUp` and `TestCase.setUpTestData` provided in the manifest."""

import importlib
import os

from scenery import logger
from scenery.common import DjangoTestCase, RemoteBackendTestCase, LoadTestCase
from scenery.manifest import SetUpInstruction


def local_execution_only(func):
    """Simple decorator that marks function as executable"""
    func._local_execution_only = True
    return func

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
        django_testcase: DjangoTestCase | type[DjangoTestCase],
        instruction: SetUpInstruction,
    ) -> None:
        """Execute the method corresponding to the SetUpInstruction.

        This method dynamically retrieves and executes the setup function specified
        by the SetUpInstruction. It logs the execution for debugging purposes.

        Args:
            django_testcase (DjangoTestCase): The Django test case class or instance.
            instruction (scenery.manifest.SetUpInstruction): The setup instruction to execute.

        Raises:
            AttributeError: If the specified setup function is not found in the imported module.
        """
        func = getattr(SetUpHandler.instructions_module, instruction.command)


        if isinstance(django_testcase, (RemoteBackendTestCase, LoadTestCase)) and hasattr(func, "_local_execution_only"):
            pass
        else:
            logger.debug(instruction)
            func(django_testcase, **instruction.args)

