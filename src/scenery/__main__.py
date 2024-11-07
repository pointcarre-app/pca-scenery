import sys
import typing


def main() -> int:
    """
    Executes the main functionality of the scenery test runner.

    Returns:
        exit_code (int): Exit code indicating success (0) or failure (1)
    """

    out: dict[str, dict[str, int | str | dict[str, typing.Any]]] = {}

    #################
    # PARSE ARGUMENTS
    #################

    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "restrict",
        nargs="?",
        default=None,
        help="Optional test restriction <manifest>.<case>.<scene>",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbosity",
        type=int,
        default=2,
        help="Verbose output",
    )

    parser.add_argument(
        "-s",
        "--scenery_settings",
        dest="scenery_settings_module",
        type=str,
        default="scenery_settings",
        help="Location of scenery settings module",
    )

    parser.add_argument(
        "-ds",
        "--django_settings",
        dest="django_settings_module",
        type=str,
        default=None,
        help="Location of django settings module",
    )

    parser.add_argument(
        "--output",
        default=None,
        dest="output",
        action="store",
        help="Export output",
    )

    args = parser.parse_args()

    out["metadata"] = {"args": args.__dict__}

    ####################
    # LOGGERS
    ####################

    # level = logging.DEBUG

    # # Format
    # format_log = "[%(asctime)s.%(msecs)03d] [%(name)s] [%(levelname)s] %(message)s"
    # datefmt_ = "%Y-%m-%d %H:%M:%S"
    # formatter = logging.Formatter(fmt=format_log, datefmt=datefmt_)

    # # Handlers
    # if args.output:
    #     handler_full = logging.FileHandler(args.output, mode="w")
    #     handler_full.setFormatter(formatter)
    #     handler_full.setLevel(level)
    # else:
    #     handler_full = logging.NullHandler()

    # # Scenery
    # logger = logging.getLogger(__package__)
    # logger.addHandler(handler_full)
    # logger.setLevel(level)

    # NOTE: should be in settings
    # logger_app = logging.getLogger("logger_app")
    # logger_app.handlers = []
    # logger_app.addHandler(handler_full)
    # logger_app.setLevel(level)

    ####################
    # SYSTEM CONFIG
    ####################

    import sysconfig

    out["metadata"].update(
        {
            "stdlib": sysconfig.get_paths()["stdlib"],
            "purelib": sysconfig.get_paths()["purelib"],
            "scenery": __package__,
        }
    )

    ##################
    # CONFIG SCENERY
    ##################

    import scenery.common

    scenery.common.scenery_setup(settings_location=args.scenery_settings_module)

    #####################
    # CONFIG DJANGO
    #####################

    scenery.common.django_setup(settings_module=args.django_settings_module)

    #############
    # METATESTING
    #############

    # NOTE: the imports will fail if loaded before SCENERY_ENV configuration
    from scenery.metatest import MetaTestRunner, MetaTestDiscoverer

    import collections

    summary: collections.Counter[str] = collections.Counter()
    discoverer = MetaTestDiscoverer()
    tests_discovered = discoverer.discover(verbosity=2, restrict=args.restrict)
    runner = MetaTestRunner()
    result = runner.run(tests_discovered, args.verbosity)
    # NOTE: type casting is done because mypy is being strict here because
    # dictionary types in Python are invariant by default
    # (for good reasons related to mutability and type safety).
    # This means even if type A is a subtype of type B, dict[str, A]
    # not considered a subtype of dict[str, B].
    out.update(
        typing.cast(
            dict[str, dict[str, int | str | dict[str, typing.Any]]],
            result,
        )
    )
    for result_value in result.values():
        summary.update(result_value)

    ###############
    # OUTPUT RESULT
    ###############

    if args.output is not None:
        import json

        with open(args.output, "w") as f:
            json.dump(out, f)

    for key, val in summary.items():
        if key != "testsRun" and val > 0:
            fail = True
        else:
            fail = False

    if fail:
        msg, color, exit_code = "FAIL", "red", 1
    else:
        msg, color, exit_code = "OK", "green", 0

    print(f"Summary:\n{scenery.common.tabulate(summary)}")
    print(f"{scenery.common.colorize(color, msg)}\n\n")

    return exit_code


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
