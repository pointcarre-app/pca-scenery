import unittest
import sys
# import typing 

def main() -> int:
    """Test the package `scenery` itself."""

    # NOTE mad: I first run rehearsal per se
    # then check that the main command works
    # by running the test I created 
    # for the dummy django app


    ###################
    # CONFIG SCENERY
    ###################

    # NOTE mad: should be consistent with scenery.common.scenery_setup()
    # TODO: remove and use root-folder
    # os.environ["SCENERY_COMMON_ITEMS"] = f"{rehearsal_dir}/common_items.yml"
    # os.environ["SCENERY_SET_UP_INSTRUCTIONS"] = "rehearsal.set_up_instructions"
    # os.environ["SCENERY_POST_REQUESTS_INSTRUCTIONS_SELENIUM"] = "rehearsal.post_requests_instructions_selenium"
    # os.environ["SCENERY_TESTED_APP_NAME"] = "some_app"
    # os.environ["SCENERY_MANIFESTS_FOLDER"] = f"{rehearsal_dir}/manifests"
    # rehearsal_dir = os.path.abspath(os.path.join(__file__, os.pardir))
    # print(f"REHEARSAL DIR{rehearsal_dir}\n")

    from scenery.common import django_setup, scenery_setup, colorize, summarize_test_result

    scenery_setup("rehearsal.scenery_settings")

    django_setup("rehearsal.django_project.django_project.settings")

    ####################
    # RUN
    ####################


    # Rehearsal
    ###########

    print(f"{colorize('cyan', '# Rehearsal')}\n")

    # import rehearsal
    import rehearsal.tests
    loader = unittest.TestLoader()
    testsuites = loader.loadTestsFromModule(rehearsal.tests)
    rehearsal_tests = unittest.TestSuite()

    rehearsal_tests.addTests(testsuites)
    # for testsuite in testsuites:
        # testsuite 
        # rehearsal_tests.addTests(testsuite)
    
    rehearsal_runner = unittest.TextTestRunner(stream=None)
    rehearsal_result = rehearsal_runner.run(rehearsal_tests)
    rehearsal_success, rehearsal_summary = summarize_test_result(rehearsal_result, verbosity=2)

    # Dummy django app
    ##################

    print(f"{colorize('cyan', '# Dummy django app')}\n")

    from scenery.__main__ import main as scenery_main
    exit_code = scenery_main("rehearsal.scenery_settings")

    # TODO mad: exit_code and overall success
    return exit_code


if __name__ == "__main__":




    exit_code = main()
    sys.exit(exit_code)
