"""Run the testing routing based on the `scenery` settings.

See: `python -m scenery --help`
"""

# TODO mad: this function is never executed during testing

import sys
import typing
import os
from collections import Counter
import logging

from scenery.core import process_manifest
from scenery.common import parse_args


        


def main(args) -> int:
    """
    Execute the main functionality of the scenery test runner.

    Returns:
        exit_code (int): Exit code indicating success (0) or failure (1)
    """
    out: dict[str, dict[str, int | str | dict[str, typing.Any]]] = {}


    out["metadata"] = {"args": args.__dict__}

    ####################
    # SYSTEM CONFIG
    ####################

    import sysconfig

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

    # NOTE mad: the imports will fail if loaded before SCENERY_ENV configuration
    # from scenery.metatest import TestsRunner, TestsDiscoverer

    # discoverer = TestsDiscoverer()
    # backend_suite, frontend_suite =  discoverer.discover(
    #     verbosity=2, 
    #     restrict_manifest_test=args.restrict_manifest_test, 
    #     skip_back=args.skip_back, 
    #     skip_front=args.skip_front, 
    #     restrict_view=args.restrict_view,
    #     )
    # runner = TestsRunner(failfast=args.failfast)

    # print("BACKEND")
    # backend_result = runner.run(backend_suite, args.verbosity)
    # backend_success = scenery.common.summarize_test_result(backend_result)

    # print("FRONTEND")
    # frontend_result = runner.run(frontend_suite, args.verbosity)
    # frontend_success = scenery.common.summarize_test_result(frontend_result)
    

    # from scenery.metatest import TestsLoader, TestsRunner
    
    # folder = os.environ["SCENERY_MANIFESTS_FOLDER"]

    # backend_success, frontend_success = True, True
    # for filename in os.listdir(folder):
    #     manifest_backend_success, manifest_frontend_success = process_manifest(filename, verbosity=2)
    #     backend_success &= manifest_backend_success
    #     frontend_success &= manifest_frontend_success

    args = parse_args()

    folder = os.environ["SCENERY_MANIFESTS_FOLDER"]
    results = []
    for filename in os.listdir(folder):

        # print("HERE", filename, args.restrict_manifest)

        if args.restrict_manifest is not None and filename.replace(".yml", "") != args.restrict_manifest:
            continue

        results.append(process_manifest(filename, args=args))
        # break
    # with Pool() as pool:
    #     results = pool.map(process_manifest, os.listdir(folder))

    overall_backend_success, overall_frontend_success = True, True
    overall_backend_summary, overall_frontend_summary = Counter(), Counter()
    for backend_success, backend_summary, frontend_success, frontend_summary in results:
        overall_backend_success &= backend_success
        overall_frontend_success &= frontend_success
        overall_frontend_summary.update(frontend_summary)
        overall_backend_summary.update(backend_summary)

    if not args.skip_back:
        if overall_backend_success:
            log_lvl, msg, color = logging.INFO,  "\n🟢 BACKEND OK", "green"
        else:
            log_lvl, msg, color = logging.ERROR, "\n❌ BACKEND FAIL", "red"

        print(f"\nSummary:\n{scenery.common.tabulate(overall_backend_summary)}\n")
        print(f"{scenery.common.colorize(color, msg)}\n\n")

    if not args.skip_front:
        if overall_frontend_success:
            log_lvl, msg, color = logging.INFO,  "\n🟢 FRONTEND OK", "green"
        else:
            log_lvl, msg, color = logging.ERROR, "\n❌ FRONTEND FAIL", "red"

        print(f"\nSummary:\n{scenery.common.tabulate(overall_frontend_summary)}\n")
        print(f"{scenery.common.colorize(color, msg)}\n\n")


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

    if not args.skip_front and not args.skip_back:
        if success:
            msg, color = "\n\n🟢 BOTH BACKEND AND FRONTEND WENT FINE", "green"
        else:
            msg, color = "\n\n❌ EITHER BACKEND OR FRONTEND FAILED", "red"

        print(f"{scenery.common.colorize(color, msg)}\n\n")

    return exit_code


if __name__ == "__main__":

    args = parse_args()


    ##################
    # CONFIG SCENERY
    ##################

    import scenery.common

    scenery.common.scenery_setup(settings_location=args.scenery_settings_module)

    #####################
    # CONFIG DJANGO
    #####################

    scenery.common.django_setup(settings_module=args.django_settings_module)

    from scenery.core import TestsLoader, TestsRunner


    
    exit_code = main(args)
    sys.exit(exit_code)
