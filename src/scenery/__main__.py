"""Run the testing routing based on the `scenery` settings.

See: `python -m scenery --help`
"""
from collections import Counter
import os
import logging
import sys
from typing import Any
from typing import Counter as CounterType
import sysconfig

from rich.console import Console
from rich.rule import Rule
from rich.panel import Panel

def main(settings_module:str | None=None) -> int:
    """
    Execute the main functionality of the scenery test runner.

    Returns:
        exit_code (int): Exit code indicating success (0) or failure (1)
    """

    console = Console()

    console.print(Rule("[section]CONFIG SCENERY[/section]", style="cyan"))
    logging.log(logging.INFO, "Scenery start")


    out: dict[str, dict[str, int | str | dict[str, Any]]] = {}

    from scenery.common import parse_args, scenery_setup, django_setup, rich_tabulate, summarize_test_result
    args = parse_args()

    out["metadata"] = {"args": args.__dict__}
    
    if settings_module is not None:
        args.scenery_settings_module = settings_module
    scenery_setup(settings_location=args.scenery_settings_module)
    django_setup(settings_module=args.django_settings_module)

    ####################
    # SYSTEM CONFIG
    ####################

    out["metadata"].update(
        {
            "sysconfig": {
                "stdlib": sysconfig.get_paths()["stdlib"],
                "purelib": sysconfig.get_paths()["purelib"],
                "scenery": __package__,
            }
        }
    )

    #############
    # METATESTING
    #############

    rich_tabulate(out["metadata"]["sysconfig"], "sysconfig", "")

    console.print(Rule("[section]TESTING[/section]", style="cyan"))

    logging.log(logging.INFO, "Testing start")

    from scenery.core import process_manifest

    # NOTE mad: this is here to be able to load driver in two places
    # See also core.TestsLoader.tests_from_manifest.
    # Probably not a great pattern but let's fix this later

    # driver = get_selenium_driver(headless=args.headless)
    driver = None

    folder = os.environ["SCENERY_MANIFESTS_FOLDER"]
    # results = []
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

    result_msg = ""
    result_color = "green"

    if not args.only_front:
        if overall_backend_success:
            log_lvl, msg, color = logging.INFO,  "all backend tests passed", "green"
            result_msg += "🟢 "
        else:
            result_msg += "❌ "
            result_color = "red"
            log_lvl, msg, color = logging.ERROR, "some backend tests failed", "red"
        result_msg += msg + "\n"

        logging.log(log_lvl, f"[{color}]{msg}[/{color}]")

    if not args.only_back:
        if overall_frontend_success:
            log_lvl, msg, color = logging.INFO,  "all frontend tests passed", "green" 
            result_msg += "🟢 "
        else:
            result_msg += "❌ "
            result_color = "red"
            log_lvl, msg, color = logging.ERROR, "some frontend test failed", "red"
        result_msg += msg

        msg = f"[{color}]{msg}[/{color}]"
        logging.log(log_lvl, msg)



    console.print(Panel(
        result_msg,
        title="Results",
        border_style=result_color
    ))
    if not args.only_back:
        rich_tabulate(overall_backend_summary, "backend", "")
    if not args.only_back:
        rich_tabulate(overall_frontend_summary, "frontend", "")

    # if args.output is not None:
    #     import json

    #     with open(args.output, "w") as f:
    #         json.dump(out, f)

    ###################
    # Exit code
    ###################
    
    success = min(int(overall_backend_success), int(overall_frontend_success),)
    exit_code = 1 - success

    if success:
        log_lvl, msg, color = logging.INFO, "scenery passed", "green"
        result_msg = "🟢 " + msg
    else:
        log_lvl, msg, color = logging.ERROR, "scenery failed", "red"
        result_msg = "❌ " + msg

    logging.log(log_lvl, f"[{color}]{msg}[/{color}]")

    console.print(Rule(result_msg.upper(), style=color))

    return exit_code


if __name__ == "__main__":

    exit_code = main()
    sys.exit(exit_code)
