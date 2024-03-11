"""Handles the import subcommand for spyctl."""

import click

import spyctl.spyctl_lib as lib
from spyctl.commands import apply

# ----------------------------------------------------------------- #
#                         Import Subcommand                         #
# ----------------------------------------------------------------- #


@click.command("import", cls=lib.CustomCommand, epilog=lib.SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True, is_eager=True)
@click.option(
    "-f",
    "--filename",
    help="Filename containing policies to import.",
    metavar="",
    type=click.File(),
    required=True,
)
def spy_import(filename):
    """Import previously exported policies by file name
    into a new organization context."""
    handle_import(filename)


def handle_import(filename):
    """
    Handles the import of a file. Essentially a wrapper for the
    actual apply command.

    Args:
        filename (str): The name of the file to import.

    Returns:
        None
    """
    apply.handle_apply(filename)
