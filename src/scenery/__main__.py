"""Run the testing routing based on the `scenery` settings.

See: `python -m scenery --help`
"""

# TODO mad: this function is never executed during testing

import sys
import typing
import os
from multiprocessing import Pool
from collections import Counter
import logging


def process_manifest(filename, args):

    print(f"\n{filename}", end="")

    loader = TestsLoader()
    runner = TestsRunner()

    backend_suite, frontend_suite = loader.tests_from_manifest(filename, skip_back=args.skip_back, skip_front=args.skip_front, restrict_view=args.restrict_view)

    backend_result = runner.run(backend_suite, verbosity=0)
    backend_success, backend_summary = scenery.common.summarize_test_result(backend_result, verbosity=0)

    frontend_result = runner.run(frontend_suite, verbosity=0)
    frontend_success, frontend_summary = scenery.common.summarize_test_result(frontend_result, verbosity=0)

    # TODO mad: number of tests
    # msg = f"Resulting in {len(backend_suite._tests)} backend and {len(frontend_suite._tests)} frontend tests."
    # n_backend_tests = sum(len(test_suite._tests) for test_suite in backend_parrallel_suites)
    # n_fonrtend_tests = sum(len(test_suite._tests) for test_suite in frontend_parrallel_suites)
    # msg = f"Resulting in {n_backend_tests} backend and {n_fonrtend_tests} frontend tests."

    # if verbosity >= 1:
    #     print(f"{msg}\n")

    return backend_success, backend_summary, frontend_success, frontend_summary

def parse_args():

    #################
    # PARSE ARGUMENTS
    #################

    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--restrict-test",
        nargs="?",
        default=None,
        help="Optional test restriction <manifest>.<case>.<scene>",
        dest="restrict_manifest_test"
    )


    parser.add_argument(
        "--restrict-view",
        nargs="?",
        default=None,
        help="Optional test restriction <manifest>.<case>.<scene>",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbosity",
        type=int,
        default=2,
        help="Verbose output",
    )

    parser.add_argument(
        "-s",
        "--scenery_settings",
        dest="scenery_settings_module",
        type=str,
        default="scenery_settings",
        help="Location of scenery settings module",
    )

    parser.add_argument(
        "-ds",
        "--django_settings",
        dest="django_settings_module",
        type=str,
        default=None,
        help="Location of django settings module",
    )

    parser.add_argument('--failfast', action='store_true')
    parser.add_argument('--skip-back', action='store_true')
    parser.add_argument('--skip-front', action='store_true')

    # parser.add_argument(
    #     "--output",
    #     default=None,
    #     dest="output",
    #     action="store",
    #     help="Export output",
    # )

    args = parser.parse_args()
    return args

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

    folder = os.environ["SCENERY_MANIFESTS_FOLDER"]
    results = []
    for filename in os.listdir(folder):
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

    if overall_backend_success:
        log_lvl, msg, color = logging.INFO,  "\n🟢 BACKEND OK", "green"
    else:
        log_lvl, msg, color = logging.ERROR, "\n❌ BACKEND FAIL", "red"

    print(f"\nSummary:\n{scenery.common.tabulate(overall_backend_summary)}\n")
    print(f"{scenery.common.colorize(color, msg)}\n\n")

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

    if success:
        msg, color = "\n\n🟢 SCENERY WENT FINE", "green"
    else:
        msg, color = "\n\n❌ SCENERY FAILED", "red"

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

    from scenery.metatest import TestsLoader, TestsRunner


    
    exit_code = main(args)
    sys.exit(exit_code)
