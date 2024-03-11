"""Handles the 'diff' subcommand for spyctl."""

import time
from typing import IO, Dict, List, Optional, Union

import click

import spyctl.commands.merge as merge_cmd
import spyctl.config.configs as cfgs
import spyctl.filter_resource as filt
import spyctl.merge_lib as m_lib
import spyctl.resources.policies as p
import spyctl.spyctl_lib as lib
from spyctl import api, cli

# ----------------------------------------------------------------- #
#                          Diff Subcommand                          #
# ----------------------------------------------------------------- #


@click.command("diff", cls=lib.CustomCommand, epilog=lib.SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.option(
    "-f",
    "--filename",
    help="Target file(s) of the diff.",
    metavar="",
    type=lib.FileList(),
    cls=lib.MutuallyExclusiveEatAll,
    mutually_exclusive=["policy"],
)
@click.option(
    "-p",
    "--policy",
    is_flag=False,
    flag_value="all",
    default=None,
    help="Target policy name(s) or uid(s) of the diff. If supplied with no"
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
    help="File to diff with target.",
    metavar="",
    type=click.File(),
    cls=lib.MutuallyExclusiveOption,
    mutually_exclusive=["with_policy"],
)
@click.option(
    "-P",
    "--with-policy",
    "with_policy",
    help="Policy uid to diff with target. If supplied with no argument then"
    " spyctl will attempt to find a policy matching the uid in the target's"
    " metadata.",
    metavar="",
    is_flag=False,
    flag_value="matching",
    cls=lib.MutuallyExclusiveOption,
    mutually_exclusive=["with_file"],
)
@click.option(
    "-l",
    "--latest",
    is_flag=True,
    help=f"Diff target with latest records using the value of"
    f" '{lib.LATEST_TIMESTAMP_FIELD}' in '{lib.METADATA_FIELD}'."
    " This replaces --start-time.",
    metavar="",
)
@click.option(
    "-t",
    "--start-time",
    "st",
    help="Start time of the query for fingerprints to diff."
    " Only used if --latest, --with-file, --with-policy are not set."
    " Default is 24 hours ago.",
    default="24h",
    type=lib.time_inp,
)
@click.option(
    "-e",
    "--end-time",
    "et",
    help="End time of the query for fingerprints to diff."
    " Only used if --with-file, and --with-policy are not set."
    " Default is now.",
    default=time.time(),
    type=lib.time_inp,
)
@click.option(
    "--full-diff",
    is_flag=True,
    help="A diff summary is shown by default, set this flag to show the full"
    " object when viewing a diff. (All changes to the object"
    " are shown in the summary).",
)
@click.option(
    "-o",
    "--output",
    default=lib.OUTPUT_DEFAULT,
    type=click.Choice(lib.OUTPUT_CHOICES, case_sensitive=False),
)
@click.option(
    "-y",
    "--yes",
    "--assume-yes",
    is_flag=True,
    help='Automatic yes to prompts; assume "yes" as answer to all prompts and'
    " run non-interactively.",
)
@click.option(
    "--include-network/--exclude-network",
    help="Include or exclude network data in the diff."
    " Default is to include network data in the diff.",
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
def diff(
    filename,
    policy,
    st,
    et,
    include_network,
    colorize,
    output,
    yes=False,
    with_file=None,
    with_policy=None,
    latest=False,
    use_api=False,
    full_diff=False,
):
    """Diff target Baselines and Policies with other Resources.

      Diff'ing in Spyctl requires a target Resource (e.g. a Baseline or Policy
    document you are maintaining) and a Resource to diff with the target.
    A target can be either a local file supplied using the -f option or a policy
    you've applied to the Spyderbat Backend supplied with the -p option.
    By default, target's are diff'd with deviations if they are applied policies,
    otherwise they are diff'd with relevant* Fingerprints from the last 24
    hours to now. Targets may also be diff'd with local files with the -w option
    or with data from an existing applied policy using the -P option.

      The output of a diff shows you any lines that would be added to or removed
    from your target Resource as a result of a Merge. diffs may also be performed
    in bulk. Bulk diffs are outputted to a pager like 'less' or 'more'.

      To maintain a target Resource effectively, the goal should be to get to
    get to a point where the diff no longer displays added or removed lines (other
    than timestamps).

    \b
    Examples:
      # diff a local policy file with data from the last
      # 24hrs to now:
      spyctl diff -f policy.yaml\n
    \b
      # diff a local policy file with data from its
      # latestTimestamp field to now:
      spyctl diff -f policy.yaml --latest\n
    \b
      # diff an existing applied policy with data from the
      # last 24hrs to now:
      spyctl diff -p <NAME_OR_UID>\n
    \b
      # Bulk diff all existing policies with data from the
      # last 24hrs to now:
      spyctl diff -p\n
    \b
      # Bulk diff multiple policies with data from the
      # last 24hrs to now:
      spyctl diff -p <NAME_OR_UID1>,<NAME_OR_UID2>\n
    \b
      # Bulk diff all files in cwd matching a pattern with relevant*
      # Fingerprints from the last 24hrs to now:
      spyctl diff -f *.yaml\n
    \b
      # diff an existing applied policy with a local file:
      spyctl diff -p <NAME_OR_UID> --with-file fingerprints.yaml\n
    \b
      # diff a local file with data from an existing applied policy
      spyctl diff -f policy.yaml -P <NAME_OR_UID>\n
    \b
      # diff a local file with a valid UID in its metadata with the matching
      # policy in the Spyderbat Backend
      spyctl diff -f policy.yaml -P

    * Each policy has one or more Selectors in its spec field,
    relevant Fingerprints are those that match those Selectors.

    For time field options such as --start-time and --end-time you can
    use (m) for minutes, (h) for hours (d) for days, and (w) for weeks back
    from now or provide timestamps in epoch format.

    Note: Long time ranges or "get" commands in a context consisting of
    multiple machines can take a long time.
    """  # noqa E501
    if yes:
        cli.set_yes_option()
    if not colorize:
        lib.disable_colorization()
    handle_diff(
        filename,
        policy,
        with_file,
        with_policy,
        st,
        et,
        latest,
        include_network,
        use_api,
        full_diff,
        output,
    )


# ----------------------------------------------------------------- #
#                          Diff Handlers                            #
# ----------------------------------------------------------------- #

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
                __nothing_to_diff_with(target_name, target, latest)
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
                    __nothing_to_diff_with(target_name, target, latest)
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
                    __nothing_to_diff_with(target_name, target, latest)
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
        if latest:
            st = merge_cmd.get_latest_timestamp(target)
        if not cli.query_yes_no(
            f"Diff {target_name} with Deviations from"
            f" {lib.epoch_to_zulu(st)} to {lib.epoch_to_zulu(et)}?"
        ):
            return False
        uid = target[lib.METADATA_FIELD].get(lib.METADATA_UID_FIELD)
        if not uid:
            cli.err_exit(
                f"Target {target_name} has not been applied, no deviations to diff with"  # noqa
            )
        with_obj = merge_cmd.get_with_deviations(uid, st, et)
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
    cli.try_log(
        f"{name.capitalize()} has nothing to {src_cmd} with... skipping."
    )
