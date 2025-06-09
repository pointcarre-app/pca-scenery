"""Run the testing routing based on the `scenery` settings.

See: `python -m scenery --help`
"""



if __name__ == "__main__":

    import sys

    import scenery.cli

    print("ICI")


    exit_code = scenery.cli.main()
    sys.exit(exit_code)
