def main() -> int:
    """Test the package `scenery` itself."""

    ###################
    # CONFIG SCENERY
    ###################

    import os

    rehearsal_dir = os.path.abspath(os.path.join(__file__, os.pardir))

    print("REHEARSAL DIR", rehearsal_dir)

    # Scenery
    # NOTE: should be consistent with scenery.common.scenery_setup()
    os.environ["SCENERY_COMMON_ITEMS"] = f"{rehearsal_dir}/common_items.yml"
    os.environ["SCENERY_SET_UP_INSTRUCTIONS"] = "rehearsal.set_up_instructions"
    os.environ["SCENERY_TESTED_APP_NAME"] = "some_app"
    os.environ["SCENERY_MANIFESTS_FOLDER"] = f"{rehearsal_dir}/manifests"

    ###################
    # CONFIG DJANGO
    ###################

    import scenery.common

    scenery.common.django_setup("rehearsal.project_django.project_django.settings")

    #############
    # RUN TESTS
    #############

    # NOTE: I first run rehearsal per and
    # then check that the main command works
    # by running the test I created in the dummy
    # django app

    import rehearsal
    import collections

    summary: collections.Counter[str] = collections.Counter()
    rehearsal_discoverer = rehearsal.RehearsalDiscoverer()
    rehearsal_runner = rehearsal.RehearsalRunner()
    tests_discovered = rehearsal_discoverer.discover(verbosity=2)
    result = rehearsal_runner.run(tests_discovered, verbosity=2)
    for result_value in result.values():
        summary.update(result_value)

    from scenery.metatest import MetaTestRunner, MetaTestDiscoverer

    metatest_discoverer = MetaTestDiscoverer()
    tests_discovered = metatest_discoverer.discover(verbosity=2)
    metatest_runner = MetaTestRunner()
    result = metatest_runner.run(tests_discovered, verbosity=2)
    for result_value in result.values():
        summary.update(result_value)

    ########
    # OUTPUT
    ########

    for key, val in summary.items():
        if key != "testsRun" and val > 0:
            fail = True
        else:
            fail = False

    if fail:
        msg, color, exit = "FAIL", "red", 1
    else:
        msg, color, exit = "OK", "green", 0

    print(f"\n\nSummary:\n{scenery.common.tabulate(summary)}")
    print(f"{scenery.common.colorize(color, msg)}\n\n")
    return exit


if __name__ == "__main__":
    import sys

    exit = main()
    sys.exit(exit)
