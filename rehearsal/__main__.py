def process_manifest(filename):


    loader = TestsLoader()
    runner = TestsRunner()

    backend_suite, frontend_suite = loader.tests_from_manifest(filename)

    backend_result = runner.run(backend_suite, verbosity=0)
    backend_success, backend_summary = scenery.common.summarize_test_result(backend_result, verbosity=0)

    frontend_result = runner.run(frontend_suite, verbosity=0)
    frontend_success, frontend_summary = scenery.common.summarize_test_result(frontend_result, verbosity=0)

    # from pprint import pprint
    # print("***************", filename)
    # pprint(backend_summary)
    # pprint(frontend_summary)

    # TODO mad: number of tests
    # msg = f"Resulting in {len(backend_suite._tests)} backend and {len(frontend_suite._tests)} frontend tests."
    # n_backend_tests = sum(len(test_suite._tests) for test_suite in backend_parrallel_suites)
    # n_fonrtend_tests = sum(len(test_suite._tests) for test_suite in frontend_parrallel_suites)
    # msg = f"Resulting in {n_backend_tests} backend and {n_fonrtend_tests} frontend tests."

    # if verbosity >= 1:
    #     print(f"{msg}\n")

    return backend_success, backend_summary, frontend_success, frontend_summary

def main() -> int:
    """Test the package `scenery` itself."""


    ###################
    # RUN TESTS
    ###################

    # NOTE mad: I first run rehearsal per se
    # then check that the main command works
    # by running the test I created 
    # for the dummy django app

    # Rehearsal
    ###########

    print(f"{scenery.common.colorize("cyan", "# Rehearsal")}\n")

    
    rehearsal_discoverer = rehearsal.RehearsalDiscoverer()
    rehearsal_runner = rehearsal.RehearsalRunner()
    rehearsal_tests = rehearsal_discoverer.discover(verbosity=2)
    rehearsal_result = rehearsal_runner.run(rehearsal_tests, verbosity=2)
    rehearsal_success, rehearsal_summary = scenery.common.summarize_test_result(rehearsal_result, verbosity=2)

    # print(scenery.common.tabulate(rehearsal_summary))

    # Dummy django app
    ##################

    print(f"{scenery.common.colorize("cyan", "# Dummy django app")}\n")


    # backend_success, frontend_success = True, True
    # for filename in os.listdir(folder):
    #     manifest_backend_success, manifest_frontend_success = process_manifest(filename, verbosity=2)
    #     backend_success &= manifest_backend_success
    #     frontend_success &= manifest_frontend_success

    folder = os.environ["SCENERY_MANIFESTS_FOLDER"]
    results = []
    for filename in os.listdir(folder):
        results.append(process_manifest(filename))
    # with Pool() as pool:
    #     results = pool.map(process_manifest, os.listdir(folder))

    from collections import Counter
    import logging

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
    from scenery.metatest import TestsLoader, TestsRunner



    exit_code = main()
    sys.exit(exit_code)
