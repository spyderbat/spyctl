"""Handles the merge command for spyctl."""

import time
from typing import IO, Dict, List, Optional, Union

import click

import spyctl.config.configs as cfgs
import spyctl.filter_resource as filt
import spyctl.merge_lib as m_lib
import spyctl.resources.baselines as b
import spyctl.resources.deviations as dev
import spyctl.resources.policies as p
import spyctl.resources.resources_lib as r_lib
import spyctl.resources.suppression_policies as sp
import spyctl.schemas_v2 as schemas
import spyctl.spyctl_lib as lib
from spyctl import api, cli
from spyctl.commands import apply

POLICIES = None
FINGERPRINTS = None
DEVIATIONS = None
MATCHING = "matching"
ALL = "all"

YES_EXCEPT = False

# ----------------------------------------------------------------- #
#                         Merge Subcommand                          #
# ----------------------------------------------------------------- #


@click.command("merge", cls=lib.CustomCommand, epilog=lib.SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.option(
    "-f",
    "--filename",
    help="Target file(s) of the merge.",
    metavar="",
    type=lib.FileList(),
    cls=lib.MutuallyExclusiveEatAll,
    mutually_exclusive=["policy"],
)
@click.option(
    "-p",
    "--policy",
    is_flag=False,
    flag_value=ALL,
    default=None,
    help="Target policy name(s) or uid(s) of the merge. If supplied with no"
    " argument, set to 'all'.",
    metavar="",
    type=lib.ListParam(),
    cls=lib.MutuallyExclusiveOption,
    mutually_exclusive=["filename"],
)
@click.option(
    "-w",
    "--with-file",
    "with_file",
    help="File to merge into target.",
    metavar="",
    type=click.File(),
    cls=lib.MutuallyExclusiveOption,
    mutually_exclusive=["with_policy"],
)
@click.option(
    "-P",
    "--with-policy",
    "with_policy",
    help="Policy uid to merge with target. If supplied with no argument then"
    " spyctl will attempt to find a policy matching the uid in the"
    " target's metadata.",
    metavar="",
    is_flag=False,
    flag_value=MATCHING,
    cls=lib.MutuallyExclusiveOption,
    mutually_exclusive=["with_file"],
)
@click.option(
    "-l",
    "--latest",
    is_flag=True,
    help=f"Merge file with latest records using the value of"
    f" '{lib.LATEST_TIMESTAMP_FIELD}' in the target's '{lib.METADATA_FIELD}'."
    " This replaces --start-time.",
    metavar="",
)
@click.option(
    "-o",
    "--output",
    default=lib.OUTPUT_DEFAULT,
    type=click.Choice(lib.OUTPUT_CHOICES, case_sensitive=False),
)
@click.option(
    "-t",
    "--start-time",
    "st",
    help="Start time of the query for fingerprints to merge."
    " Only used if --latest, --with-file, and --with-policy are not set."
    " Default is 24 hours ago.",
    default="24h",
    type=lib.time_inp,
)
@click.option(
    "-e",
    "--end-time",
    "et",
    help="End time of the query for fingerprints to merge."
    " Only used if --with-file and --with-policy are not set."
    " Default is now.",
    default=time.time(),
    type=lib.time_inp,
)
@click.option(
    "-O",
    "--output-to-file",
    help="Should output merge to a file. Unique filename created from the name"
    " in the object's metadata.",
    is_flag=True,
)
@click.option(
    "--full-diff",
    is_flag=True,
    help="A diff summary is shown by default, set this flag to show the full"
    " object when viewing a diff following a merge. (All changes to the object"
    " are shown in the summary).",
)
@click.option(
    "-y",
    "--yes",
    "--assume-yes",
    is_flag=True,
    help='Automatic yes to prompts; assume "yes" as answer to all prompts and'
    " run non-interactively.",
    cls=lib.MutuallyExclusiveOption,
    mutually_exclusive=["yes_except"],
)
@click.option(
    "-Y",
    "--yes-except",
    "--assume-yes-except-review",
    is_flag=True,
    help='Automatic yes to merge prompts; assume "yes" as answer to all merge'
    " prompts but still prompts review of policy updates before applying.",
    cls=lib.MutuallyExclusiveOption,
    mutually_exclusive=["yes"],
)
@click.option(
    "--include-network/--exclude-network",
    help="Include or exclude network data in the merge."
    " Default is to include network data in the merge.",
    default=True,
)
@click.option(
    "-a",
    "--api",
    "use_api",
    metavar="",
    default=False,
    hidden=True,
    is_flag=True,
)
@lib.colorization_option
def merge(
    filename,
    policy,
    output,
    st,
    et,
    include_network,
    colorize,
    yes=False,
    yes_except=False,
    with_file=None,
    with_policy=None,
    latest=False,
    output_to_file=False,
    use_api=False,
    full_diff=False,
):
    """Merge target Baselines and Policies with other Resources.

      Merging in Spyctl requires a target Resource (e.g. a Baseline or Policy
    document you are maintaining) and a Resource to merge into the target.
    A target can either be a local file supplied using the -f option or a policy
    you've applied to the Spyderbat Backend supplied with the -p option.
    By default, target's are merged with deviations if they are applied policies,
    otherwise they are merged with relevant* Fingerprints from the last 24
    hours to now. Targets may also be merged with local files with the -w option
    or with data from an existing applied policy using the -P option.

      When merging a single local file with another resource, the output will
    be sent to stdout. WARNING: Do not redirect output to the same file you
    used as input. You may use the -O flag to output the merged data to a
    unique file with a name generate by Spyctl.

      When bulk merging local files, the output for each merge operation will
    be outputted to unique files generated by Spyctl (the same as supplying the
    -O flag mentioned above).

      When merging existing applied policies in bulk or individually, the default
    destination for the output will be to apply it directly to the Spyderbat Backend (you
    will have a chance to review the merge before any changes are applied).
    This removes the requirement to deal with local files when managing policies. However,
    it is a good idea to back up policies in a source-control repository. You can also
    use the -O operation to send the output of this merge to a local file.

    \b
    Examples:
      # merge a local policy file with data from the last
      # 24hrs to now:
      spyctl merge -f policy.yaml\n
    \b
      # merge a local policy file with data from its
      # latestTimestamp field to now:
      spyctl merge -f policy.yaml --latest\n
    \b
      # merge an existing applied policy with data from the
      # last 24hrs to now:
      spyctl merge -p <NAME_OR_UID>\n
    \b
      # Bulk merge all existing policies with data from the
      # last 24hrs to now:
      spyctl merge -p\n
    \b
      # Bulk merge multiple policies with data from the
      # last 24hrs to now:
      spyctl merge -p <NAME_OR_UID1>,<NAME_OR_UID2>\n
    \b
      # Bulk merge all files in cwd matching a pattern with data
      # from the last 24hrs to now:
      spyctl merge -f *.yaml\n
    \b
      # merge an existing applied policy with a local file:
      spyctl merge -p <NAME_OR_UID> --with-file fingerprints.yaml\n
    \b
      # merge a local file with data from an existing applied policy
      spyctl merge -f policy.yaml -P <NAME_OR_UID>\n
    \b
      # merge a local file with a valid UID in its metadata with the matching
      # policy in the Spyderbat Backend
      spyctl merge -f policy.yaml -P

    * Each policy has one or more Selectors in its spec field,
    relevant Fingerprints are those that match those Selectors.

    For time field options such as --start-time and --end-time you can
    use (m) for minutes, (h) for hours (d) for days, and (w) for weeks back
    from now or provide timestamps in epoch format.

    Note: Long time ranges or "get" commands in a context consisting of
    multiple machines can take a long time.
    """  # noqa E501
    if yes or yes_except:
        cli.set_yes_option()
    if not colorize:
        lib.disable_colorization()
    if output == lib.OUTPUT_DEFAULT:
        output = lib.OUTPUT_YAML
    handle_merge(
        filename,
        policy,
        with_file,
        with_policy,
        st,
        et,
        latest,
        output,
        output_to_file,
        yes_except,
        include_network,
        use_api,
        full_diff,
    )


# ----------------------------------------------------------------- #
#                         Merge Handlers                            #
# ----------------------------------------------------------------- #


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
    do_api=False,
    full_diff=False,
):
    if do_api:
        ctx = cfgs.get_current_context()
        if not filename_target or not with_file:
            cli.err_exit("api test only with local files")
        r_data = lib.load_file_for_api_test(filename_target[0])
        w_data = lib.load_file_for_api_test(with_file)
        merged_data = api.api_merge(*ctx.get_api_data(), r_data, w_data)
        cli.show(merged_data, lib.OUTPUT_RAW)
        return
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
                target,
                target_name,
                with_file,
                with_policy,
                st,
                et,
                latest,
            )
            # If we have something to merge, add to actions
            if with_obj:
                merged_obj = merge_resource(
                    target, target_name, with_obj, merge_network=merge_network
                )
                if merged_obj:
                    handle_output(
                        output, output_dest, merged_obj, full_diff=full_diff
                    )
            elif with_obj is False:
                continue
            else:
                merge_obj = __nothing_to_merge_with(
                    target_name, target, latest
                )
                if merge_obj:
                    handle_output(
                        output, output_dest, merge_obj, full_diff=full_diff
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
                        handle_output(
                            output,
                            output_dest,
                            merged_obj,
                            full_diff=full_diff,
                        )
                elif with_obj is False:
                    continue
                else:
                    merge_obj = __nothing_to_merge_with(
                        target_name, target, latest
                    )
                    if merge_obj:
                        handle_output(
                            output, output_dest, merge_obj, full_diff=full_diff
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
                        handle_output(
                            output,
                            output_dest,
                            merged_obj,
                            pager,
                            full_diff=full_diff,
                        )
                elif with_obj is False:
                    continue
                else:
                    merge_obj = __nothing_to_merge_with(
                        target_name, target, latest
                    )
                    if merge_obj:
                        handle_output(
                            output,
                            output_dest,
                            merge_obj,
                            pager,
                            full_diff=full_diff,
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
            st = get_latest_timestamp(target)
        if not cli.query_yes_no(
            f"Merge {target_name} with Deviations from"
            f" {lib.epoch_to_zulu(st)} to {lib.epoch_to_zulu(et)}?"
            f"{apply_disclaimer}"
        ):
            return False
        uid = target[lib.METADATA_FIELD][lib.METADATA_UID_FIELD]
        with_obj = get_with_deviations(uid, st, et)
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


def get_latest_timestamp(target: Dict) -> float:
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
    return st


def get_with_deviations(uid: str, st, et) -> List[Dict]:
    deviations = dev.get_unique_deviations(uid, st, et)
    return deviations


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
    latest=False,
    check_irrelevant=False,
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
                merge_obj.asymmetric_merge(w_obj, check_irrelevant)
            except m_lib.InvalidMergeError as e:
                cli.try_log(
                    f"Unable to {src_cmd} with invalid object. {w_obj}",
                    *e.args,
                )
    else:
        raise ValueError(
            f"Bug found, attempting to {src_cmd} with invalid object"
        )
    if target[lib.SPEC_FIELD] == merge_obj.get_obj_data().get(lib.SPEC_FIELD):
        if latest and src_cmd == "merge":
            cli.try_log(
                f"{src_cmd} of {target_name} produced no updates to the"
                f" '{lib.SPEC_FIELD}'.. updating {lib.LATEST_TIMESTAMP_FIELD}"
                " field to now."
            )
            merge_obj.update_latest_timestamp()
            return merge_obj
        else:
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
    target_kind = target.get(lib.KIND_FIELD)
    if target_kind == lib.POL_KIND and with_kind == lib.DEVIATION_KIND:
        pol_uid = target[lib.METADATA_FIELD].get(lib.METADATA_UID_FIELD)
        dev_pol_uid = with_obj[lib.METADATA_FIELD]["policy_uid"]
        if pol_uid != dev_pol_uid:
            cli.try_log(
                f"Error uid mismatch. Trying to {src_cmd} '{target_name}' of"
                f" type '{resrc_type}' with '{with_kind}' but the policy uids"
                " do not match. Skipping...",
                is_warning=True,
            )
            return True
        return False
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
    full_diff=False,
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


def apply_merge(merge_obj: m_lib.MergeObject, full_diff=False):
    data = merge_obj.get_obj_data()
    pol_name = lib.get_metadata_name(data)
    pol_uid = data[lib.METADATA_FIELD][lib.METADATA_UID_FIELD]
    if (YES_EXCEPT or not cli.YES_OPTION) and cli.query_yes_no(
        f"Review merge updates to '{pol_name}-{pol_uid}'?",
        default="no",
        ignore_yes_option=YES_EXCEPT,
    ):
        cli.show(
            merge_obj.get_diff(full_diff),
            lib.OUTPUT_RAW,
            dest=lib.OUTPUT_DEST_PAGER,
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


def __nothing_to_merge_with(
    name: str, target, latest, src_cmd="merge"
) -> Optional[m_lib.MergeObject]:
    if latest:
        cli.try_log(
            f"{name.capitalize()} has nothing to {src_cmd} with. Updating"
            f" '{lib.LATEST_TIMESTAMP_FIELD}' field."
        )
        merge_object = get_merge_object(
            target[lib.KIND_FIELD], target, True, src_cmd
        )
        merge_object.update_latest_timestamp()
        return merge_object
    else:
        cli.try_log(
            f"{name.capitalize()} has nothing to {src_cmd} with... skipping."
        )
