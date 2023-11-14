import spyctl.api as api
import click
import spyctl.cli as cli
import spyctl.config.configs as cfg
import spyctl.spyctl_lib as lib
import spyctl.resources.notification_targets as nt
import spyctl.resources.notifications_configs as nc
import yaml
import spyctl.schemas_v2 as schemas
from typing import Dict, Callable
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
    edit_index = None
    edit_id = None
    for i, route in enumerate(routes):
        id = route.get(lib.DATA_FIELD, {}).get(lib.ID_FIELD)
        name = route.get(lib.DATA_FIELD, {}).get(lib.NAME_FIELD)
        if id == name_or_id or name == name_or_id:
            if edit_index is not None and name == name_or_id:
                cli.err_exit(f"{name_or_id} is ambiguous, use ID")
            edit_index = i
            edit_id = id
    if edit_index is None:
        cli.err_exit(f"No notification configs matching '{name_or_id}'.")
    config = (
        routes[edit_index]
        .get(lib.DATA_FIELD, {})
        .get(lib.NOTIF_SETTINGS_FIELD)
    )
    if not config:
        cli.err_exit("Editing legacy notification configs not supported.")
    resource_yaml = yaml.dump(config)
    edit_resource(
        resource_yaml,
        edit_id,
        lib.NOTIFICATION_CONFIGS_RESOURCE.name,
        schemas.NotificationConfigModel,
        apply_config_edits,
    )


def handle_edit_notif_tgt(name_or_id):
    ctx = cfg.get_current_context()
    notif_pol = api.get_notification_policy(*ctx.get_api_data())
    targets: Dict = notif_pol[lib.TARGETS_FIELD]
    edit_tgt = None
    # check if name exists
    if name_or_id in targets:
        tgt_data = targets[name_or_id]
        edit_tgt = nt.Target(backend_target={name_or_id: tgt_data})
    if not edit_tgt:
        for tgt_name, tgt in targets.items():
            id = tgt.get(lib.DATA_FIELD, {}).get(lib.ID_FIELD)
            if id is None:
                continue
            if id == name_or_id:
                edit_tgt = nt.Target(backend_target={tgt_name: tgt})
                break
    if not edit_tgt:
        cli.err_exit(f"No notification targets matching '{name_or_id}'.")
    resource_yaml = yaml.dump(edit_tgt.as_dict())
    edit_resource(
        resource_yaml,
        edit_tgt.id,
        lib.NOTIFICATION_TARGETS_RESOURCE.name,
        schemas.NotificationTgtResourceModel,
        apply_tgt_edits,
    )


def edit_resource(
    resource_yaml: str,
    resource_id: str,
    resource_type,
    validator: Callable,
    apply_func: Callable,
):
    temp_file = None
    while True:
        if not temp_file:
            edit_yaml = click.edit(
                __add_edit_prompt(resource_yaml), extension=".yaml"
            )
        else:
            try:
                with open(temp_file, "r") as f:
                    tmp_yaml = f.read()
                edit_yaml = click.edit(tmp_yaml, extension=".yaml")
            except Exception as e:
                cli.err_exit(str(e))
        if not edit_yaml or __strip_comments(edit_yaml) == resource_yaml:
            cli.try_log("Edit cancelled, no changes made.")
            exit(0)
        try:
            edit_dict = yaml.load(edit_yaml, lib.UniqueKeyLoader)
            error = None
            validator(**edit_dict)
        except Exception as e:
            error = str(e)
        if error and temp_file:
            edit_yaml = __add_error_comments(
                resource_type,
                resource_id,
                edit_yaml,
                error,
            )
            with open(temp_file, "w") as f:
                f.write(edit_yaml)
            cli.try_log(f"Edit failed, edits saved to {temp_file}")
            exit(1)
        if error:
            edit_yaml = __add_error_comments(
                resource_type,
                resource_id,
                edit_yaml,
                error,
            )
            temp_file = tempfile.NamedTemporaryFile(
                "w", delete=False, prefix="spyctl-edit-", suffix=".yaml"
            )
            temp_file.write(edit_yaml)
            cli.try_log(f"Edit failed, edits saved to {temp_file.name}")
            temp_file.close()
            temp_file = temp_file.name
            continue
        else:
            apply_func(edit_dict, resource_id)
            break


def apply_config_edits(edit_dict: Dict, config_id: str):
    ctx = cfg.get_current_context()
    notif_pol = api.get_notification_policy(*ctx.get_api_data())
    config = nc.NotificationConfig(edit_dict)
    config.id = config_id
    routes = notif_pol.get(lib.ROUTES_FIELD, [])
    edit_index = None
    for i, route in enumerate(routes):
        id = route.get(lib.DATA_FIELD, {}).get(lib.ID_FIELD)
        if id == config_id:
            edit_index = i
            break
    if edit_index is None:
        cli.err_exit(f"Unable to locate config with id '{config_id}'")
    config.set_last_updated()
    routes[i] = config.route
    notif_pol[lib.ROUTES_FIELD] = routes
    api.put_notification_policy(*ctx.get_api_data(), notif_pol)
    cli.try_log(f"Successfully edited Notification Config '{config.id}'")


def apply_tgt_edits(edit_dict: Dict, target_id: str):
    ctx = cfg.get_current_context()
    notif_pol = api.get_notification_policy(*ctx.get_api_data())
    target = nt.Target(target_resource=edit_dict)
    target.id = target_id
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
    if not old_tgt:
        cli.err_exit(f"Unable to locate config with id '{target_id}'")
    old_name = next(iter(old_tgt))
    targets.pop(old_name)
    target.set_last_update_time()
    new_tgt = target.as_target()
    targets.update(**new_tgt)
    notif_pol[lib.TARGETS_FIELD] = targets
    api.put_notification_policy(*ctx.get_api_data(), notif_pol)
    cli.try_log(f"Successfully edited Notification Target '{target.id}'")


def __strip_comments(yaml_string: str) -> str:
    lines = []
    for line in yaml_string.split("\n"):
        if line.strip().startswith("#"):
            continue
        lines.append(line)
    return "\n".join(lines)


def __add_edit_prompt(yaml_string: str):
    return EDIT_PROMPT + yaml_string


def __add_error_comments(
    resource: str, name: str, yaml_string: str, error: str
):
    yaml_string = __strip_comments(yaml_string)
    error_prompt = f'# {resource} "{name}" was not valid:\n'
    error = error.split("\n")
    error = ["# " + line for line in error]
    error = "\n".join(error)
    error_prompt += error + "\n#\n"
    rv = EDIT_PROMPT + error_prompt + yaml_string
    return rv
