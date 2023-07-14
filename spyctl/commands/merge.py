from typing import IO, Dict, List, Optional, Union

import spyctl.api as api
import spyctl.cli as cli
import spyctl.commands.apply as apply
import spyctl.commands.get as get
import spyctl.config.configs as cfgs
import spyctl.filter_resource as filt
import spyctl.merge_lib as m_lib
import spyctl.resources.baselines as b
import spyctl.resources.policies as p
import spyctl.resources.suppression_policies as sp
import spyctl.resources.api_filters.fingerprints as f_api_filt
import spyctl.spyctl_lib as lib
import spyctl.schemas as schemas
import spyctl.resources.resources_lib as r_lib

POLICIES = None
FINGERPRINTS = None
MATCHING = "matching"
ALL = "all"

YES_EXCEPT = False


def handle_merge(
    filename_target: List[IO],
    policy_target: List[str],
    with_file: IO,
    with_policy: str,
    st,
    et,
    latest: bool,
    output: str,
    output_to_file: bool = False,
    yes_except: bool = False,
    merge_network: bool = True,
):
    global POLICIES, YES_EXCEPT
    YES_EXCEPT = yes_except
    if not POLICIES and (with_policy or policy_target):
        ctx = cfgs.get_current_context()
        POLICIES = api.get_policies(*ctx.get_api_data())
        POLICIES.sort(key=lambda x: x[lib.METADATA_FIELD][lib.NAME_FIELD])
        if not POLICIES and policy_target:
            cli.err_exit("No policies to merge.")
        elif not POLICIES and with_policy:
            cli.err_exit("No policies to merge with.")
    if filename_target:
        if len(filename_target) > 1 or output_to_file:
            output_dest = lib.OUTPUT_DEST_FILE
        else:
            output_dest = lib.OUTPUT_DEFAULT
        filename_target.sort(key=lambda x: x.name)
        for file in filename_target:
            target = load_target_file(file)
            target_name = f"local file '{file.name}'"
            resrc_kind = target.get(lib.KIND_FIELD)
            if resrc_kind not in [lib.BASELINE_KIND, lib.POL_KIND]:
                cli.try_log(
                    f"The 'merge' command is not supported for {resrc_kind}",
                    is_warning=True,
                )
                continue
            with_obj = get_with_obj(
                target, target_name, with_file, with_policy, st, et, latest
            )
            # If we have something to merge, add to actions
            if with_obj:
                merged_obj = merge_resource(
                    target, target_name, with_obj, merge_network=merge_network
                )
                if merged_obj:
                    handle_output(output, output_dest, merged_obj)
            elif with_obj is False:
                continue
            else:
                cli.try_log(
                    f"{file.name} has nothing to merge with... skipping."
                )
    elif policy_target:
        if output_to_file:
            output_dest = lib.OUTPUT_DEST_FILE
        else:
            output_dest = lib.OUTPUT_DEST_API
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
                    output_dest,
                )
                # If we have something to merge, add to actions
                if with_obj:
                    merged_obj = merge_resource(
                        target,
                        target_name,
                        with_obj,
                        merge_network=merge_network,
                    )
                    if merged_obj:
                        handle_output(output, output_dest, merged_obj)
                elif with_obj is False:
                    continue
                else:
                    cli.try_log(
                        f"{t_uid} has nothing to merge with..." " skipping."
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
            if len(targets) > 0:
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
                    output_dest,
                )
                if with_obj:
                    merged_obj = merge_resource(
                        target,
                        target_name,
                        with_obj,
                        merge_network=merge_network,
                    )
                    if merged_obj:
                        handle_output(output, output_dest, merged_obj, pager)
                elif with_obj is False:
                    continue
                else:
                    cli.try_log(
                        f"{t_uid} has nothing to merge with..." " skipping."
                    )
    else:
        cli.err_exit("No target(s) to merge.")


def get_with_obj(
    target: Dict,
    target_name: str,
    with_file: IO,
    with_policy: str,
    st,
    et,
    latest,
    dest: str = "",
) -> Optional[Union[Dict, List[Dict], bool]]:
    global FINGERPRINTS
    target_uid = target.get(lib.METADATA_FIELD, {}).get(lib.METADATA_UID_FIELD)
    if dest == lib.OUTPUT_DEST_API:
        apply_disclaimer = (
            " (Note: you will have a chance to review any merge changes before"
            " applying them.)"
        )
    else:
        apply_disclaimer = ""
    if with_file:
        with_obj = load_with_file(with_file)
        if not cli.query_yes_no(
            f"Merge {target_name} with local file '{with_file.name}'?"
            f"{apply_disclaimer}"
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
                f"Merge {target_name} with data from applied policy "
                f"'{pol_name} - {pol_uid}'?{apply_disclaimer}"
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
                f"Merge {target_name} with data from applied policy"
                f" '{pol_name} - {pol_uid}'?{apply_disclaimer}"
            ):
                return False
    else:
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
            f"Merge {target_name} with relevant Fingerprints from"
            f" {lib.epoch_to_zulu(st)} to {lib.epoch_to_zulu(et)}?"
            f"{apply_disclaimer}"
        ):
            return False
        if FINGERPRINTS is None:
            with_obj = get_with_fingerprints(target, st, et, latest)
            cli.try_log(f"Filtering fingerprints for {target_name}")
            with_obj = filter_fingerprints(target, with_obj)
        else:
            cli.try_log(f"Filtering fingerprints for {target_name}")
            with_obj = filter_fingerprints(target, FINGERPRINTS)
    return with_obj


def load_target_file(target_file: IO) -> Dict:
    rv = lib.load_resource_file(target_file)
    return rv


def get_target_policy(target_uid) -> Optional[Dict]:
    rv = p.get_policy_by_uid(target_uid, POLICIES)
    return rv


def load_with_file(with_file: IO) -> Dict:
    rv = lib.load_resource_file(with_file)
    return rv


def get_with_fingerprints(target: Dict, st, et, latest) -> List[Dict]:
    global FINGERPRINTS
    ctx = cfgs.get_current_context()
    if latest:
        filters = lib.selectors_to_filters(target)
        muids = get.get_muids_scope(**filters)
        if muids:
            filters[lib.MACHINES_FIELD] = muids
        pipeline = f_api_filt.generate_pipeline(filters=filters)
        fingerprints = api.get_fingerprints(
            *ctx.get_api_data(),
            [ctx.global_source],
            time=(st, et),
            pipeline=pipeline,
        )
    else:
        fingerprints = api.get_fingerprints(
            *ctx.get_api_data(),
            [ctx.global_source],
            time=(st, et),
        )
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


def merge_resource(
    target: Dict,
    target_name: str,
    with_obj: Union[Dict, List[Dict]],
    src_cmd="merge",
    merge_network=True,
    ctx: cfgs.Context = None,
) -> Optional[m_lib.MergeObject]:
    if target == with_obj:
        cli.try_log(
            f"{src_cmd} target and with-object are the same.. skipping"
        )
        return None
    if not ctx:
        ctx = cfgs.get_current_context()
    merge_with_objects = []
    if isinstance(with_obj, Dict):
        merge_with_objects = r_lib.handle_input_data(with_obj, ctx)
    else:
        for obj in with_obj:
            merge_with_objects.extend(
                r_lib.handle_input_data(data=obj, ctx=ctx)
            )
    resrc_kind = target.get(lib.KIND_FIELD)
    merge_obj = get_merge_object(resrc_kind, target, merge_network, src_cmd)
    if isinstance(merge_with_objects, list):
        for w_obj in merge_with_objects:
            if is_type_mismatch(target, target_name, src_cmd, w_obj):
                continue
            try:
                merge_obj.asymmetric_merge(w_obj)
            except m_lib.InvalidMergeError as e:
                cli.try_log(
                    f"Unable to {src_cmd} with invalid object. {w_obj}",
                    *e.args,
                )
    else:
        raise Exception(
            f"Bug found, attempting to {src_cmd} with invalid object"
        )
    if target[lib.SPEC_FIELD] == merge_obj.get_obj_data().get(lib.SPEC_FIELD):
        cli.try_log(
            f"{src_cmd} of {target_name} produced no updates to the"
            f" '{lib.SPEC_FIELD}' field.. skipping"
        )
        if lib.API_CALL:
            return merge_obj
        return None
    return merge_obj


def get_merge_object(
    resrc_kind: str, target: Dict, merge_network: bool, src_cmd: str
):
    if resrc_kind == lib.BASELINE_KIND:
        merge_obj = m_lib.MergeObject(
            target,
            b.BASELINE_MERGE_SCHEMAS,
            schemas.valid_object,
            merge_network,
        )
    elif resrc_kind == lib.POL_KIND:
        resrc_type = target[lib.METADATA_FIELD][lib.METADATA_TYPE_FIELD]
        if resrc_type == lib.POL_TYPE_TRACE:
            merge_schemas = sp.T_S_POLICY_MERGE_SCHEMAS
        else:
            merge_schemas = p.POLICY_MERGE_SCHEMAS
        merge_obj = m_lib.MergeObject(
            target, merge_schemas, schemas.valid_object, merge_network
        )
    else:
        cli.try_log(
            f"The '{src_cmd}' command is not supported for {resrc_kind}",
            is_warning=True,
        )
    return merge_obj


def is_type_mismatch(
    target: Dict, target_name: str, src_cmd: str, with_obj: Dict
) -> bool:
    resrc_type = target[lib.METADATA_FIELD][lib.METADATA_TYPE_FIELD]
    with_type = with_obj[lib.METADATA_FIELD][lib.METADATA_TYPE_FIELD]
    with_kind = with_obj.get(lib.KIND_FIELD)
    if resrc_type != with_type:
        cli.try_log(
            f"Error type mismatch. Trying to {src_cmd} '{target_name}' of type"
            f" '{resrc_type}' with '{with_kind}' object of type '{with_type}'."
            " Skipping...",
            is_warning=True,
        )
        return True
    return False


def handle_output(
    output_format: str,
    output_dest: str,
    merge_obj: m_lib.MergeObject,
    pager=False,
):
    data = merge_obj.get_obj_data()
    if output_dest == lib.OUTPUT_DEST_API:
        apply_merge(merge_obj)
    elif output_dest == lib.OUTPUT_DEST_FILE:
        save_merge_to_file(merge_obj, output_format)
    else:
        if pager:
            cli.show(data, output_format, dest=lib.OUTPUT_DEST_PAGER)
        else:
            cli.show(data, output_format)


def apply_merge(merge_obj: m_lib.MergeObject):
    data = merge_obj.get_obj_data()
    pol_name = lib.get_metadata_name(data)
    pol_uid = data[lib.METADATA_FIELD][lib.METADATA_UID_FIELD]
    if (YES_EXCEPT or not cli.YES_OPTION) and cli.query_yes_no(
        f"Review merge updates to '{pol_name}-{pol_uid}'?",
        default="no",
        ignore_yes_option=YES_EXCEPT,
    ):
        cli.show(
            merge_obj.get_diff(), lib.OUTPUT_RAW, dest=lib.OUTPUT_DEST_PAGER
        )
    if not cli.query_yes_no(
        f"Apply merge changes to '{pol_name}-{pol_uid}'?",
        default=None,
        ignore_yes_option=YES_EXCEPT,
    ):
        return
    apply.handle_apply_policy(data)


def save_merge_to_file(merge_obj: m_lib.MergeObject, output_format):
    data = merge_obj.get_obj_data()
    pol_name = lib.get_metadata_name(data)
    pol_uid = data[lib.METADATA_FIELD].get(lib.METADATA_UID_FIELD)
    pol_str = f"{pol_name}-{pol_uid}" if pol_uid else pol_name
    if (YES_EXCEPT or not cli.YES_OPTION) and cli.query_yes_no(
        f"Review merge updates to '{pol_str}'?",
        default="no",
        ignore_yes_option=YES_EXCEPT,
    ):
        cli.show(
            merge_obj.get_diff(), lib.OUTPUT_RAW, dest=lib.OUTPUT_DEST_PAGER
        )
    if not cli.query_yes_no(
        f"Apply merge changes to '{pol_name}-{pol_uid}'?",
        default=None,
        ignore_yes_option=YES_EXCEPT,
    ):
        return
    out_fn = lib.find_resource_filename(data, "merge_output")
    out_fn = lib.unique_fn(out_fn, output_format)
    cli.show(data, output_format, dest=lib.OUTPUT_DEST_FILE, output_fn=out_fn)
