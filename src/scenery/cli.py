import argparse
import typing
import statistics
import collections

from rich import box
from rich.console import Console
from rich.rule import Rule
from rich.progress import Progress, BarColumn, TextColumn
from rich.style import Style
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.console import Group
from rich.panel import Panel

import scenery.commands
from scenery import logger, console




#################
# PARSE ARGUMENTS
#################


def parse_args():
    """Parse command line arguments with subcommands."""
    parser = argparse.ArgumentParser(description="Scenery Testing Framework")
    subparsers = parser.add_subparsers(dest="command", help="Testing command to run")
    # Add subparsers
    integration_parser = parse_integration_args(subparsers)
    load_parser = parse_load_args(subparsers) 

    args = parser.parse_args()

    if hasattr(args, "test"):
        args.manifest, args.case_id, args.scene_pos = parse_arg_test_restriction(args.test)


    return args


def add_common_arguments(parser: argparse.ArgumentParser):

    parser.add_argument(
        "--log",
        default="INFO",
        help="Logging level"
    )

    parser.add_argument(
        "-s",
        "--scenery-settings",
        dest="scenery_settings_module",
        type=str,
        default="scenery_settings",
        help="Location of scenery settings module",
    )




def parse_arg_test_restriction(test_name_pattern: str|None) -> typing.Tuple[str|None, str|None, str|None]:
    """Parse the --test argument into a tuple of (manifest_name, case_id, scene_pos)."""
    if test_name_pattern is not None:
        split_pattern = test_name_pattern.split(".")
        if len(split_pattern) == 1:
            manifest_name, case_id, scene_pos = split_pattern[0], None, None
        elif len(split_pattern) == 2:
            manifest_name, case_id, scene_pos = split_pattern[0], split_pattern[1], None
        elif len(split_pattern) == 3:
            manifest_name, case_id, scene_pos = split_pattern[0], split_pattern[1], split_pattern[2]
        else:
            raise ValueError(f"Wrong restrict argmuent {test_name_pattern}")
        return manifest_name, case_id, scene_pos
    else:
        return None, None, None


def parse_integration_args(subparser: argparse._SubParsersAction) -> argparse.Namespace:
    """Parse command line arguments."""

    parser = subparser.add_parser('integration', help='Integration tests')
    add_common_arguments(parser)


    parser.add_argument(
        "--mode",
        choices=["dev", "local", "staging", "prod"],
    )

    parser.add_argument(
        "-ds",
        "--django-settings",
        dest="django_settings_module",
        type=str,
        default=None,
        help="Location of django settings module",
    )

    parser.add_argument(
        "--test",
        nargs="?",
        default=None,
        help="Optional test restriction <manifest>.<case>.<scene>",
    )

    parser.add_argument(
        "--url",
        nargs="?",
        default=None,
        help="Optional url restriction",
    )

    parser.add_argument(
        "--timeout",
        dest="timeout_waiting_time",
        type=int,
        default=5,
    )

    parser.add_argument('--failfast', action='store_true')
    parser.add_argument('--back', action='store_true')
    parser.add_argument('--front', action='store_true')
    parser.add_argument('--headless', action='store_true')





def parse_load_args(subparser: argparse._SubParsersAction):

    parser = subparser.add_parser('load', help='Load tests')
    add_common_arguments(parser)

    # TODO


#################
# UI
#################



def table_from_dict(d, col1_title, col2_title, title=None, formatting={}):
        
    show_header = col1_title is not None or col2_title is not None
    table = Table(title=title, box=box.ROUNDED, show_header=show_header)
    table.add_column(col1_title, style="cyan", no_wrap=True)
    table.add_column(col2_title, justify="right")

    for key, value in d.items():

        format_str, color = formatting.get(key, ("{}", None))
        label = str(key).replace("_", " ").capitalize()
        row_values = [label,]
        value = d.get(key)
        formatted_value = format_str.format(value)
        if color:
            formatted_value = f"[{color}]{formatted_value}[/{color}]"
        row_values.append(formatted_value)
        
        table.add_row(*row_values)
    
    return table

def histogram(x):
    """Display a histogram leveraging Rich progress bars and return a renderable object"""
    # Calculate histogram data
    min_val, max_val = min(x), max(x)
    bins = 10  # Number of bins
    range_val = max_val - min_val
    bin_width = range_val / bins if range_val > 0 else 0.001
    
    histogram_data = []
    for i in range(bins):
        bin_start = min_val + i * bin_width
        bin_end = min_val + (i + 1) * bin_width
        bin_count = sum(1 for t in x if bin_start <= t < bin_end or (i == bins-1 and t == bin_end))
        histogram_data.append((bin_start, bin_end, bin_count))
    
    max_count = sum(count for _, _, count in histogram_data) if histogram_data else 0
    completed_style = Style(color="white")
    
    # Create a custom Progress object that can be rendered later
    progress = Progress(
        TextColumn("[bold]{task.description}"),
        BarColumn(bar_width=50, complete_style=completed_style),
        TextColumn("{task.completed} requests"),
        expand=False,
    )
    
    # Add tasks to the progress object
    for bin_start, bin_end, count in histogram_data:
        desc = f"{bin_start:.0f}ms - {bin_end:.0f}ms"
        progress.add_task(desc, total=max_count, completed=count)
    
    # Return the progress object itself (which is renderable)
    return progress

##################
# COMMAND WRAPPER
##################


def command(func):
    def wrapper(*args):

        command_label = func.__name__.replace("_", " ").capitalize()

        console.print(Rule(f"[section]{command_label}[/section]", style="cyan"))
        logger.info(f"starting {func.__name__}...")

        success, out = func(*args)
        
        return success, out

    return wrapper


##################
# REPORTS
##################


def report_load_tests(data: dict):

    #####################
    # OUTPUT
    #####################

    # TODO: Report and testing should focus on on 90, 95, 99

    console = Console()

    for endpoint, requests_results in data.items():

        total_requests = len(requests_results)
        if total_requests == 0:
            continue

        successes = [r for r in requests_results if r["success"]]
        failures = [r for r in requests_results if not r["success"] ]

        success_times = [r['elapsed_time']*1000 for r in successes]
        error_times = [r['elapsed_time']*1000 for r in failures]
        
        error_rate = (len(error_times) / total_requests) * 100 if total_requests > 0 else 0
        
        ep_analysis = {
            'total_requests': total_requests,
            'successful_requests': len(success_times),
            'failed_requests': len(error_times),
            'error_rate': error_rate
        }


        # TODO mad: confirm with sel if success_times is the right one
        
        if success_times:
            # quantiles = statistics.quantiles(success_times, n=100)
            quantiles = statistics.quantiles(success_times, n=4)

            ep_analysis.update({
                'min_time': min(success_times),
                'p50': statistics.median(success_times),
                # 'p90': quantiles[90-1],
                # 'p99': quantiles[99-1],
                'max': max(success_times),

            })
            
            if len(success_times) > 1:
                ep_analysis['stdev'] = statistics.stdev(success_times)
        
        formatting = {
            "error_rate": ("{:.2f}%", None),
            "min_time": ("{:.2f}ms", None),
            "p50": ("{:.2f}ms", None),
            "p90": ("{:.2f}ms", None),
            "p99": ("{:.2f}ms", None),
            "max": ("{:.2f}ms", None),
            "stdev": ("{:.2f}ms", None),
        }
         

        table = table_from_dict(
            ep_analysis, 
            "Metric", 
            "Value", 
            "",
            formatting,
            )
        
        histogram_plot = histogram(success_times)

        histogram_plot = Group(Text("\n"*1), histogram_plot)
        successes_columns = Columns([table, histogram_plot], equal=False, expand=True)

        if failures:
            failures_status_codes = collections.Counter([r["status_code"] for r in failures])        
            failures_table = table_from_dict(
                failures_status_codes, 
                "Status code of failed requests", 
                "N", 
                "",
                )
            
            panel_content = Group(successes_columns, failures_table)

        else:
            panel_content = successes_columns

        
        console.print(Panel(panel_content, title=f"{endpoint=}"))

        
        # group = Group(table, histogram)
        # console.print(Panel(group, title=f"{endpoint=}"))

        # TODO: message if response times too high ?


###############
# MAIN
###############


def main():

    out: dict[str, dict[str, int | str | dict[str, typing.Any]]] = {}

    args = parse_args()



    logger.debug(f"{args=}")



    success, out = command(scenery.commands.scenery_setup)(args)

    # if args.mode == "dev":
    success, out = command(scenery.commands.django_setup)(args)


    if args.command == "integration":
        success, out = command(scenery.commands.integration_tests)(args)
    elif args.command == "load":
        command(scenery.commands.load_tests)(args)



    # out["metadata"] = {"args": args.__dict__}

