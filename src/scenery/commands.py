import argparse
from collections import Counter
import importlib
import os
import logging
# from typing import Any
from typing import Counter as CounterType
import sys
import sysconfig
import statistics

from rich.console import Console, Group
from rich.columns import Columns
from rich.rule import Rule
from rich.panel import Panel
from rich.text import Text

import scenery.cli
from scenery.common import summarize_test_result, interpret, iter_on_manifests

from rehearsal import CustomDiscoverRunner


########################
# SCENERY CONFIG
########################

def scenery_setup(args: argparse.Namespace) -> None:
    """Read the settings module and set the corresponding environment variables.

    This function imports the specified settings module and sets environment variables
    based on its contents. The following environment variables are set:

    SCENERY_COMMON_ITEMS
    SCENERY_SET_UP_INSTRUCTIONS
    SCENERY_TESTED_APP_NAME
    SCENERY_MANIFESTS_FOLDER

    Args:
        settings_location (str): The location (import path) of the settings module.

    Raises:
        ImportError: If the settings module cannot be imported.
    """

    # TODO mad: we choose convention over verification here
    # settings = importlib.import_module("rehearsal.scenery_settings")
    # if setting_module == "rehearsal.scenery_settings":
    sys.path.append(os.path.join('.'))
    settings = importlib.import_module(args.scenery_settings_module)
    
    # Env variables
    os.environ["SCENERY_COMMON_ITEMS"] = settings.SCENERY_COMMON_ITEMS
    os.environ["SCENERY_SET_UP_INSTRUCTIONS"] = settings.SCENERY_SET_UP_INSTRUCTIONS
    os.environ["SCENERY_POST_REQUESTS_INSTRUCTIONS_SELENIUM"] = (
        settings.SCENERY_POST_REQUESTS_INSTRUCTIONS_SELENIUM
    )
    os.environ["SCENERY_TESTED_APP_NAME"] = settings.SCENERY_TESTED_APP_NAME
    os.environ["SCENERY_MANIFESTS_FOLDER"] = settings.SCENERY_MANIFESTS_FOLDER

    emojy, msg, color, log_lvl = interpret(True)
    logging.log(log_lvl, f"[{color}]scenery_setup {msg}[/{color}]")
    

    return (
        True, 
        {
            "stdlib": sysconfig.get_paths()["stdlib"],
            "purelib": sysconfig.get_paths()["purelib"],
        }
    )

###################
# DJANGO CONFIG
###################

def django_setup(args: argparse.Namespace) -> int:
    """Set up the Django environment.

    This function sets the DJANGO_SETTINGS_MODULE environment variable and calls django.setup().

    Args:
        settings_module (str): The import path to the Django settings module.
    """

    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", args.django_settings_module)
    logging.debug(f"{os.environ.get('DJANGO_SETTINGS_MODULE')=}")
    django.setup()

    
    from django.conf import settings as django_settings
    logging.debug(f"{django_settings.INSTALLED_APPS=}")

    emojy, msg, color, log_lvl = interpret(True)
    logging.log(log_lvl, f"[{color}]django_setup {msg}[/{color}]")
    
    return True, {}



def integration_tests(args):
    """
    Execute the main functionality of the scenery test runner.

    Returns:
        exit_code (int): Exit code indicating success (0) or failure (1)
    """


    # NOTE mad: this needs to be loaded afeter scenery_setup and django_setup
    from scenery.core import process_manifest


    # FIXME mad: this is here to be able to load driver in two places
    # See also core.TestsLoader.tests_from_manifest.
    # Probably not a great pattern but let's fix this later
    # driver = get_selenium_driver(headless=args.headless)
    driver = None

    overall_backend_success, overall_frontend_success = True, True
    overall_backend_summary: CounterType[str] = Counter()
    overall_frontend_summary: CounterType[str] = Counter()

    for filename in iter_on_manifests(args):
        
        backend_result, frontend_result = process_manifest(filename, args=args, driver=driver)
        backend_success, backend_summary = summarize_test_result(backend_result, "backend")
        frontend_success, frontend_summary = summarize_test_result(frontend_result, "frontend")

        overall_backend_success &= backend_success
        overall_frontend_success &= frontend_success
        overall_frontend_summary.update(frontend_summary)
        overall_backend_summary.update(backend_summary)

        # results.append((filename, result))

    #############
    # OUTPUT
    #############

    console = Console()

    panel_msg = ""
    panel_color = "green"

    if not args.only_front:
        emojy, msg, color, log_lvl = interpret(overall_backend_success)
        if overall_backend_success:
            msg = f"all backend tests {msg}"
        else:
            msg = f"some backend tests {msg}"
            panel_color = "red"
        
        logging.log(log_lvl, f"[{color}]{msg}[/{color}]")
        panel_msg += f"{emojy} {msg}"

    


    if not args.only_back:
        emojy, msg, color, log_lvl = interpret(overall_frontend_success)
        if overall_frontend_success:
            msg = f"all frontend tests {msg}"
        else:
            msg = f"some frontend tests {msg}"
            panel_color = "red"
            
        logging.log(log_lvl, f"[{color}]{msg}[/{color}]")
        panel_msg += f"\n{emojy} {msg}"


    overall_success = overall_backend_success and overall_frontend_success
    emojy, msg, color, log_lvl = interpret(overall_success)
    logging.log(log_lvl, f"[{color}]scenery {msg}[/{color}]")


    console.print(Panel(
        panel_msg,
        title="Results",
        border_style=panel_color
    ))


    console.print(Rule(f"{emojy} Integration tests {msg}", style=color))

    return overall_success, {}



def load_tests(args):


    import unittest

    from django.contrib.staticfiles.testing import StaticLiveServerTestCase

    from scenery.load_test import LoadTester

    # from scenery.core import TestsLoader, TestsRunner

    # from rehearsal import CustomTestResult, CustomDiscoverRunner


    # loader = TestsLoader()
    # runner = TestsRunner()
    # runner.runner.resultclass = CustomTestResult

    # url = "http://localhost:8000"
    # endpoint = ""
    users = 20
    requests_per_user = 5


    # NOTE mad: this needs to be loaded afeter scenery_setup and django_setup
    # from scenery.core import TestsLoader
    from scenery.manifest_parser import ManifestParser
    from scenery.core import iter_on_takes_from_manifest
    from collections import defaultdict

    folder = os.environ["SCENERY_MANIFESTS_FOLDER"]

    django_runner = CustomDiscoverRunner(None)


    only_url = args.only_url
    only_case_id = args.only_case_id
    only_scene_pos = args.only_scene_pos

    data = defaultdict(list)

    for manifest_filename in iter_on_manifests(args):

        logging.log(logging.INFO, f"{manifest_filename=}")


        # Parse manifest
        manifest = ManifestParser.parse_yaml(os.path.join(folder, manifest_filename))
        ttype = manifest.testtype

        # logging.debug(manifest)

        for case_id, case, scene_pos, scene in iter_on_takes_from_manifest(
            manifest, only_url, only_case_id, only_scene_pos
        ):
            # TODO mad: this should actually be done in iter_on_takes
            take = scene.shoot(case)
            # logging.debug(dir(take))
            # logging.debug(take.url_name)
            # logging.info(take.url)
            # logging.info(take.method)
            logging.debug(take)

            class LoadTestCase(StaticLiveServerTestCase):

                def setUp(self):
                    super().setUp()
                    self.tester = LoadTester(self.live_server_url)

                def test_load(self):

                    # Run a load test against a specific endpoint
                    self.tester.run_load_test(
                        endpoint=take.url, 
                        method=take.method,
                        data=take.data,
                        headers=None,
                        users=users,             
                        requests_per_user=requests_per_user,
                    )

                
            # django_runner.test_runner.resultclass = CustomTestResult  

            django_test = LoadTestCase("test_load")

            suite = unittest.TestSuite()
            suite.addTest(django_test)
            result = django_runner.run_suite(suite)

            for key, val in django_test.tester.data.items():
                data[key] += val

            # break

        # break




    #####################
    # OUTPUT
    #####################

    console = Console()

    for endpoint, requests_results in data.items():

        total_requests = len(requests_results)
        if total_requests == 0:
            continue

        success_times = [r['elapsed_time']*1000 for r in requests_results if r["success"]]
        error_times = [r['elapsed_time']*1000 for r in requests_results if not r["success"]]
        
        error_rate = (len(error_times) / total_requests) * 100 if total_requests > 0 else 0
        
        ep_analysis = {
            'total_requests': total_requests,
            'successful_requests': len(success_times),
            'failed_requests': len(error_times),
            'error_rate': error_rate
        }


        # TODO mad: confirm with sel if success_times is the right one
        
        if success_times:
            ep_analysis.update({
                'avg_time': statistics.mean(success_times),
                'min_time': min(success_times),
                'max_time': max(success_times),
                'median_time': statistics.median(success_times)
            })
            
            if len(success_times) > 1:
                ep_analysis['stdev_time'] = statistics.stdev(success_times)
        
        formatting = {
            "error_rate": ("{:.2f}%", None),
            "avg_time": ("{:.2f}ms", None),
            "median_time": ("{:.2f}ms", None),
            "min_time": ("{:.2f}ms", None),
            "max_time": ("{:.2f}ms", None),
            "stdev_time": ("{:.2f}ms", None),
        }
         

        table = scenery.cli.table_from_dict(
            ep_analysis, 
            "Metric", 
            "Value", 
            "",
            formatting,
            )
        
        histogram = scenery.cli.histogram(success_times)

        histogram = Group(Text("\n"*1), histogram)
        columns = Columns([table, histogram], equal=False, expand=True)
        console.print(Panel(columns, title=f"{endpoint=}"))
        # group = Group(table, histogram)
        # console.print(Panel(group, title=f"{endpoint=}"))

        # TODO: message if response times too high ?


    return True, {}