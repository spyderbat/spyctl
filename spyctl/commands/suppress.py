"""Handles the suppress subcommand for spyctl."""

import click

from spyctl.commands import apply
import spyctl.resources.suppression_policies as sp
import spyctl.spyctl_lib as lib
from spyctl import cli, search

# ----------------------------------------------------------------- #
#                       Suppress Subcommand                         #
# ----------------------------------------------------------------- #


@click.group("suppress", cls=lib.CustomSubGroup, epilog=lib.SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True)
def suppress():
    "Tune your environment by suppressing Spyderbat Resources"


@suppress.command("trace", cls=lib.CustomCommand, epilog=lib.SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.option(
    "-i",
    "--id",
    "resrc_id",
    help="id of the spydertrace or spydertrace summary to suppress",
    metavar="",
    required=True,
)
@click.option(
    "-u",
    "--include-users",
    help="Scope the trace suppression policy to the users found in the trace",
    metavar="",
    is_flag=True,
    default=False,
)
@click.option(
    "-y",
    "--yes",
    "--assume-yes",
    is_flag=True,
    help='Automatic yes to prompts; assume "yes" as answer to all prompts and'
    " run non-interactively.",
)
def suppress_spydertrace(
    include_users,
    yes,
    resrc_id=None,
):
    "Suppress one or many Spyderbat Resources"
    if yes:
        cli.set_yes_option()
    handle_suppress_trace_by_id(resrc_id, include_users)


# ----------------------------------------------------------------- #
#                        Suppress Handlers                          #
# ----------------------------------------------------------------- #


def handle_suppress_trace_by_id(orig_id: str, include_users: bool):
    """
    Handles the suppression of a trace by its ID.

    Args:
        orig_id (str): The ID of the trace to be suppressed.
        include_users (bool): Flag indicating whether to include user
            information in the suppression policy scope.

    Returns:
        None
    """
    trace = search.search_for_trace_by_uid(orig_id)
    if not trace:
        cli.err_exit(f"Unable to find a Trace with id {orig_id}")
    summary_uid = trace.get(lib.TRACE_SUMMARY_FIELD)
    if not summary_uid:
        cli.err_exit(f"Trace {orig_id} has no associated Trace Summary.")
    t_sum = search.search_for_trace_summary_by_uid(summary_uid)
    if not t_sum:
        cli.err_exit(f"Unable to find a Trace Summary for Trace {orig_id}")
    pol = sp.build_trace_suppression_policy(t_sum, include_users)
    cli.try_log("")
    if not prompt_upload_policy(pol):
        cli.try_log("Operation cancelled.")
        return
    apply.handle_apply_policy(pol.as_dict())


def prompt_upload_policy(pol: sp.TraceSuppressionPolicy) -> bool:
    """
    Prompts the user to upload a trace suppression policy.

    Args:
        pol (TraceSuppressionPolicy): The trace suppression policy to prompt
            for.

    Returns:
        bool: True if the user chooses to upload the policy, False otherwise.
    """
    query = "Scope:\n-------------\n"
    query += pol.policy_scope_string
    query += "\nSuppress spydertraces within this scope?"
    return cli.query_yes_no(query)
