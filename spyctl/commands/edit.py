import spyctl.api as api
import click
import spyctl.cli as cli
import spyctl.config.configs as cfg
import spyctl.spyctl_lib as lib
import spyctl.filter_resource as filt
import spyctl.resources.notification_targets as nt
import yaml


INTERACTIVE_SUPPORTED = [lib.NOTIFICATION_TARGETS_RESOURCE]


def handle_edit(resource, name_or_id, interactive=False):
    if not interactive and not name_or_id:
        cli.err_exit("Name or ID must be provided if not interactive.")
    if interactive and resource not in INTERACTIVE_SUPPORTED:
        cli.try_log(
            f"The interactive delete is not supported for '{resource}'"
        )
    if resource == lib.NOTIFICATION_TARGETS_RESOURCE:
        handle_edit_notif_tgt(name_or_id, interactive)
    else:
        cli.err_exit(f"The 'edit' command is not supported for '{resource}'")


def handle_edit_notif_tgt(name_or_id, interactive):
    ctx = cfg.get_current_context()
    notif_pol = api.get_notification_policy(*ctx.get_api_data())
    if interactive:
        nt.interactive_targets(notif_pol, "edit")
    else:
        targets = notif_pol[lib.TARGETS_FIELD]
        if name_or_id not in targets:
            cli.err_exit(f"No notification targets matching '{name_or_id}'.")
        tgt_yaml = yaml.dump({name_or_id: targets[name_or_id]})
        while True:
            edited_tgt = click.edit(tgt_yaml)
            if edited_tgt is None:
                break
            # TODO add validation
            break
        tgt_data = yaml.load(edited_tgt)
        if cli.query_yes_no(
            "Are you sure you want to update notification target"
            f" '{name_or_id}'?"
        ):
            cli.try_log(
                f"Successfully updated notification target '{name_or_id}'"
            )
