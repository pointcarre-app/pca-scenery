import argparse
import unittest

from rich.console import Console
from rich.rule import Rule

from scenery.common import summarize_test_result





def rehearsal_unit_tests() -> bool:

    import rehearsal.tests

    loader = unittest.TestLoader()
    rehearsal_tests = unittest.TestSuite()
    rehearsal_runner = unittest.TextTestRunner(stream=None)

    testsuites = loader.loadTestsFromModule(rehearsal.tests)
    rehearsal_tests.addTests(testsuites)    
    rehearsal_result = rehearsal_runner.run(rehearsal_tests)
    rehearsal_success, rehearsal_summary = summarize_test_result(rehearsal_result, "unitary tests")

    return rehearsal_success


def main() -> bool:
    """Test the package `scenery` itself. First run rehearsal unitary tests 
    then check that the main command works by running it on the dummy django app"""

    rehearsal_success = True

    console = Console()

    parser = argparse.ArgumentParser()
    parser.add_argument("--log", default="INFO")
    args = parser.parse_args()

    ###################
    # CONFIG SCENERY
    ###################

    console.print(Rule("[section]CONFIG FOR REHEARSAL[/section]", style="yellow"))

    args.scenery_settings_module = "rehearsal.scenery_settings"
    args.django_settings_module = "rehearsal.django_project.django_project.settings"

    import scenery.cli
    from scenery.commands import scenery_setup, django_setup

    scenery_setup_success = scenery.cli.command(scenery_setup)(args)
    rehearsal_success &=  scenery_setup_success

    django_setup_success = scenery.cli.command(django_setup)(args)    
    rehearsal_success &=  django_setup_success

    ####################
    # RUN
    ####################


    # Unit
    ###########

    console.print(Rule("[section]REHEARSAL[/section]", style="yellow"))

    unit_success = rehearsal_unit_tests()
    rehearsal_success &=  unit_success

    # Dummy django app
    ##################
    from scenery.commands import integration_tests, load_tests, inspect_code

    console.print(Rule("[section]SCENERY ON DUMMY APP[/section]", style="yellow"))

    args = argparse.Namespace(
        scenery_settings_module="rehearsal.scenery_settings", 
        manifest=None, 
        back=True, 
        front=True,
        url=None,
        case_id=None,
        scene_pos=None,
        timeout_waiting_time=None,
        headless=True,
        log=args.log,
        mode="dev",
        )
    integration_success = scenery.cli.command(integration_tests)(args)
    rehearsal_success &= integration_success

    # TODO mad: there must be a way to launch the server from here
    # args = argparse.Namespace(
    #     scenery_settings_module="rehearsal.scenery_settings", 
    #     manifest="hello_http", 
    #     url=None,
    #     case_id=None,
    #     scene_pos=None,
    #     users=2,
    #     requests=2,
    #     log=args.log,
    #     mode="local",
    #     )
    # load_success = scenery.cli.command(load_tests)(args)
    # rehearsal_success &= load_success

    args = argparse.Namespace(
        folder='src/scenery',
        log=args.log,
        mode="dev",
        )
    inspect_success = scenery.cli.command(inspect_code)(args)
    rehearsal_success &= inspect_success

    # args = argparse.Namespace(
    #     folder='rehearsal',
    #     log=args.log,
    #     mode="dev",
    #     )
    # scenery_success, scenery_out = scenery.cli.command(inspect_nlines)(args)

    return rehearsal_success


if __name__ == "__main__":
    import sys
    success = main()
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
