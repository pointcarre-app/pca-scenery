from collections import Counter
import importlib
import os
import logging
# from typing import Any
from typing import Counter as CounterType
import sys
import sysconfig

from rich.console import Console
from rich.rule import Rule
from rich.panel import Panel

# import scenery.cli
from scenery.common import summarize_test_result, interpret



########################
# SCENERY CONFIG
########################

# @scenery.cli.command
def scenery_setup(setting_module) -> None:
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

    # TODO mad: we choose convention over verification here
    # settings = importlib.import_module("rehearsal.scenery_settings")
    if setting_module == "rehearsal.scenery_settings":
        sys.path.append(os.path.join('.'))
    settings = importlib.import_module(setting_module)
    
    # Env variables
    os.environ["SCENERY_COMMON_ITEMS"] = settings.SCENERY_COMMON_ITEMS
    os.environ["SCENERY_SET_UP_INSTRUCTIONS"] = settings.SCENERY_SET_UP_INSTRUCTIONS
    os.environ["SCENERY_POST_REQUESTS_INSTRUCTIONS_SELENIUM"] = (
        settings.SCENERY_POST_REQUESTS_INSTRUCTIONS_SELENIUM
    )
    os.environ["SCENERY_TESTED_APP_NAME"] = settings.SCENERY_TESTED_APP_NAME
    os.environ["SCENERY_MANIFESTS_FOLDER"] = settings.SCENERY_MANIFESTS_FOLDER

    emojy, msg, color, log_lvl = interpret(True)
    logging.log(log_lvl, f"[{color}]scenery_setup {msg}[/{color}]")
    

    return (
        True, 
        {
            "stdlib": sysconfig.get_paths()["stdlib"],
            "purelib": sysconfig.get_paths()["purelib"],
        }
    )

###################
# DJANGO CONFIG
###################

# @scenery.cli.command
def django_setup(settings_module: str) -> int:
    """Set up the Django environment.

    This function sets the DJANGO_SETTINGS_MODULE environment variable and calls django.setup().

    Args:
        settings_module (str): The import path to the Django settings module.
    """

    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)
    django.setup()

    emojy, msg, color, log_lvl = interpret(True)
    logging.log(log_lvl, f"[{color}]django_setup {msg}[/{color}]")
    
    return True, {}






# @scenery.cli.command
def integration_tests(args) -> int:
    """
    Execute the main functionality of the scenery test runner.

    Returns:
        exit_code (int): Exit code indicating success (0) or failure (1)
    """

    console = Console()

    # NOTE mad: this needs to be loaded afeter scenery_setup and
    from scenery.core import process_manifest


    # FIXME mad: this is here to be able to load driver in two places
    # See also core.TestsLoader.tests_from_manifest.
    # Probably not a great pattern but let's fix this later
    # driver = get_selenium_driver(headless=args.headless)
    driver = None

    folder = os.environ["SCENERY_MANIFESTS_FOLDER"]
    overall_backend_success, overall_frontend_success = True, True
    overall_backend_summary: CounterType[str] = Counter()
    overall_frontend_summary: CounterType[str] = Counter()

    for filename in os.listdir(folder):

        if args.only_manifest is not None and filename.replace(".yml", "") != args.only_manifest:
            continue
        
        backend_result, frontend_result = process_manifest(filename, args=args, driver=driver)
        backend_success, backend_summary = summarize_test_result(backend_result, "backend")
        frontend_success, frontend_summary = summarize_test_result(frontend_result, "frontend")

        overall_backend_success &= backend_success
        overall_frontend_success &= frontend_success
        overall_frontend_summary.update(frontend_summary)
        overall_backend_summary.update(backend_summary)

        # results.append((filename, result))

    #############
    # OUTPUT
    #############

    panel_msg = ""
    panel_color = "green"

    if not args.only_front:
        emojy, msg, color, log_lvl = interpret(overall_backend_success)
        if overall_backend_success:
            msg = f"all backend tests {msg}"
        else:
            msg = f"some backend tests {msg}"
            panel_color = "red"
        
        logging.log(log_lvl, f"[{color}]{msg}[/{color}]")
        panel_msg += f"{emojy} {msg}"

    


    if not args.only_back:
        emojy, msg, color, log_lvl = interpret(overall_frontend_success)
        if overall_frontend_success:
            msg = f"all frontend tests {msg}"
        else:
            msg = f"some frontend tests {msg}"
            panel_color = "red"
            
        logging.log(log_lvl, f"[{color}]{msg}[/{color}]")
        panel_msg += f"\n{emojy} {msg}"

    




    # if not args.only_back:
    #     rich_tabulate(overall_backend_summary, "backend", "")
    # if not args.only_back:
    #     rich_tabulate(overall_frontend_summary, "frontend", "")



    ###################
    # Exit code
    ###################
    overall_success = overall_backend_success and overall_frontend_success
    emojy, msg, color, log_lvl = interpret(overall_success)
    logging.log(log_lvl, f"[{color}]scenery {msg}[/{color}]")


    console.print(Panel(
        panel_msg,
        title="Results",
        border_style=panel_color
    ))


    console.print(Rule(f"{emojy} Scenery {msg}".upper(), style=color))

    return overall_success, {}