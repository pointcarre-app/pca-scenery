import argparse
import unittest

from rich.console import Console
from rich.rule import Rule

from scenery.common import summarize_test_result





def rehearsal_unitary_tests():

    import rehearsal.tests

    loader = unittest.TestLoader()
    rehearsal_tests = unittest.TestSuite()
    rehearsal_runner = unittest.TextTestRunner(stream=None)

    testsuites = loader.loadTestsFromModule(rehearsal.tests)
    rehearsal_tests.addTests(testsuites)    
    rehearsal_result = rehearsal_runner.run(rehearsal_tests)
    rehearsal_success, rehearsal_summary = summarize_test_result(rehearsal_result, "unitary tests")

    return rehearsal_success, rehearsal_summary


def main() -> int:
    """Test the package `scenery` itself. First run rehearsal unitary tests 
    then check that the main command works by running it on the dummy django app"""

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
    
    # args = argparse.Namespace(
    #     scenery_settings_module="rehearsal.scenery_settings", 
    #     django_settings_module="rehearsal.django_project.django_project.settings",
    #     log="INFO"
    #     # log="DEBUG"
    # )



    import scenery.cli
    from scenery.commands import scenery_setup, django_setup

    scenery.cli.command(scenery_setup)(args)
    scenery.cli.command(django_setup)(args)

    ####################
    # RUN
    ####################


    # Rehearsal
    ###########

    console.print(Rule("[section]REHEARSAL[/section]", style="yellow"))

    unit_success, unit_out = rehearsal_unitary_tests()


    # Dummy django app
    ##################

    console.print(Rule("[section]SCENERY ON DUMMY APP[/section]", style="yellow"))

    from scenery.commands import integration_tests 

    args = argparse.Namespace(
        scenery_settings_module="rehearsal.scenery_settings", 
        manifest=None, 
        back=False, 
        front=False,
        url=None,
        case_id=None,
        scene_pos=None,
        timeout_waiting_time=None,
        headless=True,
        log=args.log,
        mode="dev",
        )
    scenery_success, scenery_out = scenery.cli.command(integration_tests)(args)




if __name__ == "__main__":

    exit_code = main()
    # sys.exit(exit_code)
