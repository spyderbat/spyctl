import spyctl.api as api
import spyctl.cli as cli
import spyctl.config.configs as cfgs
import spyctl.filter_resource as filt
import spyctl.resources.baselines as b
import spyctl.resources.policies as p
import spyctl.spyctl_lib as lib
from typing import IO, Dict, List, Optional, Union

POLICIES = None


def handle_merge(
    filename_target: List[IO],
    policy_target,
    with_file,
    with_policy,
    st,
    et,
    latest,
    output,
    output_fn=None,
):
    global POLICIES
    count = 0
    merge_actions = []
    if not POLICIES and (with_policy or policy_target):
        ctx = cfgs.get_current_context()
        POLICIES = api.get_policies(*ctx.get_api_data())
        if not POLICIES and policy_target:
            cli.err_exit("No policies to merge.")
        elif not POLICIES and with_policy:
            cli.err_exit("No policies to merge with.")
    if filename_target:
        for file in filename_target:
            target = load_target_file(file)
            with_obj = get_with_obj(
                target, with_file, with_policy, st, et, latest
            )
            # If we have something to merge, add to actions
            if with_obj:
                merge_actions.append((target, with_obj))
            else:
                cli.try_log(
                    f"{file.name} has nothing to merge with... skipping."
                )
    if policy_target:
        for pol_uid in policy_target:
            if pol_uid == "all":
                for target in POLICIES:
                    with_obj = get_with_obj(
                        target, with_file, with_policy, st, et, latest
                    )
                    # If we have something to merge, add to actions
                    if with_obj:
                        merge_actions.append((target, with_obj))
                    else:
                        cli.try_log(
                            f"{file.name} has nothing to merge with... skipping."
                        )
                    merge_resource(
                        policy,
                        with_file,
                        st,
                        et,
                        latest,
                        pager=True,
                        output_fn=o_fn,
                    )
            else:
                if output_fn and count > 1:
                    o_fn = unique_fn(output_fn, count)
                    count += 1
                else:
                    o_fn = output_fn
                    count += 1
                merge_resource(
                    policy,
                    with_file,
                    st,
                    et,
                    latest,
                    pager=True,
                    output_fn=o_fn,
                )


def get_with_obj(
    target, with_file, with_policy, st, et, latest
) -> Optional[Union[Dict, List[Dict]]]:
    if with_file:
        with_obj = load_with_file(with_file)
    elif with_policy:
        with_obj = get_with_policy(with_policy, POLICIES)
    else:
        with_obj = get_with_fingerprints(target, st, et, latest)
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


def get_with_fingerprints(target, st, et, latest) -> List[Dict]:
    pass


def get_with_policy(with_policy) -> Dict:
    pass


def merge_resource(target, with_obj):
    resrc_kind = target.get(lib.KIND_FIELD)
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
                    f"No {lib.LATEST_TIMESTAMP_FIELD} found in provided"
                    f" resource {lib.METADATA_FIELD} field. Defaulting to"
                    " 24hrs."
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
        result = b.merge_baseline(resource, with_resource, fingerprints)
    elif resrc_kind == lib.POL_KIND:
        result = p.merge_policy(resource, with_resource, fingerprints)
    else:
        cli.err_exit(f"The 'merge' command is not supported for {resrc_kind}")
    if result:
        cli.show(result.get_obj_data(), output)


def output_merge():
    pass


def apply_merge():
    pass


def unique_fn(fn: str, count: int) -> str:
    if "." in fn:
        parts = fn.split(".")
        parts[-2] = parts[-2] + f"_{count}"
        fn = ".".join(parts)
    else:
        fn = fn + f"_{count}"
    return fn
