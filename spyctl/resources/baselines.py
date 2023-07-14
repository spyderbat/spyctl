from typing import Dict, Optional, List, Union

import spyctl.cli as cli
import spyctl.merge_lib as m_lib
import spyctl.resources.fingerprints as spyctl_fprints
import spyctl.resources.policies as spyctl_policies
import spyctl.spyctl_lib as lib
import spyctl.config.configs as cfg
import spyctl.resources.resources_lib as r_lib
import spyctl.schemas as schemas

FPRINT_KIND = spyctl_fprints.FPRINT_KIND
GROUP_KIND = spyctl_fprints.GROUP_KIND
BASELINE_KIND = lib.BASELINE_KIND
POLICY_KIND = lib.POL_KIND
BASELINE_META_MERGE_SCHEMA = m_lib.MergeSchema(
    lib.METADATA_FIELD,
    merge_functions={
        lib.METADATA_NAME_FIELD: m_lib.keep_base_value_merge,
        lib.METADATA_TYPE_FIELD: m_lib.all_eq_merge,
        lib.LATEST_TIMESTAMP_FIELD: m_lib.greatest_value_merge,
    },
)
BASELINE_MERGE_SCHEMAS = [BASELINE_META_MERGE_SCHEMA, m_lib.SPEC_MERGE_SCHEMA]


class InvalidBaselineError(Exception):
    pass


class Baseline:
    required_keys = {
        lib.API_FIELD,
        lib.KIND_FIELD,
        lib.METADATA_FIELD,
        lib.SPEC_FIELD,
    }

    def __init__(self, obj: Dict, name: str = None) -> None:
        self.baseline = {}
        for key in self.required_keys:
            if key not in obj:
                raise InvalidBaselineError(f"Missing {key} for input object")
        self.metadata = obj[lib.METADATA_FIELD]
        if name:
            self.metadata[lib.METADATA_NAME_FIELD] = name
        self.spec = obj[lib.SPEC_FIELD]

    def as_dict(self) -> Dict:
        rv = {
            lib.API_FIELD: lib.API_VERSION,
            lib.KIND_FIELD: BASELINE_KIND,
            lib.METADATA_FIELD: self.metadata,
            lib.SPEC_FIELD: self.spec,
        }
        return rv


def create_baseline(
    input_data: Union[Dict, List[Dict]],
    name: str = None,
    ctx: cfg.Context = None,
):
    input_objs = []
    if isinstance(input_data, list):
        if len(input_data) == 0:
            cli.err_exit("Nothing to build baseline with")
        for datum in input_data:
            input_objs.extend(r_lib.handle_input_data(datum, ctx))
    else:
        input_objs.extend(r_lib.handle_input_data(input_data, ctx))
    if len(input_objs) == 0:
        cli.err_exit("Nothing to build baseline with")
    merge_object = m_lib.MergeObject(
        input_objs[0], BASELINE_MERGE_SCHEMAS, None
    )
    if len(input_objs) == 1:
        merge_object.asymmetric_merge({})
    else:
        for obj in input_objs[1:]:
            merge_object.symmetric_merge(obj)
    try:
        baseline = Baseline(merge_object.get_obj_data(), name)
    except InvalidBaselineError as e:
        cli.err_exit(f"Unable to create baseline. {' '.join(e.args)}")
    # Validate the Baseline
    rv = baseline.as_dict()
    if not schemas.valid_object(rv):
        cli.err_exit("Created policy failed validation.")
    return baseline.as_dict()


def merge_baseline(
    baseline: Dict, with_obj: Dict, fingerprints
) -> Optional[m_lib.MergeObject]:
    try:
        _ = Baseline(baseline)
    except InvalidBaselineError as e:
        cli.err_exit(f"Invalid baseline as input. {' '.join(e.args)}")
    with_obj_kind = (
        with_obj.get(lib.KIND_FIELD) if isinstance(with_obj, dict) else None
    )
    base_merge_obj = m_lib.MergeObject(
        baseline, BASELINE_MERGE_SCHEMAS, Baseline
    )
    if with_obj_kind == GROUP_KIND:
        fingerprints = with_obj.get(lib.DATA_FIELD, {}).get(
            spyctl_fprints.FINGERPRINTS_FIELD, []
        )
        for fprint in fingerprints:
            base_merge_obj.asymmetric_merge(fprint)
        if not base_merge_obj.is_valid:
            cli.try_log("Merge was unable to create a valid baseline")
    elif with_obj_kind == BASELINE_KIND:
        try:
            _ = Baseline(with_obj)
        except (
            InvalidBaselineError,
            spyctl_fprints.InvalidFingerprintError,
        ) as e:
            cli.err_exit(
                "Invalid baseline object as 'with object' input."
                f" {' '.join(e.args)}"
            )
        base_merge_obj.asymmetric_merge(with_obj)
        if not base_merge_obj.is_valid:
            cli.try_log("Merge was unable to create a valid baseline")
    elif with_obj == POLICY_KIND:
        try:
            _ = spyctl_policies.Policy(with_obj)
        except spyctl_policies.InvalidPolicyError as e:
            cli.err_exit(
                "Invalid policy object as 'with object' input."
                f" {' '.join(e.args)}"
            )
        base_merge_obj.asymmetric_merge(with_obj)
        if not base_merge_obj.is_valid:
            cli.try_log("Merge was unable to create a valid baseline")
    elif fingerprints is not None:
        for fingerprint in fingerprints:
            base_merge_obj.asymmetric_merge(fingerprint)
        if not base_merge_obj.is_valid:
            cli.try_log("Merge was unable to create a valid baseline")
    else:
        cli.try_log(
            f"Merging baseline with {with_obj_kind} is not yet supported."
        )
        return
    return base_merge_obj


def diff_baseline(baseline: Dict, with_obj: Dict, latest):
    base_merge_obj = merge_baseline(baseline, with_obj, latest)
    if not base_merge_obj:
        cli.err_exit("Unable to perform Diff")
    diff = base_merge_obj.get_diff()
    return diff
