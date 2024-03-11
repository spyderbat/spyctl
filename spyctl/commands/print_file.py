"""Handles the hidden print subcommand for spyctl."""

import json
from typing import IO

import click

import spyctl.spyctl_lib as lib

# ----------------------------------------------------------------- #
#                     Hidden Print Subcommand                       #
# ----------------------------------------------------------------- #


@click.command(
    "print", cls=lib.CustomCommand, hidden=True, epilog=lib.SUB_EPILOG
)
@click.option(
    "-f",
    "--filename",
    "file",
    help="Target file to print",
    metavar="",
    required=True,
    type=click.File(),
)
@click.option("-l", "--list-output", is_flag=True, default=False)
@click.help_option("-h", "--help", hidden=True)
def print_file(file, list_output):
    """Print a file's contents in a json format."""
    handle_print_file(file, list_output)


# ----------------------------------------------------------------- #
#                       Print File Handlers                         #
# ----------------------------------------------------------------- #
def handle_print_file(file: IO, list_output: bool):
    """
    Prints the contents of a file.

    Args:
        file (IO): The file object to be printed.
        list_output (bool): If True, the file contents will be printed
            as a list.

    Returns:
        None
    """
    if list_output:
        data = [lib.load_file_for_api_test(file)]
    else:
        data = lib.load_file_for_api_test(file)
    data = json.dumps({"data": json.dumps(data)})
    print(data)
