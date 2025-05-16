import logging
import unittest
import sys

from rich.console import Console
from rich.rule import Rule
from rich.panel import Panel

# import typing 

def main() -> int:
    """Test the package `scenery` itself."""

    # NOTE mad: I first run rehearsal per se
    # then check that the main command works
    # by running the test I created 
    # for the dummy django app

    console = Console()


    ###################
    # CONFIG SCENERY
    ###################

    console.print(Rule("[section]CONFIG SCENERY[/section]", style="yellow"))
    

    # NOTE mad: should be consistent with scenery.common.scenery_setup()
    # TODO: remove and use root-folder
    # os.environ["SCENERY_COMMON_ITEMS"] = f"{rehearsal_dir}/common_items.yml"
    # os.environ["SCENERY_SET_UP_INSTRUCTIONS"] = "rehearsal.set_up_instructions"
    # os.environ["SCENERY_POST_REQUESTS_INSTRUCTIONS_SELENIUM"] = "rehearsal.post_requests_instructions_selenium"
    # os.environ["SCENERY_TESTED_APP_NAME"] = "some_app"
    # os.environ["SCENERY_MANIFESTS_FOLDER"] = f"{rehearsal_dir}/manifests"
    # rehearsal_dir = os.path.abspath(os.path.join(__file__, os.pardir))
    # print(f"REHEARSAL DIR{rehearsal_dir}\n")

    from scenery.common import django_setup, scenery_setup, summarize_test_result, rich_tabulate

    scenery_setup("rehearsal.scenery_settings")

    django_setup("rehearsal.django_project.django_project.settings")

    ####################
    # RUN
    ####################


    # Rehearsal
    ###########

    console.print(Rule("[section]REHEARSAL[/section]", style="yellow"))

    logging.log(logging.INFO, "Rehearsal start")

    import rehearsal.tests

    loader = unittest.TestLoader()
    rehearsal_tests = unittest.TestSuite()
    rehearsal_runner = unittest.TextTestRunner(stream=None)

    testsuites = loader.loadTestsFromModule(rehearsal.tests)
    rehearsal_tests.addTests(testsuites)    
    rehearsal_result = rehearsal_runner.run(rehearsal_tests)
    rehearsal_success, rehearsal_summary = summarize_test_result(rehearsal_result, "rehearsal")

        # if verbosity > 1:
    #     rich_tabulate(summary, "metric", "value")

    # if not msg_prefix:
    #     msg = ""
    # else:
    #     msg = f"{msg_prefix} "

    if rehearsal_success:
        msg, color = "🟢 reaharsal passed", "green"
    else:
        msg, color = "❌ rehearsal failed", "red"

    console.print(Panel(
        msg,
        title="Results",
        border_style=color
    ))
    rich_tabulate(rehearsal_summary, "rehearsal", "")


    # Dummy django app
    ##################

    console.print(Rule("[section]SCENERY ON DUMMY APP[/section]", style="yellow"))

    from scenery.__main__ import main as scenery_main
    scenery_exit_code = scenery_main("rehearsal.scenery_settings")

    ####################
    # OUTPUT
    ####################

    overall_success = scenery_exit_code == 0 and rehearsal_success
    exit_code = 1 - overall_success

    if overall_success:
        log_lvl, msg, color = logging.INFO, "reharsal passed", "green1"
        result_msg = "🟢 " + msg
    else:
        log_lvl, msg, color = logging.ERROR, "reharsal failed", "bright_red"
        result_msg = "❌ " + msg

    logging.log(log_lvl, f"[{color}]{msg}[/{color}]")

    console.print(Rule(result_msg.upper(), style=color))
    return exit_code


if __name__ == "__main__":

    exit_code = main()
    sys.exit(exit_code)
