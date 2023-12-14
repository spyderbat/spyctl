from typing import IO, Dict, List, Optional, Union

import spyctl.api as api
import spyctl.cli as cli
import spyctl.config.configs as cfgs
import spyctl.filter_resource as filt
import spyctl.resources.policies as p
import spyctl.spyctl_lib as lib
import spyctl.commands.merge as merge_cmd
import spyctl.merge_lib as m_lib

POLICIES = None
FINGERPRINTS = None
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
    merge_network=True,
    do_api=False,
    force_fprints=False,
    full_diff=False,
    output=lib.OUTPUT_DEFAULT,
):
    if do_api:
        ctx = cfgs.get_current_context()
        if not filename_target or not with_file:
            cli.err_exit("api test only with local files")
        r_data = lib.load_file_for_api_test(filename_target[0])
        w_data = lib.load_file_for_api_test(with_file)
        diff_data = api.api_diff(*ctx.get_api_data(), r_data, w_data)
        cli.show(diff_data, lib.OUTPUT_RAW)
        return
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
                target,
                target_name,
                with_file,
                with_policy,
                st,
                et,
                latest,
                force_fprints,
            )
            if with_obj:
                diff_resource(
                    target,
                    target_name,
                    with_obj,
                    pager,
                    merge_network,
                    full_diff=full_diff,
                    output=output,
                )
            elif with_obj is False:
                continue
            else:
                cli.try_log(
                    f"{file.name} has nothing to diff with... skipping."
                )
                merge_obj = __nothing_to_diff_with(target_name, target, latest)
                if merge_obj:
                    handle_output(merge_obj, pager, full_diff=full_diff)
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
                with_obj = get_with_obj(
                    target,
                    target_name,
                    with_file,
                    with_policy,
                    st,
                    et,
                    latest,
                    force_fprints,
                )
                if with_obj:
                    diff_resource(
                        target,
                        target_name,
                        with_obj,
                        pager,
                        merge_network,
                        full_diff=full_diff,
                        output=output,
                    )
                elif with_obj is False:
                    continue
                else:
                    merge_obj = __nothing_to_diff_with(
                        target_name, target, latest
                    )
                    if merge_obj:
                        handle_output(merge_obj, pager, full_diff=full_diff)
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
                    force_fprints,
                )
                if with_obj:
                    diff_resource(
                        target,
                        target_name,
                        with_obj,
                        pager,
                        merge_network,
                        full_diff=full_diff,
                        output=output,
                    )
                elif with_obj is False:
                    continue
                else:
                    merge_obj = __nothing_to_diff_with(
                        target_name, target, latest
                    )
                    if merge_obj:
                        handle_output(merge_obj, pager, full_diff=full_diff)
    else:
        cli.err_exit("No target of the diff.")


def get_with_obj(
    target: Dict,
    target_name,
    with_file: IO,
    with_policy: str,
    st,
    et,
    latest,
    with_fingerprints=False,
) -> Optional[Union[Dict, List[Dict]]]:
    global FINGERPRINTS
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
    elif with_fingerprints or not target.get(lib.METADATA_FIELD, {}).get(
        lib.METADATA_UID_FIELD
    ):
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
            if FINGERPRINTS is not None:
                cli.try_log("--latest flag set, re-downloading fingerprints..")
                FINGERPRINTS = None
        if not cli.query_yes_no(
            f"diff {target_name} with relevant Fingerprints from"
            f" {lib.epoch_to_zulu(st)} to {lib.epoch_to_zulu(et)}?"
        ):
            return False
        if FINGERPRINTS is None:
            with_obj = get_with_fingerprints(target, st, et, latest)
            cli.try_log(f"Filtering fingerprints for {target_name}")
            with_obj = filter_fingerprints(target, with_obj)
        else:
            cli.try_log(f"Filtering fingerprints for {target_name}")
            with_obj = filter_fingerprints(target, FINGERPRINTS)
    else:
        if latest:
            st = merge_cmd.get_latest_timestamp(target)
        if not cli.query_yes_no(
            f"Diff {target_name} with Deviations from"
            f" {lib.epoch_to_zulu(st)} to {lib.epoch_to_zulu(et)}?"
        ):
            return False
        uid = target[lib.METADATA_FIELD][lib.METADATA_UID_FIELD]
        with_obj = merge_cmd.get_with_deviations(uid, st, et)
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


def get_with_fingerprints(target: Dict, st, et, latest) -> List[Dict]:
    global FINGERPRINTS
    fingerprints = merge_cmd.get_with_fingerprints(target, st, et, latest)
    FINGERPRINTS = fingerprints
    return fingerprints


def filter_fingerprints(target, fingerprints) -> List[Dict]:
    filters = lib.selectors_to_filters(target)
    rv = filt.filter_fingerprints(
        fingerprints, **filters, use_context_filters=False
    )
    return rv


def get_with_policy(pol_uid: str, policies: List[Dict]) -> Dict:
    return p.get_policy_by_uid(pol_uid, policies)


def diff_resource(
    target: Dict,
    target_name,
    with_obj: Union[Dict, List[Dict]],
    pager=False,
    merge_network=True,
    full_diff=False,
    output=lib.OUTPUT_DEFAULT,
):
    merged_obj = merge_cmd.merge_resource(
        target, target_name, with_obj, "diff", merge_network
    )
    if merged_obj:
        handle_output(merged_obj, pager, full_diff, output)


def handle_output(
    merged_obj: m_lib.MergeObject,
    pager=False,
    full_diff=False,
    output=lib.OUTPUT_DEFAULT,
):
    if output == lib.OUTPUT_DEFAULT:
        output = lib.OUTPUT_RAW
        diff_object = False
    else:
        diff_object = True
    diff_data = merged_obj.get_diff(full_diff, diff_object)
    if pager:
        cli.show(diff_data, output, dest=lib.OUTPUT_DEST_PAGER)
    else:
        cli.show(diff_data, output)


def __nothing_to_diff_with(
    name: str, target, latest, src_cmd="diff"
) -> Optional[m_lib.MergeObject]:
    if latest:
        cli.try_log(
            f"{name.capitalize()} has nothing to {src_cmd} with. Would"
            f" update '{lib.LATEST_TIMESTAMP_FIELD}' field on merge."
        )
        return
        merge_object = merge_cmd.get_merge_object(
            target[lib.KIND_FIELD], target, True, src_cmd
        )
        merge_object.update_latest_timestamp()
        return merge_object
    else:
        cli.try_log(
            f"{name.capitalize()} has nothing to {src_cmd} with... skipping."
        )
