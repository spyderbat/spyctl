from typing import Dict, Tuple, Optional, List
import spyctl.config.configs as cfg
import spyctl.spyctl_lib as lib
import json
import yaml
from tabulate import tabulate
import zulu


def create_suppression_policy(
    trace_summary: Dict, include_users: bool = False
) -> "SuppressionPolicy":
    pol = SuppressionPolicy(trace_summary, include_users)
    return pol


class SuppressionPolicy:
    def __init__(self, trace_summary: Dict, include_users: bool) -> None:
        self.trace_summary = trace_summary
        self.include_users = include_users
        self.selectors = {}
        self.flags = None
        self.__build_flags()
        self.__build_trace_selector()
        if include_users:
            self.__build_user_selector()

    @property
    def policy_scope_string(self):
        ctx = cfg.get_current_context()
        rv = f"Organization UID: {ctx.org_uid}\n"
        rv += yaml.dump({"selectors": self.selectors}, sort_keys=False)
        rv += yaml.dump({"allowedFlags": self.flags})
        return rv

    def as_dict(self) -> Dict:
        rv = {
            lib.API_FIELD: lib.API_VERSION,
            lib.KIND_FIELD: lib.POL_KIND,
            lib.METADATA_FIELD: {
                lib.NAME_FIELD: self.__build_name(),
                lib.TYPE_FIELD: lib.POL_TYPE_TRACE,
                lib.LATEST_TIMESTAMP_FIELD: self.trace_summary["last_seen"],
            },
            lib.SPEC_FIELD: {},
        }
        rv[lib.SPEC_FIELD].update(self.selectors)
        rv[lib.SPEC_FIELD][lib.ALLOWED_FLAGS_FIELD] = self.flags
        return rv

    def __build_name(self) -> str:
        trace_selector: Dict = self.trace_summary[lib.SPEC_FIELD][
            lib.TRACE_SELECTOR_FIELD
        ]
        trigger_ancestors = trace_selector.get(lib.TRIGGER_ANCESTORS_FIELD)
        if not trigger_ancestors:
            trigger_ancestors = trace_selector.get("trigger_ancestors")
        return f"Suppression Policy for {trigger_ancestors}"

    def __build_flags(self):
        flag_summary = self.trace_summary[lib.SPEC_FIELD][
            lib.FLAG_SUMMARY_FIELD
        ]
        flags = flag_summary.get("flag")
        if flags:
            flags = flags.get(lib.FLAGS_FIELD)
        else:
            flags = flag_summary[lib.FLAGS_FIELD]
        self.flags = [{lib.FLAG_CLASS: f[lib.FLAG_CLASS]} for f in flags]

    def __build_trace_selector(self):
        selector = {}
        trace_selector: Dict = self.trace_summary[lib.SPEC_FIELD][
            lib.TRACE_SELECTOR_FIELD
        ]
        trigger_class = trace_selector.get(lib.TRIGGER_CLASS_FIELD)
        if not trigger_class:
            trigger_class = trace_selector.get("trigger_class")
        if trigger_class:
            selector[lib.TRIGGER_CLASS_FIELD] = trigger_class
        trigger_ancestors = trace_selector.get(lib.TRIGGER_ANCESTORS_FIELD)
        if not trigger_ancestors:
            trigger_ancestors = trace_selector.get("trigger_ancestors")
        if trigger_ancestors:
            selector[lib.TRIGGER_ANCESTORS_FIELD] = trigger_ancestors
        self.selectors[lib.TRACE_SELECTOR_FIELD] = selector

    def __build_user_selector(self) -> Dict:
        selector = {}
        user_selector: Dict = self.trace_summary[lib.SPEC_FIELD][
            lib.USER_SELECTOR_FIELD
        ]
        users = user_selector.get(lib.USERS_FIELD)
        if not users:
            users = user_selector.get("whitelist")
        if users:
            selector["users"] = users
        self.selectors[lib.USER_SELECTOR_FIELD] = selector


def get_data_for_api_call(
    policy: SuppressionPolicy,
) -> Tuple[Optional[str], Dict]:
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
        lib.API_REQ_FIELD_NAME: name[:32],
        lib.API_REQ_FIELD_POLICY: json.dumps(policy),
        lib.API_REQ_FIELD_POL_SELECTORS: json.dumps(policy_selectors),
        lib.API_REQ_FIELD_TYPE: type,
        lib.API_REQ_FIELD_UID: uid,
    }
    if tags:
        data[lib.API_REQ_FIELD_TAGS] = tags
    else:
        data[lib.API_REQ_FIELD_TAGS] = []
    return uid, data


def s_policies_output(policies: List[Dict]):
    if len(policies) == 1:
        return policies[0]
    elif len(policies) > 1:
        return {lib.API_FIELD: lib.API_VERSION, lib.ITEMS_FIELD: policies}
    else:
        return {}


def s_policies_summary_output(policies: List[Dict]):
    output_list = []
    headers = ["UID", "NAME", "STATUS", "TYPE", "CREATE_TIME"]
    data = []
    for policy in policies:
        data.append(s_policy_summary_data(policy))
    data.sort(key=lambda x: [x[3], x[1]])
    output_list.append(tabulate(data, headers, tablefmt="plain"))
    return "\n".join(output_list)


def s_policy_summary_data(policy: Dict):
    uid = policy[lib.METADATA_FIELD].get(lib.METADATA_UID_FIELD)
    status = policy[lib.SPEC_FIELD].get(lib.ENABLED_FIELD, True)
    if status is False and uid:
        status = "Disabled"
    elif status and uid:
        status = "Enforcing"
    elif status is False:
        status = "Not Applied & Disabled"
    else:
        status = "Not Applied"
    if not uid:
        uid = "N/A"
    create_time = policy[lib.METADATA_FIELD].get(lib.METADATA_CREATE_TIME)
    if create_time:
        create_time = (
            zulu.parse(create_time).format("YYYY-MM-ddTHH:mm:ss") + "Z"
        )
    else:
        create_time = "N/A"
    rv = [
        uid,
        policy[lib.METADATA_FIELD][lib.NAME_FIELD],
        status,
        policy[lib.METADATA_FIELD][lib.TYPE_FIELD],
        create_time,
    ]
    return rv
