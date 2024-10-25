def main():
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

    import rehearsal
    import collections

    out, summary = {}, collections.Counter()
    discoverer = rehearsal.RehearsalDiscoverer()
    runner = rehearsal.RehearsalRunner()
    tests_discovered = discoverer.discover(verbosity=2)
    result = runner.run(tests_discovered, verbosity=2)
    out.update(result)
    for val in result.values():
        summary.update(val)

    from scenery.metatest import MetaTestRunner, MetaTestDiscoverer

    discoverer = MetaTestDiscoverer()
    tests_discovered = discoverer.discover(verbosity=2)
    runner = MetaTestRunner()
    result = runner.run(tests_discovered, verbosity=2)
    out.update(result)
    for val in result.values():
        summary.update(val)

    ########
    # OUTPUT
    ########

    fail = False
    for key, val in summary.items():
        if key != "testsRun" and val > 0:
            fail = True
            break

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
