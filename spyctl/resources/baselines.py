from typing import Dict

import yaml
import time

import spyctl.cli as cli
import spyctl.resources.fingerprints as spyctl_fprints
import spyctl.spyctl_lib as lib
import spyctl.subcommands.merge as merge
import spyctl.api as api
import spyctl.config.configs as cfgs
import spyctl.filter_resource as filt

FPRINT_KIND = spyctl_fprints.FPRINT_KIND
GROUP_KIND = spyctl_fprints.GROUP_KIND
BASELINE_KIND = lib.BASELINE_KIND


class InvalidBaselineError(Exception):
    pass


class Baseline:
    valid_obj_kinds = {GROUP_KIND, FPRINT_KIND, BASELINE_KIND}
    required_keys = {lib.API_FIELD, lib.KIND_FIELD, lib.METADATA_FIELD}

    def __init__(self, obj: Dict) -> None:
        for key in self.required_keys:
            if key not in obj:
                raise InvalidBaselineError(f"Missing {key} for input object")
        if not lib.valid_api_version(obj[lib.API_FIELD]):
            raise InvalidBaselineError(f"Invalid {lib.API_FIELD}")
        obj_kind = obj[lib.KIND_FIELD]
        if obj_kind not in self.valid_obj_kinds:
            raise InvalidBaselineError("Invalid kind for input object")
        if obj_kind == FPRINT_KIND:
            fprint = spyctl_fprints.Fingerprint(obj).as_dict()
            baseline_data = fprint
        elif obj_kind == GROUP_KIND:
            if lib.DATA_FIELD not in obj:
                raise InvalidBaselineError(
                    f"Missing {lib.DATA_FIELD} for input object"
                )
            fprints = obj[lib.DATA_FIELD][spyctl_fprints.FINGERPRINTS_FIELD]
            fprint_grps = spyctl_fprints.make_fingerprint_groups(fprints)
            all_grps = []
            for grps_list in fprint_grps:
                all_grps.extend(grps_list)
            if len(all_grps) > 1:
                raise InvalidBaselineError(
                    "Detected Fingerprints Group with mismatched Fingerprints."
                )
            baseline_data = merge.merge_objects(fprints)
            baseline_data = yaml.load(
                yaml.dump(
                    baseline_data, Dumper=merge.MergeDumper, sort_keys=False
                ),
                yaml.Loader,
            )
            latest_timestamp = (
                all_grps[0]
                .get(lib.METADATA_FIELD, {})
                .get(lib.LATEST_TIMESTAMP_FIELD)
            )
            if latest_timestamp is not None:
                baseline_data[lib.METADATA_FIELD][
                    lib.LATEST_TIMESTAMP_FIELD
                ] = latest_timestamp
        else:
            if lib.SPEC_FIELD not in obj:
                raise InvalidBaselineError(
                    f"Missing {lib.SPEC_FIELD} for input object"
                )
            baseline_data = obj
        self.metadata = baseline_data[lib.METADATA_FIELD]
        self.spec = baseline_data[lib.SPEC_FIELD]

    def as_dict(self) -> Dict:
        rv = {
            lib.API_FIELD: lib.API_VERSION,
            lib.KIND_FIELD: BASELINE_KIND,
            lib.METADATA_FIELD: self.metadata,
            lib.SPEC_FIELD: self.spec,
        }
        return rv


def create_baseline(obj: Dict):
    try:
        baseline = Baseline(obj)
    except (InvalidBaselineError, spyctl_fprints.InvalidFingerprintError) as e:
        cli.err_exit(f"Unable to create baseline. {' '.join(e.args)}")
    return baseline.as_dict()


def merge_baseline(baseline: Dict, with_obj: Dict, latest, output):
    try:
        _ = Baseline(baseline)
    except InvalidBaselineError as e:
        cli.err_exit(f"Invalid baseline as input. {' '.join(e.args)}")
    with_obj_kind = (
        with_obj.get(lib.KIND_FIELD) if isinstance(with_obj, dict) else None
    )
    if with_obj_kind == GROUP_KIND:
        merged_spec = merge.merge_objects(
            with_obj[lib.DATA_FIELD][spyctl_fprints.FINGERPRINTS_FIELD],
            lib.SPEC_FIELD,
        )
        merged_spec = yaml.load(
            yaml.dump(merged_spec, Dumper=merge.MergeDumper, sort_keys=False),
            yaml.Loader,
        )
        merged_spec = merge.merge_objects(
            [merged_spec, baseline], lib.SPEC_FIELD
        )
        merged_spec = yaml.load(
            yaml.dump(merged_spec, Dumper=merge.MergeDumper, sort_keys=False),
            yaml.Loader,
        )
        baseline[lib.SPEC_FIELD] = merged_spec[lib.SPEC_FIELD]
    elif latest:
        latest_timestamp = baseline.get(lib.METADATA_FIELD, {}).get(
            lib.LATEST_TIMESTAMP_FIELD
        )
        if latest_timestamp is not None:
            st = lib.time_inp(latest_timestamp)
        else:
            cli.err_exit(
                f"No {lib.LATEST_TIMESTAMP_FIELD} found in provided resource"
                " metadata field."
            )
        et = time.time()
        filters = lib.selectors_to_filters(baseline)
        ctx = cfgs.get_current_context()
        machines = api.get_machines(*ctx.get_api_data(), cli.api_err_exit)
        machines = filt.filter_machines(machines, filters)
        muids = [m["uid"] for m in machines]
        fingerprints = api.get_fingerprints(
            *ctx.get_api_data(),
            muids=muids,
            time=(st, et),
            err_fn=cli.api_err_exit,
        )
        fingerprints = filt.filter_fingerprints(fingerprints, **filters)
        fingerprints.append(baseline)
        merged_spec = merge.merge_objects(
            fingerprints,
            lib.SPEC_FIELD,
        )
        merged_spec = yaml.load(
            yaml.dump(merged_spec, Dumper=merge.MergeDumper, sort_keys=False),
            yaml.Loader,
        )
        baseline[lib.SPEC_FIELD] = merged_spec
    else:
        cli.try_log(
            f"Merging baseline with {with_obj_kind} is not yet supported."
        )
        return
    cli.show(baseline, output)
