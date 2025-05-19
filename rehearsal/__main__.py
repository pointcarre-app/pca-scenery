import argparse
import unittest
import sys


from rich.console import Console
from rich.rule import Rule
from rich.panel import Panel

# import typing 

from scenery.common import summarize_test_result





def unitary_tests():

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
    """Test the package `scenery` itself."""

    # NOTE mad: I first run rehearsal per se then check that the main command works
    # by running the tests I created  for the dummy django app

    console = Console()

    ###################
    # CONFIG SCENERY
    ###################

    console.print(Rule("[section]CONFIG FOR REHEARSAL[/section]", style="yellow"))
    

    import scenery.cli
    from scenery.commands import scenery_setup, django_setup

    scenery.cli.command(scenery_setup, show_panel=False, show_report=False)("rehearsal.scenery_settings")
    scenery.cli.command(django_setup, show_panel=False, show_report=False)("rehearsal.django_project.django_project.settings")

    ####################
    # RUN
    ####################


    # Rehearsal
    ###########

    console.print(Rule("[section]REHEARSAL[/section]", style="yellow"))

    unit_success, unit_out = scenery.cli.command(unitary_tests)()


    # Dummy django app
    ##################

    console.print(Rule("[section]SCENERY ON DUMMY APP[/section]", style="yellow"))

    from scenery.commands import integration_tests

    args = argparse.Namespace(
        scenery_settings_module="rehearsal.scenery_settings", 
        only_manifest=None, 
        only_back=False, 
        only_front=False,
        only_view=None,
        only_case_id=None,
        only_scene_pos=None,
        timeout_waiting_time=None,
        headless=True
        )
    scenery_success, scenery_out = scenery.cli.command(integration_tests)(args)

    # ####################
    # # OUTPUT
    # ####################

    # overall_success = scenery_exit_code == 0 and rehearsal_success
    # exit_code = 1 - overall_success

    # if overall_success:
    #     log_lvl, msg, color = logging.INFO, "reharsal passed", "green1"
    #     result_msg = "🟢 " + msg
    # else:
    #     log_lvl, msg, color = logging.ERROR, "reharsal failed", "bright_red"
    #     result_msg = "❌ " + msg

    # logging.log(log_lvl, f"[{color}]{msg}[/{color}]")

    # console.print(Rule(result_msg.upper(), style=color))
    # return exit_code


if __name__ == "__main__":

    exit_code = main()
    sys.exit(exit_code)
