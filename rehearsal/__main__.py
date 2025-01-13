def main() -> int:
    """Test the package `scenery` itself."""

    ###################
    # CONFIG SCENERY
    ###################

    import os

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

    import rehearsal
    
    rehearsal_discoverer = rehearsal.RehearsalDiscoverer()
    rehearsal_runner = rehearsal.RehearsalRunner()
    rehearsal_tests = rehearsal_discoverer.discover(verbosity=2)
    rehearsal_result = rehearsal_runner.run(rehearsal_tests, verbosity=2)
    rehearsal_success = scenery.common.summarize_test_result(rehearsal_result)

    # Dummy django app
    ##################

    print(f"{scenery.common.colorize("cyan", "# Dummy django app")}\n")

    from scenery.metatest import MetaTestRunner, MetaTestDiscoverer

    # Discovery
    metatest_discoverer = MetaTestDiscoverer()
    http_suite, selenium_suite = metatest_discoverer.discover(verbosity=2)

    # Running
    metatest_runner = MetaTestRunner()

    print(f"{scenery.common.colorize("cyan", "## Http")}\n")
    http_result = metatest_runner.run(http_suite, verbosity=2)
    http_success = scenery.common.summarize_test_result(http_result)
    http_success = True


    print(f"{scenery.common.colorize("cyan", "## Selenium")}\n")
    selenium_result = metatest_runner.run(selenium_suite, verbosity=2)
    selenium_success = scenery.common.summarize_test_result(selenium_result)

    ###################
    # Exit code
    ###################
    
    success = min(int(rehearsal_success), int(http_success), int(selenium_success),)
    exit_code = 1 - success

    if success:
        msg, color = "🟢 REHEARSAL WENT FINE", "green"
    else:
        msg, color = "❌ REHEARSAL FAILED", "red"

    print(f"{scenery.common.colorize(color, msg)}\n\n")

    return exit_code


if __name__ == "__main__":
    import sys

    exit_code = main()
    sys.exit(exit_code)
