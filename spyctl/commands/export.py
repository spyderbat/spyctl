"""Handle the export subcommand for spyctl."""

from typing import Optional

import click

import spyctl.config.configs as cfg
import spyctl.filter_resource as filt
import spyctl.resources.notification_configs as n_configs
import spyctl.resources.notification_targets as n_targets
import spyctl.resources.suppression_policies as s_pol
import spyctl.spyctl_lib as lib
from spyctl import api, cli

# ----------------------------------------------------------------- #
#                         Export Subcommand                         #
# ----------------------------------------------------------------- #


@click.command("export", cls=lib.CustomCommand, epilog=lib.SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.argument("resource", type=lib.ExportResourcesParam())
@click.argument("name_or_id", required=False)
@click.option(
    "-E",
    "--exact",
    "--exact-match",
    is_flag=True,
    help="Exact match for NAME_OR_ID. This command's default behavior"
    "displays any resource that contains the NAME_OR_ID.",
)
def export(resource, exact=False, name_or_id=None):
    """Export Spyderbat Resources for later use to import."""
    handle_export(resource, name_or_id, exact)


# ----------------------------------------------------------------- #
#                          Export Handlers                          #
# ----------------------------------------------------------------- #


def handle_export(
    resource: str, name_or_id: Optional[str], exact: bool
) -> None:

    if name_or_id and not exact:
        name_or_id = name_or_id + "*" if name_or_id[-1] != "*" else name_or_id
        name_or_id = "*" + name_or_id if name_or_id[0] != "*" else name_or_id

    if resource == lib.SUPPRESSION_POLICY_RESOURCE:
        handle_export_suppression_policies(name_or_id)
    elif resource == lib.NOTIFICATION_CONFIGS_RESOURCE:
        handle_export_notification_configs(name_or_id)
    else:
        cli.err_exit(f"The 'export' command is not supported for {resource}")


def handle_export_suppression_policies(name_or_id: Optional[str]) -> None:
    ctx = cfg.get_current_context()
    policies = api.get_policies(
        *ctx.get_api_data(),
        params={lib.METADATA_TYPE_FIELD: lib.POL_TYPE_TRACE},
    )
    if name_or_id:
        policies = filt.filter_obj(
            policies,
            [
                [lib.METADATA_FIELD, lib.NAME_FIELD],
                [lib.METADATA_FIELD, lib.METADATA_UID_FIELD],
            ],
            name_or_id,
        )
    for policy in policies:
        metadata: dict = {}
        metadata[lib.METADATA_NAME_FIELD] = policy[lib.METADATA_FIELD][
            lib.METADATA_NAME_FIELD
        ]
        metadata[lib.METADATA_TYPE_FIELD] = policy[lib.METADATA_FIELD][
            lib.METADATA_TYPE_FIELD
        ]
        policy[lib.METADATA_FIELD] = metadata
    policies = s_pol.s_policies_output(policies)
    cli.show(policies, lib.OUTPUT_YAML)


def handle_export_notification_configs(name_or_id: Optional[str]) -> None:
    ctx = cfg.get_current_context()
    n_pol = api.get_notification_policy(*ctx.get_api_data())
    if n_pol is None or not isinstance(n_pol, dict):
        cli.err_exit("Could not load notification policy")
    routes = n_pol.get(lib.ROUTES_FIELD, [])
    if name_or_id:
        routes = filt.filter_obj(routes, ["data.id", "data.name"], name_or_id)

    # remove the uids and build up the list of targets required
    target_names_in_configs: set = set()
    configs_to_export = []
    targets_to_export = []
    for route in routes:
        data = route[lib.NOTIF_DATA_FIELD]
        notif_settings = data.get(lib.NOTIF_SETTINGS_FIELD)
        if notif_settings is None:
            continue
        targets = notif_settings.get(lib.SPEC_FIELD, {}).get(
            lib.NOTIF_TARGET_FIELD, []
        )
        if isinstance(targets, list):
            target_names_in_configs |= set(targets)
        else:
            if targets:
                target_names_in_configs.add(targets)

        if lib.ID_FIELD in data:
            del data[lib.ID_FIELD]
        if "uid" in data:
            del data["uid"]
        if lib.METADATA_UID_FIELD in notif_settings:
            del notif_settings[lib.METADATA_UID_FIELD]
        configs_to_export.append(n_configs.NotificationConfig(notif_settings))

    all_targets = n_pol.get(lib.TARGETS_FIELD, [])
    for target_name in target_names_in_configs:
        txp = {target_name: all_targets[target_name]}
        del txp[target_name][lib.NOTIF_DATA_FIELD][lib.ID_FIELD]
        targets_to_export.append(n_targets.Target(backend_target=txp))

    exported = {
        lib.API_FIELD: lib.API_VERSION,
        lib.ITEMS_FIELD: [target.as_dict() for target in targets_to_export]
        + [config.as_dict() for config in configs_to_export],
    }

    cli.show(exported, lib.OUTPUT_YAML)
