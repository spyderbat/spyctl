import spyctl.api as api
import spyctl.cli as cli
import spyctl.config.configs as cfg
import spyctl.spyctl_lib as lib
import spyctl.filter_resource as filt
import spyctl.resources.notification_targets as nt
from typing import Dict, List

INTERACTIVE_SUPPORTED = [
    lib.NOTIFICATION_TARGETS_RESOURCE,
    lib.NOTIFICATION_CONFIGS_RESOURCE,
]


def handle_delete(resource, name_or_id):
    if resource == lib.NOTIFICATION_CONFIGS_RESOURCE:
        handle_delete_notif_config(name_or_id)
    elif resource == lib.NOTIFICATION_TARGETS_RESOURCE:
        handle_delete_notif_tgt(name_or_id)
    elif resource == lib.POLICIES_RESOURCE:
        handle_delete_policy(name_or_id)
    elif resource == lib.SUPPRESSION_POLICY_RESOURCE:
        handle_delete_suppression_policy(name_or_id)
    else:
        cli.err_exit(f"The 'delete' command is not supported for '{resource}'")


def handle_delete_notif_config(name_or_id):
    ctx = cfg.get_current_context()
    notif_pol = api.get_notification_policy(*ctx.get_api_data())
    routes: List = notif_pol.get(lib.ROUTES_FIELD, [])
    del_index = None
    del_id = None
    for i, route in enumerate(routes):
        id = route.get(lib.DATA_FIELD, {}).get(lib.ID_FIELD)
        name = route.get(lib.DATA_FIELD, {}).get(lib.NAME_FIELD)
        if id == name_or_id or name == name_or_id:
            if del_index is not None and name == name_or_id:
                cli.err_exit(f"{name_or_id} is ambiguous, use ID")
            del_index = i
            del_id = id
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
            id = tgt.get(lib.DATA_FIELD, {}).get(lib.ID_FIELD)
            if id is None:
                continue
            if id == name_or_id:
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

    policies = api.get_policies(*ctx.get_api_data())
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
        cli.err_exit(f"No policies matching name_or_uid '{name_or_uid}'")
    for uid, name in policies:
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
