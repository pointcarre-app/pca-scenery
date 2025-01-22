from collections import Counter
import logging
import unittest

def main() -> int:
    """Test the package `scenery` itself."""

    # NOTE mad: I first run rehearsal per se
    # then check that the main command works
    # by running the test I created 
    # for the dummy django app

    # Rehearsal
    ###########

    print(f"{scenery.common.colorize("cyan", "# Rehearsal")}\n")

    import rehearsal.tests
    loader = unittest.TestLoader()
    testsuites = loader.loadTestsFromModule(rehearsal.tests)
    rehearsal_tests = unittest.TestSuite()

    for testsuite in testsuites:
        rehearsal_tests.addTests(testsuite)
    rehearsal_runner = unittest.TextTestRunner(stream=sys.stdout)
    rehearsal_result = rehearsal_runner.run(rehearsal_tests)
    rehearsal_success, rehearsal_summary = scenery.common.summarize_test_result(rehearsal_result, verbosity=2)

    # Dummy django app
    ##################

    print(f"{scenery.common.colorize("cyan", "# Dummy django app")}\n")

    from scenery.core import process_manifest
    from scenery.common import parse_args

    args = parse_args()

    folder = os.environ["SCENERY_MANIFESTS_FOLDER"]
    results = []
    for filename in os.listdir(folder):
        results.append(process_manifest(filename, args=args))

    # TODO: dry with __main__
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


    # from scenery.metatest import TestsRunner, TestsDiscoverer


    # Discovery
    # metatest_discoverer = TestsDiscoverer()
    # back_suite, front_suite = metatest_discoverer.discover(verbosity=2)
    # back_suite, front_suite = metatest_discoverer.discover(verbosity=2)

    # # Running
    # metatest_runner = TestsRunner()

    # print(f"{scenery.common.colorize("cyan", "## Http")}\n")
    # back_result = metatest_runner.run(back_suite, verbosity=2)
    # backend_success = scenery.common.summarize_test_result(back_result)
    # back_success = True


    # print(f"{scenery.common.colorize("cyan", "## Selenium")}\n")
    # front_result = metatest_runner.run(front_suite, verbosity=2)
    # front_success = scenery.common.summarize_test_result(front_result)

    ###################
    # Exit code
    ###################
    
    success = min(int(rehearsal_success), int(backend_success), int(frontend_success),)
    exit_code = 1 - success

    if success:
        msg, color = "\n\n🟢 REHEARSAL WENT FINE", "green"
    else:
        msg, color = "\n\n❌ REHEARSAL FAILED", "red"

    print(f"{scenery.common.colorize(color, msg)}\n\n")

    return exit_code


if __name__ == "__main__":

    import os
    import sys
    from multiprocessing import Pool


    ###################
    # CONFIG SCENERY
    ###################

    rehearsal_dir = os.path.abspath(os.path.join(__file__, os.pardir))

    print(f"REHEARSAL DIR{rehearsal_dir}\n")

    # NOTE mad: should be consistent with scenery.common.scenery_setup()
    os.environ["SCENERY_COMMON_ITEMS"] = f"{rehearsal_dir}/common_items.yml"
    os.environ["SCENERY_SET_UP_INSTRUCTIONS"] = "rehearsal.set_up_instructions"
    os.environ["SCENERY_POST_REQUESTS_INSTRUCTIONS_SELENIUM"] = "rehearsal.post_requests_instructions_selenium"
    os.environ["SCENERY_TESTED_APP_NAME"] = "some_app"
    os.environ["SCENERY_MANIFESTS_FOLDER"] = f"{rehearsal_dir}/manifests"

    ###################
    # CONFIG DJANGO
    ###################

    import scenery.common

    scenery.common.django_setup("rehearsal.django_project.django_project.settings")

    ####################
    # RUN
    ####################


    import rehearsal
    from scenery.core import TestsLoader, TestsRunner



    exit_code = main()
    sys.exit(exit_code)
