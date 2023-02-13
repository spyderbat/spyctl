import spyctl.api as api
import spyctl.cli as cli
import spyctl.config.configs as cfgs
import spyctl.filter_resource as filt
import spyctl.resources.baselines as spyctl_baselines
import spyctl.resources.policies as spyctl_policies
import spyctl.spyctl_lib as lib


def handle_diff(filename, with_file, st, et, latest):
    resource = lib.load_resource_file(filename)
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
        spyctl_baselines.diff_baseline(resource, with_resource, fingerprints)
    elif resrc_kind == lib.POL_KIND:
        spyctl_policies.diff_policy(resource, with_resource, fingerprints)
    else:
        cli.err_exit(f"The 'diff' command is not supported for {resrc_kind}")
