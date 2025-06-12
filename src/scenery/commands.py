import argparse
import importlib
import os
from pathlib import Path
import sys
import typing


from scenery.common import summarize_test_result, interpret, iter_on_manifests
import scenery.cli
from scenery import logger


########################
# SCENERY CONFIG
########################

def scenery_setup(args: argparse.Namespace) -> bool:
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

    sys.path.append(os.path.join('.'))
    settings = importlib.import_module(args.scenery_settings_module)
    
    # Env variables
    os.environ["SCENERY_COMMON_ITEMS"] = settings.SCENERY_COMMON_ITEMS
    os.environ["SCENERY_SET_UP_INSTRUCTIONS"] = settings.SCENERY_SET_UP_INSTRUCTIONS
    os.environ["SCENERY_POST_REQUESTS_INSTRUCTIONS_SELENIUM"] = (
        settings.SCENERY_POST_REQUESTS_INSTRUCTIONS_SELENIUM
    )
    os.environ["SCENERY_TESTED_APP_NAME"] = settings.SCENERY_TESTED_APP_NAME
    os.environ["SCENERY_MANIFESTS_FOLDER"] = settings.SCENERY_MANIFESTS_FOLDER

    emojy, msg, color, log_lvl = interpret(True)
    logger.info("scenery set-up", style=color)
    
    return True

###################
# DJANGO CONFIG
###################

def django_setup(args: argparse.Namespace) -> bool:
    """Set up the Django environment.

    This function sets the DJANGO_SETTINGS_MODULE environment variable and calls django.setup().

    Args:
        settings_module (str): The import path to the Django settings module.
    """
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", args.django_settings_module)
    logger.debug(f"{os.environ.get('DJANGO_SETTINGS_MODULE')=}")
    django.setup()

    
    from django.conf import settings as django_settings
    logger.debug(f"{django_settings.INSTALLED_APPS=}")

    emojy, msg, color, log_lvl = interpret(True)
    logger.log(log_lvl, "django set-up", style=color)
    
    return True


###################
# INTEGRATION TESTS
###################

def integration_tests(args: argparse.Namespace) -> bool:
    """
    Execute the main functionality of the scenery test runner.

    Returns:
        exit_code (int): Exit code indicating success (0) or failure (1)
    """
    # NOTE mad: this needs to be loaded afeter scenery_setup and django_setup
    from scenery.core import process_manifest_as_integration_test


    # FIXME mad: this is here to be able to load driver in two places
    # See also core.TestsLoader.tests_from_manifest.
    # Probably not a great pattern but let's fix this later
    # driver = get_selenium_driver(headless=args.headless)
    driver = None

    report_data  : dict[str, typing.List[typing.Tuple[bool, dict]]] = {
        "dev_backend": [],
        "dev_frontend": [],
        "remote_backend": [],
        "remote_frontend": []
    }


    for filename in iter_on_manifests(args):
        
        results = process_manifest_as_integration_test(filename, args=args, driver=driver)

        for key, val in results.items():
            if val:
                success, summary = summarize_test_result(val, key.replace("_", "-"))
                report_data[key].append((success, summary))

    success = scenery.cli.report_integration(report_data)

    return success



###################
# LOAD TESTS
###################

def load_tests(args: argparse.Namespace) -> bool:
    # NOTE mad: this needs to be loaded after scenery_setup and django_setup
    from scenery.core import process_manifest_as_load_test

    success = True
    report_data : dict[str, typing.List] = {}

    for filename in iter_on_manifests(args):        
        results = process_manifest_as_load_test(filename, args=args)
        file_level_success = scenery.cli.report_load(results)
        report_data.update(results)
        success &= file_level_success

    return success


###################
# CODE
###################

def inspect_code(args: argparse.Namespace) -> bool:
    from scenery.inspect_code import count_line_types

    report_data = {}

    # Get all files recursively
    folder = Path(args.folder)

    # TODO: just the directory (make option)

    # All files
    for file_path in folder.rglob('*.py'):
        if file_path.is_file():
            report_data[str(file_path)] = count_line_types(file_path)

    success = scenery.cli.report_inspect(report_data)

    return success

