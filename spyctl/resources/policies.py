import json
from typing import Dict, List, Optional, Tuple

import zulu
from tabulate import tabulate

import spyctl.cli as cli
import spyctl.merge_lib as m_lib
import spyctl.resources.baselines as spyctl_baselines
import spyctl.resources.fingerprints as spyctl_fprints
import spyctl.spyctl_lib as lib

# For the Spyderbat API
API_REQ_FIELD_NAME = "name"
API_REQ_FIELD_POLICY = "policy"
API_REQ_FIELD_POL_SELECTORS = "selectors"
API_REQ_FIELD_TAGS = "tags"
API_REQ_FIELD_TYPE = "type"
API_REQ_FIELD_UID = "uid"

FPRINT_KIND = spyctl_fprints.FPRINT_KIND
GROUP_KIND = spyctl_fprints.GROUP_KIND
BASELINE_KIND = lib.BASELINE_KIND
POLICY_KIND = lib.POL_KIND

POLICY_META_MERGE_SCHEMA = m_lib.MergeSchema(
    lib.METADATA_FIELD,
    merge_functions={
        lib.METADATA_NAME_FIELD: m_lib.keep_base_value_merge,
        lib.METADATA_TYPE_FIELD: m_lib.all_eq_merge,
        lib.METADATA_UID_FIELD: m_lib.keep_base_value_merge,
        lib.METADATA_CREATE_TIME: m_lib.keep_base_value_merge,
        lib.LATEST_TIMESTAMP_FIELD: m_lib.greatest_value_merge,
    },
)
POLICY_MERGE_SCHEMAS = [POLICY_META_MERGE_SCHEMA, m_lib.SPEC_MERGE_SCHEMA]


class InvalidPolicyError(Exception):
    pass


class Policy:
    required_keys = {
        lib.API_FIELD,
        lib.KIND_FIELD,
        lib.METADATA_FIELD,
        lib.SPEC_FIELD,
    }
    valid_obj_kinds = {POLICY_KIND, BASELINE_KIND}

    def __init__(self, obj: Dict) -> None:
        self.policy = {}
        obj_kind = obj.get(lib.KIND_FIELD)
        if obj_kind not in self.valid_obj_kinds:
            raise InvalidPolicyError("Invalid kind for input object")
        if obj_kind == BASELINE_KIND:
            for key in self.required_keys:
                if key not in obj:
                    raise InvalidPolicyError(f"Missing {key} for input object")
            try:
                baseline = spyctl_baselines.Baseline(obj)
            except (
                spyctl_baselines.InvalidBaselineError,
                spyctl_fprints.InvalidFingerprintError,
            ) as e:
                (
                    "Unable to create policy, invalid input object."
                    f" {' '.join(e.args)}"
                )
            policy_data = baseline.as_dict()
        else:
            for key in self.required_keys:
                if key not in obj:
                    raise InvalidPolicyError(f"Missing {key} for input object")
            policy_data = obj
        self.metadata = policy_data[lib.METADATA_FIELD]
        self.spec = policy_data[lib.SPEC_FIELD]
        self.response_actions = policy_data[lib.SPEC_FIELD].get(
            lib.RESPONSE_FIELD, lib.RESPONSE_ACTION_TEMPLATE
        )
        self.spec[lib.RESPONSE_FIELD] = self.response_actions

    def get_uid(self) -> Optional[str]:
        return self.policy[lib.METADATA_FIELD].get(lib.METADATA_UID_FIELD)

    def as_dict(self):
        rv = {
            lib.API_FIELD: lib.API_VERSION,
            lib.KIND_FIELD: POLICY_KIND,
            lib.METADATA_FIELD: self.metadata,
            lib.SPEC_FIELD: self.spec,
        }
        return rv

    def add_response_action(self, resp_action: Dict):
        resp_actions: List[Dict] = self.policy[lib.SPEC_FIELD][
            lib.RESPONSE_FIELD
        ][lib.RESP_ACTIONS_FIELD]
        resp_actions.append(resp_action)

    def disable(self):
        spec = self.policy[lib.SPEC_FIELD]
        spec[lib.ENABLED_FIELD] = False

    def enable(self):
        spec = self.policy[lib.SPEC_FIELD]
        if lib.ENABLED_FIELD in spec:
            del spec[lib.ENABLED_FIELD]


def get_data_for_api_call(policy: Policy) -> Tuple[Optional[str], str]:
    policy = policy.as_dict()
    name = policy[lib.METADATA_FIELD][lib.METADATA_NAME_FIELD]
    type = policy[lib.METADATA_FIELD][lib.METADATA_TYPE_FIELD]
    tags = policy[lib.METADATA_FIELD].get(lib.METADATA_TAGS_FIELD)
    uid = policy[lib.METADATA_FIELD].get(lib.METADATA_UID_FIELD, "")
    policy_selectors = {
        key: value
        for key, value in policy[lib.SPEC_FIELD].items()
        if key.endswith("Selector")
    }
    data = {
        API_REQ_FIELD_NAME: name[:32],
        API_REQ_FIELD_POLICY: json.dumps(policy),
        API_REQ_FIELD_POL_SELECTORS: json.dumps(policy_selectors),
        API_REQ_FIELD_TYPE: type,
        API_REQ_FIELD_UID: uid,
    }
    if tags:
        data[API_REQ_FIELD_TAGS] = tags
    else:
        data[API_REQ_FIELD_TAGS] = []
    return uid, data


def create_policy(obj: Dict):
    obj_kind = obj.get(lib.KIND_FIELD)
    if obj_kind != POLICY_KIND:
        try:
            baseline = spyctl_baselines.Baseline(obj)
        except (
            spyctl_baselines.InvalidBaselineError,
            spyctl_fprints.InvalidFingerprintError,
        ) as e:
            cli.err_exit(f"Unable to create policy. {' '.join(e.args)}")
        try:
            policy = Policy(baseline.as_dict())
        except InvalidPolicyError as e:
            cli.err_exit(f"Unable to create policy. {' '.join(e.args)}")
    else:
        try:
            policy = Policy(obj)
        except InvalidPolicyError as e:
            cli.err_exit(f"Unable to create policy. {' '.join(e.args)}")
    return policy.as_dict()


def merge_policy(
    policy: Dict, with_obj: Dict, fingerprints: List[Dict] = None
) -> Optional[m_lib.MergeObject]:
    try:
        _ = Policy(policy)
    except InvalidPolicyError as e:
        cli.err_exit(f"Invalid policy as input. {' '.join(e.args)}")
    with_obj_kind = (
        with_obj.get(lib.KIND_FIELD) if isinstance(with_obj, dict) else None
    )
    pol_merge_obj = m_lib.MergeObject(policy, POLICY_MERGE_SCHEMAS, Policy)
    if with_obj_kind == GROUP_KIND:
        fingerprints = with_obj.get(lib.DATA_FIELD, {}).get(
            spyctl_fprints.FINGERPRINTS_FIELD, []
        )
        for fprint in fingerprints:
            pol_merge_obj.asymmetric_merge(fprint)
        if not pol_merge_obj.is_valid:
            cli.try_log("Merge was unable to create a valid policy")
    elif with_obj_kind == BASELINE_KIND:
        try:
            _ = spyctl_baselines.Baseline(with_obj)
        except (
            spyctl_baselines.InvalidBaselineError,
            spyctl_fprints.InvalidFingerprintError,
        ) as e:
            cli.err_exit(
                "Invalid baseline object as 'with object' input."
                f" {' '.join(e.args)}"
            )
        pol_merge_obj.asymmetric_merge(with_obj)
        if not pol_merge_obj.is_valid:
            cli.try_log("Merge was unable to create a valid policy")
    elif with_obj == POLICY_KIND:
        try:
            _ = Policy(with_obj)
        except InvalidPolicyError as e:
            cli.err_exit(
                "Invalid policy object as 'with object' input."
                f" {' '.join(e.args)}"
            )
        pol_merge_obj.asymmetric_merge(with_obj)
        if not pol_merge_obj.is_valid:
            cli.try_log("Merge was unable to create a valid policy")
    elif fingerprints is not None:
        for fingerprint in fingerprints:
            pol_merge_obj.asymmetric_merge(fingerprint)
        if not pol_merge_obj.is_valid:
            cli.try_log("Merge was unable to create a valid policy")
    else:
        cli.try_log(
            f"Merging policy with {with_obj_kind} is not yet supported."
        )
        return
    return pol_merge_obj


def diff_policy(policy: Dict, with_obj: Dict, fingerprints=None) -> str:
    pol_merge_obj = merge_policy(policy, with_obj, fingerprints)
    if not pol_merge_obj:
        cli.err_exit("Unable to perform Diff")
    diff = pol_merge_obj.get_diff()
    return diff


def policies_output(policies: List[Dict]):
    if len(policies) == 1:
        return policies[0]
    elif len(policies) > 1:
        return {lib.API_FIELD: lib.API_VERSION, lib.ITEMS_FIELD: policies}
    else:
        return {}


def policies_summary_output(policies: List[Dict]):
    headers = ["UID", "NAME", "STATUS", "TYPE", "CREATE_TIME"]
    data = []
    for policy in policies:
        data.append(policy_summary_data(policy))
    data.sort(key=lambda x: [x[3], x[1], lib.to_timestamp(x[4])])
    return tabulate(data, headers, tablefmt="plain")


def policy_summary_data(policy: Dict):
    status = policy[lib.SPEC_FIELD].get(lib.ENABLED_FIELD)
    if status is False:
        status = "Disabled"
    else:
        status = "Enforcing"
    create_time = policy[lib.METADATA_FIELD][lib.METADATA_CREATE_TIME]
    create_time = zulu.parse(create_time).format("YYYY-MM-ddTHH:mm:ss") + "Z"
    rv = [
        policy[lib.METADATA_FIELD].get(lib.METADATA_UID_FIELD),
        policy[lib.METADATA_FIELD][lib.NAME_FIELD],
        status,
        policy[lib.METADATA_FIELD][lib.TYPE_FIELD],
        create_time,
    ]
    return rv


def get_policy_by_uid(
    uid: str, policies: Optional[List[Dict]] = None
) -> Optional[Dict]:
    from spyctl.api import get_policies
    from spyctl.config.configs import get_current_context
    from spyctl.filter_resource import filter_obj

    ctx = get_current_context()
    if not policies:
        policies = get_policies(*ctx.get_api_data())
    policies = filter_obj(
        policies,
        [
            [lib.METADATA_FIELD, lib.METADATA_UID_FIELD],
        ],
        uid,
    )
    if not policies:
        return None
    return policies[0]
