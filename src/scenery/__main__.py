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


def main(settings_module:str | None=None) -> int:
    """
    Execute the main functionality of the scenery test runner.

    Returns:
        exit_code (int): Exit code indicating success (0) or failure (1)
    """

    out: dict[str, dict[str, int | str | dict[str, Any]]] = {}

    from scenery.common import parse_args, tabulate, colorize, scenery_setup, django_setup
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
            "stdlib": sysconfig.get_paths()["stdlib"],
            "purelib": sysconfig.get_paths()["purelib"],
            "scenery": __package__,
        }
    )

    #############
    # METATESTING
    #############

    from scenery.core import process_manifest

    # NOTE mad: this is here to be able to load driver in two places
    # See also core.TestsLoader.tests_from_manifest.
    # Probably not a great pattern but let's fix this later

    # driver = get_selenium_driver(headless=args.headless)
    driver = None



    folder = os.environ["SCENERY_MANIFESTS_FOLDER"]
    results = []
    for filename in os.listdir(folder):

        if args.only_manifest is not None and filename.replace(".yml", "") != args.only_manifest:
            continue
        
        result = process_manifest(filename, args=args, driver=driver)
        results.append(result)

    overall_backend_success, overall_frontend_success = True, True
    overall_backend_summary: CounterType[str] = Counter()
    overall_frontend_summary: CounterType[str] = Counter()
    for backend_success, backend_summary, frontend_success, frontend_summary in results:
        overall_backend_success &= backend_success
        overall_frontend_success &= frontend_success
        overall_frontend_summary.update(frontend_summary)
        overall_backend_summary.update(backend_summary)

    # TODO mad: this should be with summarize no ?
    # TODO mad: make it rich

    if not args.only_front:
        if overall_backend_success:
            log_lvl, msg, color = logging.INFO,  "\n🟢 BACKEND OK", "green"
        else:
            log_lvl, msg, color = logging.ERROR, "\n❌ BACKEND FAIL", "red"
        log_lvl # NOTE mad: temporary fix for ruff as it is unused yet

        print(f"\nSummary:\n{tabulate(overall_backend_summary)}\n")
        print(f"{colorize(color, msg)}\n\n")

    if not args.only_back:
        if overall_frontend_success:
            log_lvl, msg, color = logging.INFO,  "\n🟢 FRONTEND OK", "green" # ignore[assignement]
        else:
            log_lvl, msg, color = logging.ERROR, "\n❌ FRONTEND FAIL", "red"

        print(f"\nSummary:\n{tabulate(overall_frontend_summary)}\n")
        print(f"{colorize(color, msg)}\n\n")


    # ###############
    # # OUTPUT RESULT
    # ###############

    # if args.output is not None:
    #     import json

    #     with open(args.output, "w") as f:
    #         json.dump(out, f)

    ###################
    # Exit code
    ###################
    
    success = min(int(overall_backend_success), int(overall_frontend_success),)
    exit_code = 1 - success

    if not args.only_front and not args.only_back:
        if success:
            msg, color = "\n\n🟢 BOTH BACKEND AND FRONTEND WENT FINE", "green"
        else:
            msg, color = "\n\n❌ EITHER BACKEND OR FRONTEND FAILED", "red"

        print(f"{colorize(color, msg)}\n\n")

    return exit_code


if __name__ == "__main__":

    exit_code = main()
    sys.exit(exit_code)
