"""Handles the test-notification subcommand for spyctl."""

import click

import spyctl.config.configs as cfg
import spyctl.resources.notification_targets as nt
import spyctl.spyctl_lib as lib
from spyctl import api, cli

# ----------------------------------------------------------------- #
#                   Test Notification Subcommand                    #
# ----------------------------------------------------------------- #


@click.command(
    "test-notification", cls=lib.CustomCommand, epilog=lib.SUB_EPILOG
)
@click.help_option("-h", "--help", hidden=True)
@click.option(
    "-T",
    "--targets",
    type=lib.ListParam(),
    metavar="",
    help="Comma-delimitated list of target names to send a test notification"
    " to. Use 'spyctl get notification-targets' to see what is available.",
)
def test_notification(targets):
    """Send test notifications to Targets or Notification Routes.

    Targets are named destinations like email, slack hooks, webhooks, or sns
    topics.
    Notification Routes define which notifications are send to which targets.
    Testing a notification route will send a test notification to one or many
    targets it is configured with.
    """
    handle_test_notification(targets)


# ----------------------------------------------------------------- #
#                    Test Notification Handlers                     #
# ----------------------------------------------------------------- #


def handle_test_notification(test_targets):
    """
    Sends a test notification to the specified targets.

    Args:
        test_targets (list): A list of target names or IDs to send the test
            notification to.

    Raises:
        SystemExit: If no targets are provided, or if there are no targets to
            test.

    Returns:
        None
    """
    if not test_targets:
        cli.err_exit("No targets provided.")
    ctx = cfg.get_current_context()
    notif_pol = api.get_notification_policy(*ctx.get_api_data())
    if not notif_pol or not notif_pol.get(lib.TARGETS_FIELD):
        cli.err_exit(
            "No targets to test. Use 'spyctl create notification-target'."
        )
    pol_targets = notif_pol.get(lib.TARGETS_FIELD)
    if not pol_targets:
        cli.err_exit("No targets to test.")
    for name_or_id in test_targets:
        test_target = None
        # check if name exists
        if name_or_id in pol_targets:
            tgt_data = pol_targets[name_or_id]
            test_target = nt.Target(backend_target={name_or_id: tgt_data})
        if not test_target:
            for tgt_name, tgt in pol_targets.items():
                tgt_id = tgt.get(lib.DATA_FIELD, {}).get(lib.ID_FIELD)
                if tgt_id is None:
                    continue
                if tgt_id == name_or_id:
                    test_target = nt.Target(backend_target={tgt_name: tgt})
                    break
        if not test_target:
            cli.err_exit(f"No notification targets matching '{name_or_id}'.")
        resp = api.post_test_notification(
            *ctx.get_api_data(), test_target.name
        )
        if resp.status_code == 200:
            cli.try_log(f"Successfully sent test to '{test_target.name}'")
