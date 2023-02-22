from typing import Dict

import spyctl.api as api
import spyctl.cli as cli
import spyctl.config.configs as cfgs
import spyctl.filter_resource as filt
import spyctl.resources.baselines as spyctl_baselines
import spyctl.resources.policies as p
import spyctl.spyctl_lib as lib


def handle_diff(
    filename_target, policy_target, with_file, with_policy, st, et, latest
):
    pager = False
    if filename_target and policy_target:
        pager = True
    if filename_target:
        if len(filename_target) > 1:
            pager = True
        for filename in filename_target:
            resource = lib.load_resource_file(filename)
            diff_resource(resource, with_file, st, et, latest, pager=pager)
    if policy_target:
        ctx = cfgs.get_current_context()
        policies = api.get_policies(*ctx.get_api_data())
        if not policies:
            cli.err_exit("No policies to diff.")
        if len(policy_target) > 1:
            pager = True
        for pol_uid in policy_target:
            if pol_uid == "all":
                for policy in policies:
                    diff_resource(
                        policy, with_file, st, et, latest, pager=True
                    )
            else:
                policy = p.get_policy_by_uid(pol_uid, policies)
                if not policy:
                    cli.err_exit(f"Unable to find policy with UID {pol_uid}")
                resource = policy
                diff_resource(resource, with_file, st, et, latest, pager=pager)
    else:
        cli.err_exit("No target of the diff.")


def diff_resource(resource: Dict, with_file, st, et, latest, pager=False):
    resrc_kind = resource.get(lib.KIND_FIELD)
    fingerprints = None
    with_resource = None
    if not with_file:
        if latest:
            latest_timestamp = resource.get(lib.METADATA_FIELD, {}).get(
                lib.LATEST_TIMESTAMP_FIELD
            )
            if latest_timestamp is not None:
                st = lib.time_inp(latest_timestamp)
            else:
                cli.err_exit(
                    f"No '{lib.LATEST_TIMESTAMP_FIELD}' found in provided"
                    f" resource '{lib.METADATA_FIELD}' field."
                )
        filters = lib.selectors_to_filters(resource)
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
    else:
        with_resource = lib.load_resource_file(with_file)
    if resrc_kind == lib.BASELINE_KIND:
        out_diff = spyctl_baselines.diff_baseline(
            resource, with_resource, fingerprints
        )
    elif resrc_kind == lib.POL_KIND:
        out_diff = p.diff_policy(resource, with_resource, fingerprints)
    else:
        cli.err_exit(f"The 'diff' command is not supported for {resrc_kind}")
    cli.show(out_diff, lib.OUTPUT_RAW, pager=pager)
