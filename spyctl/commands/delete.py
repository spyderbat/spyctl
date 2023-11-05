import spyctl.api as api
import spyctl.cli as cli
import spyctl.config.configs as cfg
import spyctl.spyctl_lib as lib
import spyctl.filter_resource as filt
import spyctl.resources.notification_targets as nt
from typing import Dict

INTERACTIVE_SUPPORTED = [
    lib.NOTIFICATION_TARGETS_RESOURCE,
    lib.NOTIFICATION_CONFIGS_RESOURCE,
]


def handle_delete(resource, name_or_id, interactive=False):
    if not interactive and not name_or_id:
        cli.err_exit("Name or ID must be provided if not interactive.")
    if interactive and resource not in INTERACTIVE_SUPPORTED:
        cli.err_exit(
            f"The interactive delete is not supported for '{resource}'"
        )
    if interactive:
        lib.set_interactive()
    if resource == lib.NOTIFICATION_CONFIGS_RESOURCE:
        handle_delete_notif_config(name_or_id, interactive)
    elif resource == lib.NOTIFICATION_TARGETS_RESOURCE:
        handle_delete_notif_tgt(name_or_id, interactive)
    elif resource == lib.POLICIES_RESOURCE:
        handle_delete_policy(name_or_id)
    elif resource == lib.SUPPRESSION_POLICY_RESOURCE:
        handle_delete_suppression_policy(name_or_id)
    else:
        cli.err_exit(f"The 'delete' command is not supported for '{resource}'")


def handle_delete_notif_config(name_or_id, interactive):
    ctx = cfg.get_current_context()
    notif_pol = api.get_notification_policy(*ctx.get_api_data())

    if True:
        nt.interactive_targets(notif_pol, "delete", name_or_id)
    else:
        pass


def handle_delete_notif_tgt(name_or_id):
    ctx = cfg.get_current_context()
    notif_pol = api.get_notification_policy(*ctx.get_api_data())
    targets: Dict = notif_pol[lib.TARGETS_FIELD]
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
        cli.err_exit(f"No notification targets matching '{name_or_id}'.")
    if cli.query_yes_no(
        "Are you sure you want to delete notification target" f" {del_name}?"
    ):
        notif_pol = api.get_notification_policy(*ctx.get_api_data())
        notif_pol[lib.TARGETS_FIELD].pop(del_name)
        resp = api.put_notification_policy(notif_pol)
        if resp.status_code == 200:
            cli.try_log(
                f"Successfully deleted notification target '{name_or_id}'"
            )
        else:
            cli.try_log("Unable perform delete of notification target.")


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
