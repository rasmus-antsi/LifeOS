import argparse

from life_os.app import LifeOSApp
from life_os.context import Context

from commands.doctor import run as doctor_run
from commands.init import run as init_run


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="life-os",
        description="Personal system management tool",
    )

    parser.add_argument(
        "command",
        nargs="?",
        default="doctor",
        help="Command to run (default: doctor)",
    )

    parser.add_argument(
        "args",
        nargs="*",
        help="Command arguments (e.g. doctor workspace)",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    context = Context(verbose=args.verbose)
    app = LifeOSApp(context)

    # Register commands
    app.register("doctor", doctor_run)
    app.register("init", init_run)

    app.run([args.command, *args.args])


if __name__ == "__main__":
    main()
