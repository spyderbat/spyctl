from typing import IO, Dict, List, Optional, Union

import spyctl.api as api
import spyctl.cli as cli
import spyctl.config.configs as cfgs
import spyctl.filter_resource as filt
import spyctl.resources.policies as p
import spyctl.spyctl_lib as lib
import spyctl.commands.merge as merge_cmd

POLICIES = None
MATCHING = "matching"
ALL = "all"
LOADED_RESOURCE = None


def handle_diff(
    filename_target: List[IO],
    policy_target: List[str],
    with_file: IO,
    with_policy: str,
    st,
    et,
    latest,
):
    global POLICIES
    if not POLICIES and (with_policy or policy_target):
        ctx = cfgs.get_current_context()
        POLICIES = api.get_policies(*ctx.get_api_data())
        POLICIES.sort(key=lambda x: x[lib.METADATA_FIELD][lib.NAME_FIELD])
        if not POLICIES and policy_target:
            cli.err_exit("No policies to diff.")
        elif not POLICIES and with_policy:
            cli.err_exit("No policies to diff with.")
    if filename_target:
        pager = True if len(filename_target) > 1 else False
        filename_target.sort(key=lambda x: x.name)
        for file in filename_target:
            target = load_target_file(file)
            target_name = f"local file '{file.name}'"
            resrc_kind = target.get(lib.KIND_FIELD)
            if resrc_kind not in [lib.BASELINE_KIND, lib.POL_KIND]:
                cli.try_log(
                    f"The 'diff' command is not supported for {resrc_kind}",
                    is_warning=True,
                )
                continue
            with_obj = get_with_obj(
                target, target_name, with_file, with_policy, st, et, latest
            )
            if with_obj:
                diff_resource(target, with_obj, pager)
            elif with_obj is False:
                continue
            else:
                cli.try_log(
                    f"{file.name} has nothing to diff with... skipping."
                )
    elif policy_target:
        pager = (
            True
            if len(policy_target) > 1
            or (ALL in policy_target and len(POLICIES) > 1)
            else False
        )
        policy_target = sorted(policy_target)
        if ALL in policy_target:
            for target in POLICIES:
                t_name = lib.get_metadata_name(target)
                t_uid = target[lib.METADATA_FIELD][lib.METADATA_UID_FIELD]
                target_name = f"applied policy '{t_name} - {t_uid}'"
                target_uid = target[lib.METADATA_FIELD][lib.METADATA_UID_FIELD]
                with_obj = get_with_obj(
                    target,
                    target_name,
                    with_file,
                    with_policy,
                    st,
                    et,
                    latest,
                )
                if with_obj:
                    diff_resource(target, with_obj, pager)
                elif with_obj is False:
                    continue
                else:
                    cli.try_log(
                        f"{target_uid} has nothing to diff with..."
                        " skipping."
                    )
        else:
            targets = {}
            for pol_name_or_uid in policy_target:
                policies = filt.filter_obj(
                    POLICIES,
                    [
                        [lib.METADATA_FIELD, lib.NAME_FIELD],
                        [lib.METADATA_FIELD, lib.METADATA_UID_FIELD],
                    ],
                    pol_name_or_uid,
                )
                if len(policies) == 0:
                    cli.try_log(
                        "Unable to locate policy with name or UID"
                        f" {pol_name_or_uid}",
                        is_warning=True,
                    )
                    continue
                for policy in policies:
                    pol_uid = policy[lib.METADATA_FIELD][
                        lib.METADATA_UID_FIELD
                    ]
                    targets[pol_uid] = policy
            targets = sorted(
                list(targets.values()),
                key=lambda x: x[lib.METADATA_FIELD][lib.METADATA_NAME_FIELD],
            )
            if len(targets) > 1:
                pager = True
            for target in targets:
                t_name = lib.get_metadata_name(target)
                t_uid = target.get(lib.METADATA_FIELD, {}).get(
                    lib.METADATA_UID_FIELD
                )
                target_name = f"applied policy '{t_name} - {t_uid}'"
                with_obj = get_with_obj(
                    target,
                    target_name,
                    with_file,
                    with_policy,
                    st,
                    et,
                    latest,
                )
                if with_obj:
                    diff_resource(target, with_obj, pager)
                elif with_obj is False:
                    continue
                else:
                    cli.try_log(
                        f"{target_uid} has nothing to diff with..."
                        " skipping."
                    )
    else:
        cli.err_exit("No target of the diff.")


def get_with_obj(
    target: Dict, target_name, with_file: IO, with_policy: str, st, et, latest
) -> Optional[Union[Dict, List[Dict]]]:
    target_uid = target.get(lib.METADATA_FIELD, {}).get(lib.METADATA_UID_FIELD)
    if with_file:
        with_obj = load_with_file(with_file)
        if not cli.query_yes_no(
            f"diff {target_name} with '{with_file.name}'?"
        ):
            return False
    elif with_policy == MATCHING:
        if not target_uid:
            cli.try_log(
                f"{target_name} has no uid, unable to match with"
                " policy stored in the Spyderbat backend.",
                is_warning=True,
            )
            return False
        with_obj = get_with_policy(target_uid, POLICIES)
        if with_obj:
            pol_name = lib.get_metadata_name(with_obj)
            pol_uid = with_obj.get(lib.METADATA_FIELD, {}).get(
                lib.METADATA_UID_FIELD
            )
            if not cli.query_yes_no(
                f"diff {target_name} with data from applied policy"
                f" '{pol_name} - {pol_uid}'?"
            ):
                return False
    elif with_policy:
        with_obj = get_with_policy(with_policy, POLICIES)
        if with_obj:
            pol_name = lib.get_metadata_name(with_obj)
            pol_uid = with_obj.get(lib.METADATA_FIELD, {}).get(
                lib.METADATA_UID_FIELD
            )
            if not cli.query_yes_no(
                f"diff {target_name} with data from applied policy"
                f" '{pol_name} - {pol_uid}'?"
            ):
                return False
    else:
        if not cli.query_yes_no(
            f"diff {target_name} with relevant Fingerprints from"
            f" {lib.epoch_to_zulu(st)} to {lib.epoch_to_zulu(et)}?"
        ):
            return False
        with_obj = get_with_fingerprints(target, st, et, latest)
    return with_obj


def load_target_file(target_file: IO) -> Dict:
    rv = lib.load_resource_file(target_file)
    return rv


def get_target_policy(target_uid) -> Optional[Dict]:
    rv = p.get_policy_by_uid(target_uid, POLICIES)
    filt.filter_policies()
    return rv


def load_with_file(with_file: IO) -> Dict:
    rv = lib.load_resource_file(with_file)
    return rv


def get_with_fingerprints(target: Dict, st, et, latest: bool) -> List[Dict]:
    if latest:
        latest_timestamp = target.get(lib.METADATA_FIELD, {}).get(
            lib.LATEST_TIMESTAMP_FIELD
        )
        if latest_timestamp is not None:
            st = lib.time_inp(latest_timestamp)
        else:
            cli.err_exit(
                f"No {lib.LATEST_TIMESTAMP_FIELD} found in provided"
                f" resource {lib.METADATA_FIELD} field. Defaulting to"
                " 24hrs."
            )
    filters = lib.selectors_to_filters(target)
    ctx = cfgs.get_current_context()
    machines = api.get_machines(*ctx.get_api_data())
    machines = filt.filter_machines(
        machines, filters, use_context_filters=False
    )
    muids = [m["uid"] for m in machines]
    fingerprints = api.get_fingerprints(
        *ctx.get_api_data(),
        muids=muids,
        time=(st, et),
    )
    fingerprints = filt.filter_fingerprints(
        fingerprints, **filters, use_context_filters=False
    )
    return fingerprints


def get_with_policy(pol_uid: str, policies: List[Dict]) -> Dict:
    return p.get_policy_by_uid(pol_uid, policies)


def diff_resource(
    target: Dict, with_obj: Union[Dict, List[Dict]], pager=False
):
    merged_obj = merge_cmd.merge_resource(target, with_obj, "diff")
    if merged_obj:
        diff_data = merged_obj.get_diff()
        if pager:
            cli.show(diff_data, lib.OUTPUT_RAW, dest=lib.OUTPUT_DEST_PAGER)
        else:
            cli.show(diff_data, lib.OUTPUT_RAW)
