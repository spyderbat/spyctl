from typing import Dict, Optional, List

import spyctl.cli as cli
import spyctl.merge_lib as m_lib
import spyctl.resources.fingerprints as spyctl_fprints
import spyctl.resources.policies as spyctl_policies
import spyctl.spyctl_lib as lib

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
    valid_obj_kinds = {GROUP_KIND, FPRINT_KIND, BASELINE_KIND, POLICY_KIND}
    required_keys = {lib.API_FIELD, lib.KIND_FIELD, lib.METADATA_FIELD}

    def __init__(self, obj: Dict, name: str = None) -> None:
        if isinstance(obj, list):
            if len(obj) == 1:
                obj = obj[0]
        if isinstance(obj, list):
            baseline_data = self.__baseline_from_fingerprints_list(obj)
        else:
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
                fprints = obj[lib.DATA_FIELD].get(
                    spyctl_fprints.FINGERPRINTS_FIELD, []
                )
                baseline_data = self.__baseline_from_fingerprints_list(fprints)
            elif obj_kind == POLICY_KIND:
                policy = spyctl_policies.Policy(obj)
                baseline_data = policy.as_dict()
            else:
                if lib.SPEC_FIELD not in obj:
                    raise InvalidBaselineError(
                        f"Missing {lib.SPEC_FIELD} for input object"
                    )
                baseline_data = obj
        self.metadata = baseline_data[lib.METADATA_FIELD]
        if name:
            self.metadata[lib.METADATA_NAME_FIELD] = name
        self.spec = baseline_data[lib.SPEC_FIELD]

    def as_dict(self) -> Dict:
        rv = {
            lib.API_FIELD: lib.API_VERSION,
            lib.KIND_FIELD: BASELINE_KIND,
            lib.METADATA_FIELD: self.metadata,
            lib.SPEC_FIELD: self.spec,
        }
        return rv

    def __baseline_from_fingerprints_list(self, fprints: List[Dict]) -> Dict:
        if len(fprints) == 0:
            raise InvalidBaselineError(
                "Nothing to create baseline object from."
            )
        elif len(fprints) == 1:
            fprint_merge_base = m_lib.MergeObject(
                fprints[0],
                spyctl_fprints.FPRINT_MERGE_SCHEMAS,
                spyctl_fprints.Fingerprint,
            )
            fprint_merge_base.asymmetric_merge({})
            if fprint_merge_base.is_valid:
                baseline_data = fprint_merge_base.get_obj_data()
        else:
            fprint_merge_base = m_lib.MergeObject(
                fprints[0],
                spyctl_fprints.FPRINT_MERGE_SCHEMAS,
                spyctl_fprints.Fingerprint,
            )
            for i, fprint in enumerate(fprints[1:]):
                fprint_merge_base.symmetric_merge(fprint)
            if fprint_merge_base.is_valid:
                baseline_data = fprint_merge_base.get_obj_data()
            else:
                raise InvalidBaselineError(
                    "Merged Fingerprint Group failed validation."
                )
        return baseline_data


def create_baseline(obj: Dict, name: str = None):
    try:
        baseline = Baseline(obj, name)
    except (InvalidBaselineError, spyctl_fprints.InvalidFingerprintError) as e:
        cli.err_exit(f"Unable to create baseline. {' '.join(e.args)}")
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
