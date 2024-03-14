"""Handles the apply subcommand for the spyctl."""

import json
from typing import Dict, List

import click

import spyctl.commands.merge as m
import spyctl.config.configs as cfg
import spyctl.resources as _r
import spyctl.spyctl_lib as lib
from spyctl import api, cli

# ----------------------------------------------------------------- #
#                         Apply Subcommand                          #
# ----------------------------------------------------------------- #


@click.command("apply", cls=lib.CustomCommand, epilog=lib.SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True, is_eager=True)
@click.option(
    "-f",
    "--filename",
    help="Filename containing Spyderbat resource.",
    metavar="",
    type=click.File(),
    required=True,
)
def apply(filename):
    """Apply a configuration to a resource by file name."""
    handle_apply(filename)


# ----------------------------------------------------------------- #
#                          Apply Handlers                           #
# ----------------------------------------------------------------- #

APPLY_PRIORITY = {
    lib.RULESET_KIND: 100,
    lib.POL_KIND: 50,
}


def handle_apply(filename):
    """
    Apply new resources or update existing resources.

    Args:
        filename (str): The path to the resource file.

    Returns:
        None
    """
    resrc_data = lib.load_resource_file(filename)
    if lib.ITEMS_FIELD in resrc_data:
        for resrc in resrc_data[lib.ITEMS_FIELD]:
            # Sort resource items by priority
            resrc_data[lib.ITEMS_FIELD].sort(
                key=__apply_priority, reverse=True
            )
            __handle_apply(resrc)
    else:
        __handle_apply(resrc_data)


def __handle_apply(resrc_data: Dict):
    kind = resrc_data.get(lib.KIND_FIELD)
    if kind == lib.POL_KIND:
        handle_apply_policy(resrc_data)
    elif kind == lib.NOTIFICATION_KIND:
        handle_apply_notification_config(resrc_data)
    elif kind == lib.TARGET_KIND:
        handle_apply_notification_target(resrc_data)
    elif kind == lib.RULESET_KIND:
        handle_apply_ruleset(resrc_data)
    else:
        cli.err_exit(f"The 'apply' command is not supported for {kind}")


def handle_apply_policy(policy: Dict):
    """
    Apply a policy to the current context.

    Args:
        policy (Dict): The policy to be applied.

    Returns:
        None
    """
    ctx = cfg.get_current_context()
    pol_type = policy[lib.METADATA_FIELD][lib.METADATA_TYPE_FIELD]
    sub_type = _r.policies.get_policy_subtype(pol_type)
    uid = policy[lib.METADATA_FIELD].get(lib.METADATA_UID_FIELD)
    if uid:
        resp = api.put_policy_update(*ctx.get_api_data(), policy)
        if resp.status_code == 200:
            cli.try_log(f"Successfully updated policy {uid}")
    else:
        resp = api.post_new_policy(*ctx.get_api_data(), policy)
        if resp and resp.text:
            uid = json.loads(resp.text).get("uid", "")
            cli.try_log(
                f"Successfully applied new {pol_type} {sub_type} policy with uid: {uid}"  # noqa
            )


def handle_apply_ruleset(ruleset: Dict):
    """
    Apply a ruleset to the current context.

    Args:
        ruleset (Dict): The ruleset to be applied.

    Returns:
        None
    """
    ctx = cfg.get_current_context()
    rs_type = ruleset[lib.METADATA_FIELD][lib.METADATA_TYPE_FIELD]
    uid = ruleset[lib.METADATA_FIELD].get(lib.METADATA_UID_FIELD)
    if uid:
        resp = api.put_ruleset_update(*ctx.get_api_data(), ruleset)
        if resp.status_code == 200:
            cli.try_log(f"Successfully updated ruleset {uid}")
    else:
        resp = api.post_new_ruleset(*ctx.get_api_data(), ruleset)
        if resp and resp.json():
            uid = resp.json().get("uid", "")
            cli.try_log(
                f"Successfully applied new {rs_type} ruleset with uid: {uid}"
            )


def handle_apply_notification_target(notif_target: Dict):
    """
    Apply a notification target to the current context.

    Args:
        notif_target (Dict): The notification target to be applied.

    Returns:
        None
    """
    ctx = cfg.get_current_context()
    target = _r.notification_targets.Target(target_resource=notif_target)
    notif_pol = api.get_notification_policy(*ctx.get_api_data())
    targets: Dict = notif_pol.get(lib.TARGETS_FIELD, {})
    old_tgt = None
    for tgt_name, tgt_data in targets.items():
        tgt_id = tgt_data.get(lib.DATA_FIELD, {}).get(lib.ID_FIELD)
        if not tgt_id:
            continue
        if tgt_id == target.id:
            old_tgt = {tgt_name: tgt_data}
            break
        if tgt_name == target.name:
            cli.err_exit("Target names must be unique!")
    if old_tgt:
        tgt_name = next(iter(old_tgt))
        targets.pop(tgt_name)
    target.set_last_update_time()
    new_tgt = target.as_target()
    targets.update(**new_tgt)
    notif_pol[lib.TARGETS_FIELD] = targets
    api.put_notification_policy(*ctx.get_api_data(), notif_pol)
    if old_tgt:
        cli.try_log(f"Successfully updated Notification Target '{target.id}'")
    else:
        cli.try_log(f"Successfully applied Notification Target '{target.id}'")


def handle_apply_notification_config(notif_config: Dict):
    """
    Apply a notification configuration to the current context.

    Args:
        notif_config (Dict): The notification configuration to be applied.

    Returns:
        None
    """
    ctx = cfg.get_current_context()
    config = _r.notification_configs.NotificationConfig(
        config_resource=notif_config
    )
    notif_pol = api.get_notification_policy(*ctx.get_api_data())
    routes: List[Dict] = notif_pol.get(lib.ROUTES_FIELD, [])
    old_route_index = None
    for i, route in enumerate(routes):
        route_id = route.get(lib.DATA_FIELD, {}).get(lib.ID_FIELD)
        if not route_id:
            continue
        if route_id == config.id:
            old_route_index = i
    if old_route_index is not None:
        routes.pop(old_route_index)
    config.set_last_updated()
    new_route = config.route
    routes.append(new_route)
    notif_pol[lib.ROUTES_FIELD] = routes
    api.put_notification_policy(*ctx.get_api_data(), notif_pol)
    if old_route_index:
        cli.try_log(f"Successfully updated Notification Config '{config.id}'")
    else:
        cli.try_log(f"Successfully applied Notification Config '{config.id}'")


# ----------------------------------------------------------------- #
#                          Helper Functions                         #
# ----------------------------------------------------------------- #


def __apply_priority(resrc: Dict) -> int:
    kind = resrc.get(lib.KIND_FIELD)
    return APPLY_PRIORITY.get(kind, 0)


def __handle_matching_policies(
    policy: Dict, matching_policies: Dict[str, Dict]
):
    uid = policy[lib.METADATA_FIELD].get(lib.METADATA_UID_FIELD)
    if uid:
        return _r.suppression_policies.TraceSuppressionPolicy(policy)
    query = (
        "There already exists a policy matching this scope. Would you like"
        " to merge this policy into the existing one?"
    )
    if not cli.query_yes_no(query):
        return _r.suppression_policies.TraceSuppressionPolicy(policy)
    ret_pol = policy
    for uid, m_policy in matching_policies.items():
        merged = m.merge_resource(ret_pol, "", m_policy)
        if merged:
            ret_pol = merged.get_obj_data()
    ret_pol[lib.METADATA_FIELD][lib.METADATA_UID_FIELD] = uid
    return _r.suppression_policies.TraceSuppressionPolicy(ret_pol)
