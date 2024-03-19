"""Handles the 'edit' subcommand for spyctl."""

# pylint: disable=broad-exception-caught

import json
import tempfile
from io import TextIOWrapper
from typing import IO, Callable, Dict

import click
import yaml

import spyctl.config.configs as cfg
import spyctl.resources.notification_configs as nc
import spyctl.resources.notification_targets as nt
import spyctl.resources.policies as p
import spyctl.schemas_v2 as schemas
import spyctl.spyctl_lib as lib
from spyctl import api, cli

# ----------------------------------------------------------------- #
#                          Edit Subcommand                          #
# ----------------------------------------------------------------- #


@click.command("edit", cls=lib.CustomCommand, epilog=lib.SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.argument("resource", type=lib.EditResourcesParam(), required=False)
@click.argument("name_or_id", required=False)
@click.option(
    "-f",
    "--filename",
    help="Filename to use to edit the resource.",
    metavar="",
    type=click.File(mode="r+"),
)
@click.option(
    "-y",
    "--yes",
    "--assume-yes",
    is_flag=True,
    help='Automatic yes to prompts; assume "yes" as answer to all prompts and'
    " run non-interactively.",
)
def edit(resource, name_or_id, filename, yes=False):
    """Edit resources by resource and name, or by resource and ids"""
    if yes:
        cli.set_yes_option()
    handle_edit(resource, name_or_id, filename)


# ----------------------------------------------------------------- #
#                          Edit Handlers                            #
# ----------------------------------------------------------------- #

EDIT_PROMPT = (
    "# Please edit the object below. Lines beginning with a '#' will be ignored,\n"  # noqa
    "# and an empty file will abort the edit. If an error occurs while saving this file will be\n"  # noqa
    "# reopened with the relevant failures.\n"
    "#\n"
)

KIND_TO_RESOURCE_TYPE: Dict[str, str] = {
    lib.BASELINE_KIND: lib.BASELINES_RESOURCE.name,
    lib.CONFIG_KIND: lib.CONFIG_ALIAS.name,
    lib.FPRINT_GROUP_KIND: lib.FINGERPRINT_GROUP_RESOURCE.name,
    lib.FPRINT_KIND: lib.FINGERPRINTS_RESOURCE.name,
    lib.POL_KIND: lib.POLICIES_RESOURCE.name,
    (lib.POL_KIND, lib.POL_TYPE_TRACE): lib.SUPPRESSION_POLICY_RESOURCE.name,
    lib.SECRET_KIND: lib.SECRETS_ALIAS.name,
    lib.UID_LIST_KIND: lib.UID_LIST_RESOURCE.name,
    lib.DEVIATION_KIND: lib.DEVIATIONS_RESOURCE.name,
    lib.NOTIFICATION_KIND: lib.NOTIFICATION_CONFIGS_RESOURCE.name,
    lib.TARGET_KIND: lib.NOTIFICATION_TARGETS_RESOURCE.name,
    lib.RULESET_KIND: "ruleset",
}


def handle_edit(resource=None, name_or_id=None, file: IO = None):
    """
    Handles the 'edit' command for a specified resource and name or id.

    Args:
        resource (str): The resource to edit.
        name_or_id (str): The name or id of the resource to edit.
        file (IO): The file to edit.

    Returns:
        None
    """
    if file:
        handle_edit_file(file)
    else:
        if not resource or not name_or_id:
            cli.err_exit("Must specify resource and name or id.")
        if resource == lib.CLUSTER_RULESET_RESOURCE:
            handle_edit_ruleset(name_or_id)
        elif resource == lib.NOTIFICATION_CONFIGS_RESOURCE:
            handle_edit_notif_config(name_or_id)
        elif resource == lib.NOTIFICATION_TARGETS_RESOURCE:
            handle_edit_notif_tgt(name_or_id)
        elif resource == lib.RULESETS_RESOURCE:
            handle_edit_ruleset(name_or_id)
        elif resource == lib.CONTAINER_POL_RESOURCE:
            handle_edit_policy(name_or_id, lib.POL_TYPE_CONT)
        elif resource == lib.LINUX_SVC_POL_RESOURCE:
            handle_edit_policy(name_or_id, lib.POL_TYPE_SVC)
        elif resource == lib.POLICIES_RESOURCE:
            handle_edit_policy(name_or_id)
        elif resource == lib.SUPPRESSION_POLICY_RESOURCE:
            handle_edit_policy(name_or_id, lib.POL_TYPE_TRACE)
        else:
            cli.err_exit(
                f"The 'edit' command is not supported for '{resource}'"
            )


def handle_edit_file(file: IO):
    """
    Handle editing a file.

    Args:
        file (IO): The file to be edited.

    Raises:
        ValueError: If the file is not a valid resource file.
        ValueError: If editing a resource of the given kind is not supported.
    """
    resource = lib.load_resource_file(file)
    if not isinstance(resource, Dict):
        cli.err_exit("Invalid file for editing.")
    kind = resource.get(lib.KIND_FIELD)
    if kind not in KIND_TO_RESOURCE_TYPE:
        cli.err_exit(f"Editing resource of kind '{kind}' not supported.")
    if kind == lib.POL_KIND:
        m_type = resource[lib.METADATA_FIELD][lib.METADATA_TYPE_FIELD]
        if m_type == lib.POL_TYPE_TRACE:
            kind = (lib.POL_KIND, lib.POL_TYPE_TRACE)
    m_type = resource[lib.METADATA_FIELD].get(lib.METADATA_TYPE_FIELD)
    resource_type = KIND_TO_RESOURCE_TYPE.get((kind, kind))
    if not resource_type:
        resource_type = KIND_TO_RESOURCE_TYPE[kind]
    edit_resource(
        cli.make_yaml(resource),
        file,
        resource_type,
        schemas.KIND_TO_SCHEMA[kind],
        apply_file_edits,
    )


def handle_edit_ruleset(name_or_id, rs_type=None):
    ctx = cfg.get_current_context()
    params = {
        "type": rs_type,
        "name_or_uid_contains": name_or_id,
    }
    rulesets = api.get_rulesets(*ctx.get_api_data(), params=params)
    if not rulesets:
        desc = f" {rs_type} " if rs_type else " "
        cli.err_exit(f"No{desc}rulesets matching '{name_or_id}'")
    if len(rulesets) > 1:
        cli.err_exit(f"Ruleset '{name_or_id}' is ambiguous, use full UID.")
    ruleset = rulesets[0]
    resource_yaml = cli.make_yaml(ruleset)
    edit_resource(
        resource_yaml,
        ruleset[lib.METADATA_FIELD][lib.METADATA_UID_FIELD],
        "ruleset",
        schemas.KIND_TO_SCHEMA[lib.RULESET_KIND],
        apply_ruleset_edits,
    )


def handle_edit_notif_config(name_or_id):
    """
    Edit a notification configuration based on the provided name or ID.

    Args:
        name_or_id (str): The name or ID of the notification configuration to
            edit.

    Raises:
        ValueError: If the provided name or ID is ambiguous or no matching
            notification configurations are found.
        ValueError: If editing legacy notification configurations is not
            supported.

    Returns:
        None
    """
    ctx = cfg.get_current_context()
    notif_pol = api.get_notification_policy(*ctx.get_api_data())
    routes = notif_pol.get(lib.ROUTES_FIELD)
    edit_index = None
    edit_id = None
    for i, route in enumerate(routes):
        notif_id = route.get(lib.DATA_FIELD, {}).get(lib.ID_FIELD)
        name = route.get(lib.DATA_FIELD, {}).get(lib.NAME_FIELD)
        if name_or_id in [name, notif_id]:
            if edit_index is not None and name == name_or_id:
                cli.err_exit(f"{name_or_id} is ambiguous, use ID")
            edit_index = i
            edit_id = notif_id
    if edit_index is None:
        cli.err_exit(f"No notification configs matching '{name_or_id}'.")
    config = (
        routes[edit_index]
        .get(lib.DATA_FIELD, {})
        .get(lib.NOTIF_SETTINGS_FIELD)
    )
    key = (
        lib.NOTIFICATION_KIND,
        config.get(lib.METADATA_FIELD).get(lib.METADATA_TYPE_FIELD),
    )
    if key not in schemas.KIND_TO_SCHEMA:
        key = lib.NOTIFICATION_KIND
    if not config:
        cli.err_exit("Editing legacy notification configs not supported.")
    resource_yaml = cli.make_yaml(config)
    edit_resource(
        resource_yaml,
        edit_id,
        lib.NOTIFICATION_CONFIGS_RESOURCE.name,
        schemas.KIND_TO_SCHEMA[key],
        apply_config_edits,
    )


def handle_edit_notif_tgt(name_or_id):
    """
    Handle the editing of a notification target based on the given name or ID.

    Args:
        name_or_id (str): The name or ID of the notification target to be
            edited.

    Returns:
        None
    """
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
            tgt_id = tgt.get(lib.DATA_FIELD, {}).get(lib.ID_FIELD)
            if tgt_id is None:
                continue
            if tgt_id == name_or_id:
                edit_tgt = nt.Target(backend_target={tgt_name: tgt})
                break
    if not edit_tgt:
        cli.err_exit(f"No notification targets matching '{name_or_id}'.")
    resource_yaml = cli.make_yaml(edit_tgt.as_dict())
    edit_resource(
        resource_yaml,
        edit_tgt.id,
        lib.NOTIFICATION_TARGETS_RESOURCE.name,
        schemas.NotificationTgtResourceModel,
        apply_tgt_edits,
    )


def handle_edit_policy(name_or_id, pol_type=None):
    """
    Handle the editing of a policy based on the given name or ID.

    Args:
        name_or_id (str): The name or ID of the policy to be edited.

    Returns:
        None
    """
    ctx = cfg.get_current_context()
    params = {
        "type": pol_type,
        "name_or_uid_contains": name_or_id,
    }
    policies = api.get_policies(*ctx.get_api_data(), params=params)
    if len(policies) > 1:
        cli.err_exit(f"Policy '{name_or_id}' is ambiguous, use full UID.")
    if not policies:
        desc = f" {pol_type} " if pol_type else " "
        cli.err_exit(f"No{desc}policies matching '{name_or_id}'.")
    policy = policies[0]
    resource_yaml = cli.make_yaml(policy)
    edit_resource(
        resource_yaml,
        policy[lib.METADATA_FIELD][lib.METADATA_UID_FIELD],
        lib.POLICIES_RESOURCE.name,
        schemas.KIND_TO_SCHEMA[lib.POL_KIND],
        apply_policy_edits,
    )


def edit_resource(
    resource_yaml: str,
    resource_id: str,
    resource_type,
    validator: Callable,
    apply_func: Callable,
):
    """
    Edit a resource using a YAML file.

    Args:
        resource_yaml (str): The YAML content of the resource.
        resource_id (str): The ID of the resource.
        resource_type: The type of the resource.
        validator (Callable): A function that validates the edited YAML
            content.
        apply_func (Callable): A function that applies the edited YAML content.

    Returns:
        None
    """
    temp_file = None
    while True:
        if not temp_file:
            edit_yaml = click.edit(
                __add_edit_prompt(resource_yaml), extension=".yaml"
            )
        else:
            try:
                with open(temp_file, "r", encoding="UTF-8") as f:
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
                edit_yaml,
                error,
                resource_id,
            )
            with open(temp_file, "w", encoding="UTF-8") as f:
                f.write(edit_yaml)
            cli.try_log(f"Edit failed, edits saved to {temp_file}")
            exit(1)
        if error:
            edit_yaml = __add_error_comments(
                resource_type,
                edit_yaml,
                error,
                resource_id,
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
    """
    Apply edits to a notification configuration.

    Args:
        edit_dict (Dict): A dictionary containing the edits to be applied.
        config_id (str): The ID of the configuration to be edited.
    """
    ctx = cfg.get_current_context()
    notif_pol = api.get_notification_policy(*ctx.get_api_data())
    config = nc.NotificationConfig(edit_dict)
    config.id = config_id
    routes = notif_pol.get(lib.ROUTES_FIELD, [])
    edit_index = None
    for i, route in enumerate(routes):
        cfg_id = route.get(lib.DATA_FIELD, {}).get(lib.ID_FIELD)
        if cfg_id == config_id:
            edit_index = i
            break
    if edit_index is None:
        cli.err_exit(f"Unable to locate config with id '{config_id}'")
    config.set_last_updated()
    routes[edit_index] = config.route
    notif_pol[lib.ROUTES_FIELD] = routes
    api.put_notification_policy(*ctx.get_api_data(), notif_pol)
    cli.try_log(f"Successfully edited Notification Config '{config.id}'")


def apply_tgt_edits(edit_dict: Dict, target_id: str):
    """
    Apply edits to a notification target identified by target_id.

    Args:
        edit_dict (Dict): A dictionary containing the edited target resource.
        target_id (str): The ID of the target to be edited.

    Raises:
        ValueError: If the target with the specified ID is not found.

    """
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


def apply_policy_edits(edit_dict: Dict, policy_id: str):
    """
    Apply edits to a policy identified by policy_id.

    Args:
        edit_dict (Dict): A dictionary containing the edited policy resource.
        policy_id (str): The ID of the policy to be edited.
    """
    ctx = cfg.get_current_context()
    pol_type = edit_dict[lib.METADATA_FIELD][lib.METADATA_TYPE_FIELD]
    # Ensure the user didn't manipulate the uid
    edit_dict[lib.METADATA_FIELD][lib.METADATA_UID_FIELD] = policy_id
    api.put_policy_update(*ctx.get_api_data(), edit_dict)
    cli.try_log(
        f"Successfully edited {__pol_resrc_name(pol_type)} '{policy_id}'"
    )


def apply_ruleset_edits(edit_dict: Dict, ruleset_id: str):
    ctx = cfg.get_current_context()
    edit_dict[lib.METADATA_FIELD][lib.METADATA_UID_FIELD] = ruleset_id
    api.put_ruleset_update(*ctx.get_api_data(), edit_dict)
    cli.try_log(f"Successfully edited Ruleset '{ruleset_id}'")


def apply_file_edits(resource, file: IO):
    """
    Apply edits to a file based on the given resource.

    Args:
        resource: The resource containing the edits.
        file (IO): The file to apply the edits to.

    """
    extension = ".json" if file.name.endswith(".json") else ".yaml"
    try:
        file.close()
        with open(file.name, "w", encoding="UTF-8") as f:
            if extension == ".json":
                f.write(json.dumps(resource, sort_keys=False, indent=2))
            else:
                f.write(cli.make_yaml(resource))
    except Exception as e:
        cli.err_exit(f"Unable to write output to {file.name}", exception=e)
    cli.try_log(f"Successfully edited resource file '{file.name}'")


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
    resource: str, yaml_string: str, error: str, name: str = None
):
    if isinstance(name, TextIOWrapper):
        name = f' "{name.name}" '
    else:
        name = f' "{name}" ' if name else ""
    yaml_string = __strip_comments(yaml_string)
    error_prompt = f"# {resource}{name}was not valid:\n"
    error = error.split("\n")
    error = ["# " + line for line in error]
    error = "\n".join(error)
    error_prompt += error + "\n#\n"
    rv = EDIT_PROMPT + error_prompt + yaml_string
    return rv


POL_TYPE_TO_RESOURCE_NAME: Dict[str, str] = {
    lib.POL_TYPE_TRACE: lib.SUPPRESSION_POLICY_RESOURCE.name,
    lib.POL_TYPE_SVC: lib.LINUX_SVC_POL_RESOURCE.name,
    lib.POL_TYPE_CONT: lib.CONTAINER_POL_RESOURCE.name,
}


def __pol_resrc_name(policy_type: str) -> str:
    return POL_TYPE_TO_RESOURCE_NAME.get(
        policy_type, lib.POLICIES_RESOURCE.name
    )
