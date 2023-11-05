import spyctl.api as api
import random
import click
import spyctl.cli as cli
import spyctl.config.configs as cfg
import spyctl.spyctl_lib as lib
import spyctl.filter_resource as filt
import spyctl.resources.notification_targets as nt
import spyctl.resources.notifications_configs as nc
import yaml
import spyctl.schemas_v2 as schemas
from pydantic import ValidationError
from typing import Dict
import tempfile

INTERACTIVE_SUPPORTED = [
    lib.NOTIFICATION_TARGETS_RESOURCE,
    lib.NOTIFICATION_CONFIGS_RESOURCE,
]

EDIT_PROMPT = (
    "# Please edit the object below. Lines beginning with a '#' will be ignored,\n"
    "# and an empty file will abort the edit. If an error occurs while saving this file will be\n"
    "# reopened with the relevant failures.\n"
    "#\n"
)


def handle_edit(resource, name_or_id):
    if resource == lib.NOTIFICATION_CONFIGS_RESOURCE:
        handle_edit_notif_config(name_or_id)
    elif resource == lib.NOTIFICATION_TARGETS_RESOURCE:
        handle_edit_notif_tgt(name_or_id)
    else:
        cli.err_exit(f"The 'edit' command is not supported for '{resource}'")


def handle_edit_notif_config(name_or_id):
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


def handle_edit_notif_tgt(name_or_id):
    ctx = cfg.get_current_context()
    notif_pol = api.get_notification_policy(*ctx.get_api_data())
    targets: Dict = notif_pol[lib.TARGETS_FIELD]
    edit_tgt = None
    edit_name = None
    # check if name exists
    if name_or_id in targets:
        tgt_data = targets[name_or_id]
        edit_tgt = nt.Target(backend_target={name_or_id: tgt_data})
        edit_name = name_or_id
    if not edit_tgt:
        for tgt_name, tgt in targets.items():
            id = tgt.get(lib.DATA_FIELD, {}).get(lib.ID_FIELD)
            if id is None:
                continue
            if id == name_or_id:
                edit_tgt = nt.Target(backend_target={tgt_name: tgt})
                edit_name = tgt_name
                break
    if not edit_tgt:
        cli.err_exit(f"No notification targets matching '{name_or_id}'.")
    resource_yaml = yaml.dump(edit_tgt.as_dict())
    seen_error = False
    while True:
        edit_yaml = click.edit(resource_yaml, extension=".yaml")
        if edit_yaml == resource_yaml:
            cli.try_log("Edit cancelled, no changes mane.")
            exit(0)
        try:
            edit_dict = yaml.load(edit_yaml)
            error = None
            schemas.NotificationTgtResourceModel(**edit_dict)
        except Exception as e:
            error = str(e)
        if error and seen_error:
            edit_yaml = __add_error_comments(
                lib.NOTIFICATION_TARGETS_RESOURCE.name,
                edit_name,
                edit_yaml,
                error,
            )

        if error:
            seen_error = True

        edited_tgt = click.edit(tgt_yaml)
        if edited_tgt is None:
            cli.try_log("Operation cancelled.")
            return
        try:
            edits = yaml.load(edited_tgt, lib.UniqueKeyLoader)
        except Exception as e:
            cli.notice(f"Error: Unable to load edited yaml.\n{e}")
            continue
        if not schemas.valid_notification_target(edits, True):
            continue
        break
    if edits and cli.query_yes_no(
        "Are you sure you want to update notification target"
        f" '{name_or_id}'?"
    ):
        nt.NotificationTarget(nam)
        cli.try_log(f"Successfully updated notification target '{name_or_id}'")


def __strip_comments(yaml_string: str) -> str:
    lines = []
    for line in yaml_string.split("\n"):
        if line.strip().startswith("#"):
            continue
        lines.append(line)


def __add_error_comments(
    resource: str, name: str, yaml_string: str, error: str
):
    yaml_string = __strip_comments(yaml_string)
    error_prompt = f'{resource} "{name}" was not valid:\n{error}\n#\n'
    rv = EDIT_PROMPT + error_prompt + yaml_string
    return rv


def __tmp_filename():
    return random.randint(1, 10000)
