import spyctl.api as api
import click
import spyctl.cli as cli
import spyctl.config.configs as cfg
import spyctl.spyctl_lib as lib
import spyctl.filter_resource as filt
import spyctl.resources.notification_targets as nt
import spyctl.resources.notifications_configs as nc
import yaml
import spyctl.schemas_v2 as schemas


INTERACTIVE_SUPPORTED = [
    lib.NOTIFICATION_TARGETS_RESOURCE,
    lib.NOTIFICATION_CONFIGS_RESOURCE,
]


def handle_edit(resource, name_or_id, interactive=False):
    if not interactive and not name_or_id:
        cli.err_exit("Name or ID must be provided if not interactive.")
    if interactive and resource not in INTERACTIVE_SUPPORTED:
        cli.err_exit(
            f"The interactive delete is not supported for '{resource}'"
        )
    if interactive:
        lib.set_interactive()
    if resource == lib.NOTIFICATION_CONFIGS_RESOURCE:
        handle_edit_notif_config(name_or_id, interactive)
    elif resource == lib.NOTIFICATION_TARGETS_RESOURCE:
        handle_edit_notif_tgt(name_or_id, interactive)
    else:
        cli.err_exit(f"The 'edit' command is not supported for '{resource}'")


def handle_edit_notif_config(name_or_id, interactive):
    ctx = cfg.get_current_context()
    notif_pol = api.get_notification_policy(*ctx.get_api_data())
    routes = notif_pol.get(lib.ROUTES_FIELD)
    config_id = None
    if name_or_id:
        routes = filt.filter_obj(routes, ["data.id", "data.name"], name_or_id)
        if routes:
            config_id = routes[0].get(lib.DATA_FIELD, {}).get(lib.ID_FIELD)
    if True:
        nc.interactive_notifications(notif_pol, "edit", config_id)
    else:
        config = (
            routes[0].get(lib.DATA_FIELD, {}).get(lib.NOTIF_SETTINGS_FIELD)
        )
        if not config:
            cli.err_exit("Editing legacy notifications is not supported.")
        while True:
            break


def handle_edit_notif_tgt(name_or_id, interactive):
    ctx = cfg.get_current_context()
    notif_pol = api.get_notification_policy(*ctx.get_api_data())
    if True:
        nt.interactive_targets(notif_pol, "edit", name_or_id)
    else:
        pass
        # targets = notif_pol[lib.TARGETS_FIELD]
        # if name_or_id not in targets:
        #     cli.err_exit(f"No notification targets matching '{name_or_id}'.")
        # tgt_yaml = yaml.dump({name_or_id: targets[name_or_id]})
        # while True:
        #     edited_tgt = click.edit(tgt_yaml)
        #     if edited_tgt is None:
        #         cli.try_log("Operation cancelled.")
        #         return
        #     try:
        #         edits = yaml.load(edited_tgt, lib.UniqueKeyLoader)
        #     except Exception as e:
        #         cli.notice(f"Error: Unable to load edited yaml.\n{e}")
        #         continue
        #     if not schemas.valid_notification_target(edits, True):
        #         continue
        #     break
        # if edits and cli.query_yes_no(
        #     "Are you sure you want to update notification target"
        #     f" '{name_or_id}'?"
        # ):
        #     nt.NotificationTarget(nam)
        #     cli.try_log(
        #         f"Successfully updated notification target '{name_or_id}'"
        #     )
