from typing import Optional
import spyctl.api as api
import spyctl.cli as cli
import spyctl.config.configs as cfg
import spyctl.spyctl_lib as lib
import spyctl.filter_resource as filt
import spyctl.resources.suppression_policies as s_pol


def handle_export(
    resource: str, name_or_id: Optional[str], exact: bool
) -> None:

    if name_or_id and not exact:
        name_or_id = name_or_id + "*" if name_or_id[-1] != "*" else name_or_id
        name_or_id = "*" + name_or_id if name_or_id[0] != "*" else name_or_id

    if resource == lib.SUPPRESSION_POLICY_RESOURCE:
        handle_export_suppression_policies(name_or_id)
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
