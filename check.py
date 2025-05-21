#!/bin/env python
import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from itertools import product
from pathlib import Path

backend_files = [
    "backend",
    "check.py",
]  # Add non-frontend files that are not in the backend directory here
frontend_files = ["frontend"]


@dataclass
class Command:
    # Command to run, including args
    command: list[str]

    # Directory to run the command in, relative to the project root
    cwd: Path = Path(".")


def venv(s: str) -> str:
    """Ensure that the executable within a venv is used"""
    # This will be the bin directory of the current virtualenv
    bin = Path(sys.executable).parent
    return str(bin / s)


commands = {
    "backend": {
        "fmt": Command(
            [
                venv("black"),
                *backend_files,
            ]
        ),
        "fmt-check": Command([venv("black"), ".", "--diff", "--color", "--check"]),
        "lint": Command(
            [
                venv("flake8"),
                *backend_files,
                # ignore config files (all config is done here)
                "--isolated",
                # match black
                "--max-line-length=100",
                # disable line length and space before
                "--extend-ignore=E501,E203",
            ]
        ),
    },
    "frontend": {
        "fmt": Command(
            [
                venv("black"),
                *frontend_files,
            ]
        ),
        "fmt-check": Command([venv("black"), ".", "--diff", "--color", "--check"]),
        "lint": Command(
            [
                venv("flake8"),
                *frontend_files,
                # ignore config files (all config is done here)
                "--isolated",
                # match black
                "--max-line-length=100",
                # disable line length and space before
                "--extend-ignore=E501,E203",
            ]
        ),
    },
}


def print_divider(s, width):
    """Print the name of the command surrounded by '='"""
    print(f"{' ' + s + ' ' :=^{width}}")


def main():
    """
    Run the checks for the CI. By default, runs fmt and lint.
    It is also possible to specify a list of commands to run.

    The development requirements should be installed for this
    program to work.

    The following commands are available:
    - fmt: formatting
    - lint: linting
    - fmt-check: check formatting but don't apply fixes (for CI)

    By default, the checks are run on the front- and backend.
    """
    parser = argparse.ArgumentParser(
        description="""
            Run the checks for the CI. By default, runs fmt and lint.
            It is also possible to specify a list of commands to run.

            The development requirements should be installed for this
            program to work.

            The following commands are available:
            - fmt: formatting
            - lint: linting
            - fmt-check: check formatting but don't apply fixes (for CI)

            By default, the checks are run on the front- and backend.
       """
    )
    parser.add_argument("commands", nargs="*", default=["fmt", "lint"])
    parser.add_argument("-f", "--frontend", action="store_true", help="Check frontend")
    parser.add_argument("-b", "--backend", action="store_true", help="Check backend")
    args = parser.parse_args()

    # The get_terminal_size command fails in some cases
    # where there isn't really a terminal width.
    # This is the case in the CI. 80 should be a reasonable default.
    # The width is used to print the dividers between the commands.
    try:
        width = os.get_terminal_size().columns
    except OSError:
        width = 80

    cwd = Path(__file__).parent

    if args.frontend and not args.backend:
        suffixes = ["frontend"]
    elif args.backend and not args.frontend:
        suffixes = ["backend"]
    else:
        suffixes = ["frontend", "backend"]

    for c, front_or_back in product(args.commands, suffixes):
        command = commands[front_or_back][f"{c}"]
        print_divider(f"{c} ({front_or_back})", width)

        result = subprocess.run(command.command, cwd=cwd / command.cwd / front_or_back)

        if result.stdout:
            print(result.stdout)

        if result.stderr:
            print(result.stderr)

        if result.returncode > 0:
            print(
                f"""Command '{c}' on the {front_or_back}
                failed with code {result.returncode}"""
            )
            print("Exiting...")
            sys.exit(result.returncode)


if __name__ == "__main__":
    main()
