import spyctl.api as api
import spyctl.cli as cli
import spyctl.config.configs as cfg
import spyctl.spyctl_lib as lib
import spyctl.filter_resource as filt


def handle_delete(resource, name_or_id):
    if resource == lib.POLICIES_RESOURCE:
        handle_delete_policy(name_or_id)
    elif resource == lib.SUPPRESSION_POLICY_RESOURCE:
        handle_delete_suppression_policy(name_or_id)
    else:
        cli.err_exit(f"The 'delete' command is not supported for {resource}")


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
