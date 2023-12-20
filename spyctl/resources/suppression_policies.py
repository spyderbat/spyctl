from typing import Dict, Tuple, Optional, List
import spyctl.config.configs as cfg
import spyctl.spyctl_lib as lib
import json
import yaml
from tabulate import tabulate
import zulu
import spyctl.cli as cli
import spyctl.merge_lib as m_lib


def undash(s: str) -> str:
    return s.replace("-", "_")


S_POLICY_META_MERGE_SCHEMA = m_lib.MergeSchema(
    lib.METADATA_FIELD,
    merge_functions={
        lib.METADATA_NAME_FIELD: m_lib.keep_base_value_merge,
        lib.METADATA_TYPE_FIELD: m_lib.all_eq_merge,
        lib.METADATA_UID_FIELD: m_lib.keep_base_value_merge,
        lib.METADATA_CREATE_TIME: m_lib.keep_base_value_merge,
        lib.LATEST_TIMESTAMP_FIELD: m_lib.greatest_value_merge,
    },
)
T_S_POLICY_MERGE_SCHEMAS = [
    S_POLICY_META_MERGE_SCHEMA,
    m_lib.TRACE_SUPPRESSION_SPEC_MERGE_SCHEMA,
]

TRACE_POL_OPTION_TO_SELECTORS_MAP = {
    undash(lib.SUP_POL_CMD_TRIG_ANCESTORS): lib.TRACE_SELECTOR_FIELD,
    undash(lib.SUP_POL_CMD_TRIG_CLASS): lib.TRACE_SELECTOR_FIELD,
    undash(lib.SUP_POL_CMD_USERS): lib.USER_SELECTOR_FIELD,
    undash(lib.SUP_POL_CMD_INT_USERS): lib.USER_SELECTOR_FIELD,
    undash(lib.SUP_POL_CMD_N_INT_USERS): lib.USER_SELECTOR_FIELD,
}
TRACE_POL_OPTION_TO_FIELD_MAP = {
    undash(lib.SUP_POL_CMD_TRIG_ANCESTORS): lib.TRIGGER_ANCESTORS_FIELD,
    undash(lib.SUP_POL_CMD_TRIG_CLASS): lib.TRIGGER_CLASS_FIELD,
    undash(lib.SUP_POL_CMD_USERS): lib.USERS_FIELD,
    undash(lib.SUP_POL_CMD_INT_USERS): lib.INTERACTIVE_USERS_FIELD,
    undash(lib.SUP_POL_CMD_N_INT_USERS): lib.NON_INTERACTIVE_USERS_FIELD,
}

REDFLAG_POL_OPTION_TO_SELECTORS_MAP = {
    lib.SUP_POL_CMD_USERS: lib.USER_SELECTOR_FIELD,
}


def build_trace_suppression_policy(
    trace_summary: Dict = None,
    include_users: bool = False,
    mode: str = lib.POL_MODE_ENFORCE,
    name: str = None,
    **selectors,
):
    pol = TraceSuppressionPolicy(trace_summary, mode, name)
    if not include_users:
        pol.spec.pop(lib.USER_SELECTOR_FIELD, None)
        pol.selectors.pop(lib.USER_SELECTOR_FIELD, None)
    pol.update_selectors(**selectors)
    return pol


class TraceSuppressionPolicy:
    def __init__(
        self,
        obj: Dict = None,
        mode: str = lib.POL_MODE_ENFORCE,
        name: str = None,
    ) -> None:
        if obj:
            self.metadata: Dict = obj[lib.METADATA_FIELD]
            self.spec: Dict = obj[lib.SPEC_FIELD]
        else:
            self.metadata = {}
            self.spec = {}
        self.selectors: Dict[str, Dict] = {}
        self.flags = []
        self.name = name
        self.mode = self.spec.get(lib.POL_MODE_FIELD, mode)
        self.__build_name()
        self.__build_flags()
        self.__build_trace_selector()
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
                lib.METADATA_NAME_FIELD: self.name,
                lib.METADATA_TYPE_FIELD: lib.POL_TYPE_TRACE,
                lib.METADATA_S_CHECKSUM_FIELD: lib.make_checksum(
                    json.dumps(self.selectors, sort_keys=True)
                ),
            },
            lib.SPEC_FIELD: {},
        }
        if lib.METADATA_UID_FIELD in self.metadata:
            rv[lib.METADATA_FIELD][lib.METADATA_UID_FIELD] = self.metadata[
                lib.METADATA_UID_FIELD
            ]
        if lib.METADATA_CREATE_TIME in self.metadata:
            rv[lib.METADATA_FIELD][lib.METADATA_CREATE_TIME] = self.metadata[
                lib.METADATA_CREATE_TIME
            ]
        rv[lib.SPEC_FIELD].update(
            json.loads(json.dumps(self.selectors, sort_keys=True))
        )
        rv[lib.SPEC_FIELD][lib.POL_MODE_FIELD] = self.mode
        rv[lib.SPEC_FIELD][lib.ALLOWED_FLAGS_FIELD] = sorted(
            self.flags, key=lambda x: x[lib.FLAG_CLASS]
        )
        return rv

    def update_selectors(self, **selectors) -> Dict:
        selectors = {undash(k): v for k, v in selectors.items()}
        if (
            undash(lib.SUP_POL_CMD_INT_USERS) in selectors
            or undash(lib.SUP_POL_CMD_N_INT_USERS) in selectors
            or undash(lib.SUP_POL_CMD_USERS) in selectors
        ):
            user_selector = self.selectors.get(lib.USER_SELECTOR_FIELD)
            if user_selector:
                user_selector.pop(lib.USERS_FIELD, None)
        for key, values in selectors.items():
            if (
                key not in TRACE_POL_OPTION_TO_SELECTORS_MAP
                or key not in TRACE_POL_OPTION_TO_FIELD_MAP
            ):
                cli.err_exit("Unrecognized selector field")
            selector_name = TRACE_POL_OPTION_TO_SELECTORS_MAP[key]
            field_name = TRACE_POL_OPTION_TO_FIELD_MAP[key]
            self.selectors.setdefault(selector_name, {})
            self.selectors[selector_name].update({field_name: values})

    def __build_name(self):
        if self.name:
            return
        if not self.metadata:
            self.name = "Custom Trace Suppression Policy"
            return
        trace_selector: Dict = self.spec[lib.TRACE_SELECTOR_FIELD]
        trigger_ancestors = trace_selector.get(lib.TRIGGER_ANCESTORS_FIELD)
        if not trigger_ancestors:
            trigger_ancestors = trace_selector.get("trigger_ancestors")
        if not trigger_ancestors:
            self.name = "Custom Trace Suppression Policy"
        if isinstance(trigger_ancestors, list):
            self.name = f"Trace Suppression Policy for {trigger_ancestors[0]}"
        else:
            self.name = f"Trace Suppression Policy for {trigger_ancestors}"

    def __build_flags(self):
        if not self.spec:
            return
        spec_flags = self.spec.get(lib.FLAG_SUMMARY_FIELD)
        if not spec_flags:
            flags = self.spec.get(lib.ALLOWED_FLAGS_FIELD)
            if flags:
                self.flags = flags
            else:
                self.flags = []
        else:
            flags = spec_flags.get("flag")
            if flags:
                flags = flags.get(lib.FLAGS_FIELD)
            else:
                flags = spec_flags[lib.FLAGS_FIELD]
            self.flags = [{lib.FLAG_CLASS: f[lib.FLAG_CLASS]} for f in flags]

    def __build_trace_selector(self):
        if not self.spec:
            return
        selector = {}
        trace_selector: Dict = self.spec.get(lib.TRACE_SELECTOR_FIELD, {})
        trigger_class = trace_selector.get(lib.TRIGGER_CLASS_FIELD)
        if not trigger_class:
            trigger_class = trace_selector.get("trigger_class")
        if trigger_class:
            if isinstance(trigger_class, list):
                selector[lib.TRIGGER_CLASS_FIELD] = trigger_class
            else:
                selector[lib.TRIGGER_CLASS_FIELD] = [trigger_class]
        trigger_ancestors = trace_selector.get(lib.TRIGGER_ANCESTORS_FIELD)
        if not trigger_ancestors:
            trigger_ancestors = trace_selector.get("trigger_ancestors")
        if trigger_ancestors:
            if isinstance(trigger_class, list):
                selector[lib.TRIGGER_ANCESTORS_FIELD] = trigger_ancestors
            else:
                selector[lib.TRIGGER_ANCESTORS_FIELD] = [trigger_ancestors]
        if selector:
            self.selectors[lib.TRACE_SELECTOR_FIELD] = selector

    def __build_user_selector(self):
        if not self.spec:
            return
        selector = {}
        user_selector: Dict = self.spec.get(lib.USER_SELECTOR_FIELD, {})
        users = user_selector.get(lib.USERS_FIELD)
        if not users:
            users = user_selector.get("whitelist")
        if users:
            selector["users"] = users
        if selector:
            self.selectors[lib.USER_SELECTOR_FIELD] = selector


def get_data_for_api_call(
    policy: TraceSuppressionPolicy,
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
    # Add a tag with the hash of the selectors
    data[lib.API_REQ_FIELD_TAGS].append(
        "SELECTOR_HASH:"
        f"{policy[lib.METADATA_FIELD][lib.METADATA_S_CHECKSUM_FIELD]}"
    )
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
    mode = policy[lib.SPEC_FIELD].get(lib.POL_MODE_FIELD, lib.POL_MODE_ENFORCE)
    if status is False and uid:
        status = "Disabled"
    elif status is False and not uid:
        status = "Not Applied & Disabled"
    elif status and mode == lib.POL_MODE_ENFORCE and uid:
        status = "Enforcing"
    elif status and mode == lib.POL_MODE_AUDIT and uid:
        status = "Auditing"
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
