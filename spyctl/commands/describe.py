from typing import IO, Dict

import spyctl.api as api
import spyctl.cli as cli
import spyctl.config.configs as cfg
import spyctl.filter_resource as filt
import spyctl.spyctl_lib as lib


def handle_describe(resource: str, name_or_uid: str, file: IO = None):
    if resource == lib.POLICIES_RESOURCE:
        handle_describe_policy()


def handle_describe_policy(name_or_uid, file: IO = None):
    if not name_or_uid and not file:
        cli.err_exit("No file or name_or_uid provided")
    if not file:
        policy = get_policy_by_name_or_uid
    else:
        policy = get_policy_from_file(name_or_uid, file)
    pol_name = policy[lib.METADATA_FIELD][lib.METADATA_NAME_FIELD]
    cli.try_log(f"Describing policy '{pol_name}'")


def get_policy_from_file(name_or_uid: str, file: IO) -> Dict:
    resource = lib.load_resource_file(file)
    kind = resource[lib.KIND_FIELD]
    if kind != lib.POL_KIND:
        cli.err_exit(f"File kind '{kind}' is not '{lib.POL_KIND}'")
    if name_or_uid:
        policies = filt.filter_obj(
            [resource],
            [
                [lib.METADATA_FIELD, lib.METADATA_NAME_FIELD],
                [lib.METADATA_FIELD, lib.METADATA_UID_FIELD],
            ],
            name_or_uid,
        )
        if len(policies) == 0:
            cli.err_exit(f"No policies matching name_or_uid '{name_or_uid}'")
        return policies[0]
    return resource


def get_policy_by_name_or_uid(name_or_uid) -> Dict:
    ctx = cfg.get_current_context()
    policies = api.get_policies(*ctx.get_api_data())
    policies = filt.filter_obj(
        policies,
        [
            [lib.METADATA_FIELD, lib.METADATA_NAME_FIELD],
            [lib.METADATA_FIELD, lib.METADATA_UID_FIELD],
        ],
        name_or_uid,
    )
    if len(policies) == 0:
        cli.err_exit(f"No policies matching name_or_uid '{name_or_uid}'")
    if len(policies) > 1:
        cli.err_exit("Name or uid of policy is ambiguous")
    return policies[0]
