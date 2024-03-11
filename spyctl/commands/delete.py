"""Handles the delete subcommand for spyctl."""

from typing import Dict, List

import click

import spyctl.config.configs as cfg
import spyctl.filter_resource as filt
import spyctl.spyctl_lib as lib
from spyctl import api, cli

# ----------------------------------------------------------------- #
#                        Delete Subcommand                          #
# ----------------------------------------------------------------- #


@click.command("delete", cls=lib.CustomCommand, epilog=lib.SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.argument("resource", type=lib.DelResourcesParam())
@click.argument("name_or_id", required=False)
@click.option(
    "-y",
    "--yes",
    "--assume-yes",
    is_flag=True,
    help='Automatic yes to prompts; assume "yes" as answer to all prompts and'
    " run non-interactively.",
)
def delete(resource, name_or_id, yes=False):
    """Delete resources by resource and name, or by resource and ids"""
    if yes:
        cli.set_yes_option()
    handle_delete(resource, name_or_id)


# ----------------------------------------------------------------- #
#                         Delete Handlers                           #
# ----------------------------------------------------------------- #


def handle_delete(resource, name_or_id):
    if resource == lib.CLUSTER_RULESET_RESOURCE:
        handle_delete_ruleset(name_or_id)
    elif resource == lib.NOTIFICATION_CONFIGS_RESOURCE:
        handle_delete_notif_config(name_or_id)
    elif resource == lib.NOTIFICATION_TARGETS_RESOURCE:
        handle_delete_notif_tgt(name_or_id)
    elif resource == lib.POLICIES_RESOURCE:
        handle_delete_policy(name_or_id)
    elif resource == lib.SUPPRESSION_POLICY_RESOURCE:
        handle_delete_suppression_policy(name_or_id)
    else:
        cli.err_exit(f"The 'delete' command is not supported for '{resource}'")


def handle_delete_ruleset(name_or_id):
    ctx = cfg.get_current_context()
    params = {"name_or_uid_contains": name_or_id}
    rulesets = api.get_rulesets(*ctx.get_api_data(), params=params)
    if not rulesets:
        cli.err_exit(f"No rulesets matching '{name_or_id}'")
    for rs in rulesets:
        name = rs[lib.METADATA_FIELD][lib.METADATA_NAME_FIELD]
        uid = rs[lib.METADATA_FIELD][lib.METADATA_UID_FIELD]
        perform_delete = cli.query_yes_no(
            f"Are you sure you want to delete ruleset '{name} - {uid}' from Spyderbat?"  # noqa
        )
        if perform_delete:
            api.delete_ruleset(
                *ctx.get_api_data(),
                rs[lib.METADATA_FIELD][lib.METADATA_UID_FIELD],
            )
            cli.try_log(f"Successfully deleted ruleset '{name} - {uid}'")
        else:
            cli.try_log(f"Skipping delete of '{name} -- {uid}'")


def handle_delete_notif_config(name_or_id):
    ctx = cfg.get_current_context()
    notif_pol = api.get_notification_policy(*ctx.get_api_data())
    routes: List = notif_pol.get(lib.ROUTES_FIELD, [])
    del_index = None
    del_id = None
    for i, route in enumerate(routes):
        cfg_id = route.get(lib.DATA_FIELD, {}).get(lib.ID_FIELD)
        name = route.get(lib.DATA_FIELD, {}).get(lib.NAME_FIELD)
        if cfg_id == name_or_id or name == name_or_id:
            if del_index is not None and name == name_or_id:
                cli.err_exit(f"{name_or_id} is ambiguous, use ID")
            del_index = i
            del_id = cfg_id
    if del_index is None:
        cli.err_exit(f"No notification config matching '{name_or_id}'")
    if cli.query_yes_no(
        f"Are you sure you want to delete notification config {del_id}"
    ):
        routes.pop(del_index)
        notif_pol[lib.ROUTES_FIELD] = routes
        api.put_notification_policy(*ctx.get_api_data(), notif_pol)
        cli.try_log(f"Successfully deleted notification config '{del_id}'")


def handle_delete_notif_tgt(name_or_id):
    ctx = cfg.get_current_context()
    notif_pol = api.get_notification_policy(*ctx.get_api_data())
    targets: Dict = notif_pol.get(lib.TARGETS_FIELD, {})
    del_name = None
    # check if name exists
    if name_or_id in targets:
        del_name = name_or_id
    if not del_name:
        for tgt_name, tgt in targets.items():
            tgt_id = tgt.get(lib.DATA_FIELD, {}).get(lib.ID_FIELD)
            if tgt_id is None:
                continue
            if tgt_id == name_or_id:
                del_name = tgt_name
    if not del_name:
        cli.err_exit(f"No notification target matching '{name_or_id}'.")
    if cli.query_yes_no(
        "Are you sure you want to delete notification target" f" '{del_name}'?"
    ):
        notif_pol = api.get_notification_policy(*ctx.get_api_data())
        notif_pol[lib.TARGETS_FIELD].pop(del_name)
        api.put_notification_policy(*ctx.get_api_data(), notif_pol)
        cli.try_log(f"Successfully deleted notification target '{del_name}'")


def handle_delete_policy(name_or_uid):
    ctx = cfg.get_current_context()
    params = {"name_or_uid_contains": name_or_uid}
    policies = api.get_policies(*ctx.get_api_data(), params=params)
    if len(policies) == 0:
        cli.err_exit(f"No policies matching name_or_uid '{name_or_uid}'")
    for policy in policies:
        name = policy[lib.METADATA_FIELD][lib.METADATA_NAME_FIELD]
        uid = policy[lib.METADATA_FIELD][lib.METADATA_UID_FIELD]
        perform_delete = cli.query_yes_no(
            f"Are you sure you want to delete policy '{name} - {uid}' from"
            " Spyderbat?"
        )
        if perform_delete:
            api.delete_policy(
                *ctx.get_api_data(),
                uid,
            )
            cli.try_log(f"Successfully deleted policy '{name} - {uid}'")
        else:
            cli.try_log(f"Skipping delete of '{name} - {uid}'")


def handle_delete_suppression_policy(name_or_uid):
    ctx = cfg.get_current_context()

    policies = api.get_policies(
        *ctx.get_api_data(), {lib.TYPE_FIELD: lib.POL_TYPE_TRACE}
    )
    policies = [
        (
            p[lib.METADATA_FIELD][lib.METADATA_UID_FIELD],
            p[lib.METADATA_FIELD][lib.METADATA_NAME_FIELD],
        )
        for p in filt.filter_obj(
            policies,
            [
                [lib.METADATA_FIELD, lib.METADATA_NAME_FIELD],
                [lib.METADATA_FIELD, lib.METADATA_UID_FIELD],
            ],
            name_or_uid,
        )
    ]
    if len(policies) == 0:
        cli.err_exit(
            f"No suppression policies matching name_or_uid '{name_or_uid}'"
        )
    for uid, name in policies:
        perform_delete = cli.query_yes_no(
            f"Are you sure you want to delete suppression policy "
            f"'{name} - {uid}' from Spyderbat?"
        )
        if perform_delete:
            api.delete_policy(
                *ctx.get_api_data(),
                uid,
            )
            cli.try_log(f"Successfully deleted policy '{name} - {uid}'")
        else:
            cli.try_log(f"Skipping delete of '{name} - {uid}'")
