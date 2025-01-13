"""Run the testing routing based on the `scenery` settings.

See: `python -m scenery --help`
"""

# TODO mad: this function is never executed during testing

import sys
import typing


def main() -> int:
    """
    Execute the main functionality of the scenery test runner.

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

    parser.add_argument('--failfast', action='store_true')

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

    # NOTE mad: the imports will fail if loaded before SCENERY_ENV configuration
    from scenery.metatest import MetaTestRunner, MetaTestDiscoverer

    discoverer = MetaTestDiscoverer()
    http_suite, selenium_suite =  discoverer.discover(verbosity=2, restrict=args.restrict)
    runner = MetaTestRunner(failfast=args.failfast)

    print("HTTP")
    
    http_result = runner.run(http_suite, args.verbosity)
    http_success = scenery.common.summarize_test_result(http_result)

    print("SELENIUM")

    selenium_result = runner.run(selenium_suite, args.verbosity)
    selenium_success = scenery.common.summarize_test_result(selenium_result)
    

    # NOTE mad: type casting is done because mypy is being strict here because
    # dictionary types in Python are invariant by default
    # (for good reasons related to mutability and type safety).
    # This means even if type A is a subtype of type B, dict[str, A]
    # not considered a subtype of dict[str, B].
    # out.update(
    #     typing.cast(
    #         dict[str, dict[str, int | str | dict[str, typing.Any]]],
    #         result,
    #     )
    # )
    # result = 
    # from pprint import pprint
    # pprint(result)
    # for result_value in result.values():
    #     summary.update(result_value)

    # summary = scenery.common.serialize_unittest_result(results)

    # ###############
    # # OUTPUT RESULT
    # ###############

    # if args.output is not None:
    #     import json

    #     with open(args.output, "w") as f:
    #         json.dump(out, f)

    ###################
    # Exit code
    ###################
    
    success = min(int(http_success), int(selenium_success),)
    exit_code = 1 - success

    if success:
        msg, color = "🟢 SCENERY WENT FINE", "green"
    else:
        msg, color = "❌ SCENERY FAILED", "red"

    print(f"{scenery.common.colorize(color, msg)}\n\n")

    return exit_code


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
