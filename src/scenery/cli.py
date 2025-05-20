import argparse
import logging
import typing

from rich import box
from rich.logging import RichHandler
from rich.console import Console
from rich.rule import Rule
from rich.progress import Progress, BarColumn, TextColumn
from rich.style import Style
from rich.table import Table

import scenery.commands




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


    if args.not_headless is not None:     
        args.headless = not args.not_headless
    args.only_manifest, args.only_case_id, args.only_scene_pos = parse_arg_test_restriction(args.only_test)

    return args


def add_common_arguments(parser: argparse.ArgumentParser):

    # parser.add_argument(
    #     "-v",
    #     "--verbose",
    #     dest="verbosity",
    #     type=int,
    #     default=2,
    #     help="Verbose output",
    # )

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

    parser.add_argument(
        "-ds",
        "--django-settings",
        dest="django_settings_module",
        type=str,
        default=None,
        help="Location of django settings module",
    )


def parse_arg_test_restriction(only_test: str|None) -> typing.Tuple[str|None, str|None, str|None]:
    """Parse the --only-test argument into a tuple of (manifest_name, case_id, scene_pos)."""
    if only_test is not None:
        only_args = only_test.split(".")
        if len(only_args) == 1:
            manifest_name, case_id, scene_pos = only_args[0], None, None
        elif len(only_args) == 2:
            manifest_name, case_id, scene_pos = only_args[0], only_args[1], None
        elif len(only_args) == 3:
            manifest_name, case_id, scene_pos = only_args[0], only_args[1], only_args[2]
        else:
            raise ValueError(f"Wrong restrict argmuent {only_test}")
        return manifest_name, case_id, scene_pos
    else:
        return None, None, None


def parse_integration_args(subparser: argparse._SubParsersAction) -> argparse.Namespace:
    """Parse command line arguments."""

    parser = subparser.add_parser('integration', help='Integration tests')
    add_common_arguments(parser)


    parser.add_argument(
        "--only-test",
        nargs="?",
        default=None,
        help="Optional test restriction <manifest>.<case>.<scene>",
    )

    parser.add_argument(
        "--only-view",
        nargs="?",
        default=None,
        help="Optional view restriction",
    )

    parser.add_argument(
        "--timeout",
        dest="timeout_waiting_time",
        type=int,
        default=5,
    )

    parser.add_argument('--failfast', action='store_true')
    parser.add_argument('--only-back', action='store_true')
    parser.add_argument('--only-front', action='store_true')
    parser.add_argument('--not-headless', action='store_true')




def parse_load_args(subparser: argparse._SubParsersAction):

    parser = subparser.add_parser('load', help='Load tests')
    add_common_arguments(parser)

    # TODO


#################
# UI
#################



def rich_tabulate(d, col1_title, col2_title, title=None, formatting={}):
        console = Console()
        
        # Create a new table
        show_header = col1_title is not None or col2_title is not None
        table = Table(title=title, box=box.ROUNDED, show_header=show_header)
        table.add_column(col1_title, style="cyan", no_wrap=True)
        table.add_column(col2_title, justify="right")

        for key, value in d.items():

            format_str, color = formatting.get(key, ("{}", None))
            label = key.replace("_", " ").capitalize()
            row_values = [label,]
            value = d.get(key)
            formatted_value = format_str.format(value)
            if color:
                formatted_value = f"[{color}]{formatted_value}[/{color}]"
            row_values.append(formatted_value)
            
            table.add_row(*row_values)
        
    
        # Print the table
        console.print(table)

def show_histogram(x):
    """Display a histogram leveraging Rich progress bars"""

    console = Console()

    # Calculate histogram data
    min_val, max_val = min(x), max(x)
    bins = 10  # Number of bins
    
    # Ensure we don't divide by zero
    range_val = max_val - min_val
    bin_width = range_val / bins if range_val > 0 else 0.001
    
    # Count values in each bin
    histogram_data = []
    for i in range(bins):
        bin_start = min_val + i * bin_width
        bin_end = min_val + (i + 1) * bin_width
        bin_count = sum(1 for t in x if bin_start <= t < bin_end or (i == bins-1 and t == bin_end))
        histogram_data.append((bin_start, bin_end, bin_count))
    
    # Find the maximum count for percentage calculation
    max_count = sum(count for _, _, count in histogram_data) if histogram_data else 0

    completed_style = Style(color="white")

    # Use Progress bars to display the histogram
    with Progress(
        TextColumn("[bold]{task.description}"),
        BarColumn(bar_width=50,
        # style=bar_style,
        complete_style=completed_style,
        ),
        TextColumn("{task.completed} requests"),
        console=console,
        expand=False,
    ) as progress:
        for bin_start, bin_end, count in histogram_data:
            # Create a task description with the bin range
            desc = f"{bin_start:.4f}s - {bin_end:.4f}s"
            
            # Add a task for each bin and set its completion percentage based on the count
            progress.add_task(desc, total=max_count, completed=count)

##################
# COMMAND WRAPPER
##################




def command(func):
    def wrapper(*args):

        command_label = func.__name__.replace("_", " ").capitalize()

        console = Console()
        console.print(Rule(f"[section]{command_label}[/section]", style="cyan"))
        logging.log(logging.INFO, f"Starting {func.__name__}...")

        success, out = func(*args)
        
        return success, out

    return wrapper



def main():

    out: dict[str, dict[str, int | str | dict[str, typing.Any]]] = {}

    args = parse_args()


    # Set up logging with Rich handler
    logging.basicConfig(
        # level=logging.INFO,
        level=args.log,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, markup=True)]
    )


    success, out = command(scenery.commands.scenery_setup)(args.scenery_settings_module)
    success, out = command(scenery.commands.django_setup)(args.django_settings_module)

    # command(scenery.commands.django_setup)()

    if args.command == "integration":
        success, out = command(scenery.commands.integration_tests)(args)
    # elif args.command == "load":
    #     command(scenery.commands.load)(args)
    else:
        logging.error(f"{args.command} is not a thing")



    # # out["metadata"] = {"args": args.__dict__}

    # logging.info(f"{out=}")


