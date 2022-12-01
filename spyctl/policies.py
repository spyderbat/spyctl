import json
from typing import Dict, List, Optional, Tuple

# For the Spyderbat API
API_REQ_FIELD_NAME = "name"
API_REQ_FIELD_POLICY = "policy"
API_REQ_FIELD_POL_SELECTORS = "policy_selectors"
API_REQ_FIELD_TAGS = "tags"
API_REQ_FIELD_TYPE = "type"
API_REQ_FIELD_UID = "uid"

# For policy objects
S_CRIT = "critical"
S_HIGH = "high"
S_MED = "medium"
S_LOW = "low"
S_INFO = "info"
ACTION_KILL_POD = "kill-pod"
ACTION_KILL_PROC = "kill-process"
ACTION_KILL_PROC_GRP = "kill-process-group"
ACTION_WEBHOOK = "webhook"
ALLOWED_SEVERITIES = {S_CRIT, S_HIGH, S_MED, S_LOW, S_INFO}
ALLOWED_TEMPLATES = {"json", "yaml", "slack"}
ALLOWED_ACTIONS = {
    ACTION_WEBHOOK,
    ACTION_KILL_POD,
    ACTION_KILL_PROC,
    ACTION_KILL_PROC_GRP,
}
API_VERSION = "spyderbat/v1"
POL_KIND = "SpyderbatPolicy"
POL_TYPE_CONT = "container"
POL_TYPE_SVC = "service"
POL_TYPES = {POL_TYPE_SVC, POL_TYPE_CONT}
K8S_API_FIELD = "apiVersion"
K8S_KIND_FIELD = "kind"
K8S_METADATA_FIELD = "metadata"
K8S_SPEC_FIELD = "spec"
K8S_MATCH_LABELS_FIELD = "matchLabels"
METADATA_NAME_FIELD = "name"
METADATA_TYPE_FIELD = "type"
METADATA_UID_FIELD = "uid"
METADATA_TAGS_FIELD = "tags"
METADATA_NAME_TEMPLATE = "foobar-policy"
CONT_SELECTOR_FIELD = "containerSelector"
NAMESPACE_SELECTOR_FIELD = "namespaceSelector"
MACHINE_SELECTOR_FIELD = "machineSelector"
POD_SELECTOR_FIELD = "podSelector"
SVC_SELECTOR_FIELD = "serviceSelector"
ENABLED_FIELD = "enabled"
PROC_POLICY_FIELD = "processPolicy"
NET_POLICY_FIELD = "networkPolicy"
RESPONSE_FIELD = "response"
RESP_DEFAULT_FIELD = "default"
RESP_ACTIONS_FIELD = "actions"
RESP_ACTION_NAME_FIELD = "actionName"
RESP_URL_FIELD = "url"
RESP_TEMPLATE_FIELD = "template"
RESP_SEVERITY_FILED = "severity"
CONTAINER_SELECTOR_TEMPLATE = {
    "image": "foo",
    "imageID": "sha256:bar",
    "containerName": "/foobar",
}
SVC_SELECTOR_TEMPLATE = {"cgroup": "systemd:/system.slice/foobar.service"}
PROCESS_POLICY_TEMPLATE = [
    {
        "name": "foo",
        "exe": ["/usr/bin/foo", "/usr/sbin/foo"],
        "id": "foo_0",
        "euser": ["root"],
        "children": [{"name": "bar", "exe": ["/usr/bin/bar"], "id": "bar_0"}],
    }
]
NETWORK_POLICY_TEMPLATE = {
    "ingress": [
        {
            "from": [
                {
                    "ipBlock": {
                        "cidr": "0.0.0.0/0",
                    }
                }
            ],
            "ports": [{"protocol": "TCP", "port": 1337}],
            "processes": ["foo_0"],
        }
    ],
    "egress": [
        {
            "to": [{"dnsSelector": ["foobar.com"]}],
            "ports": [{"protocol": "TCP", "port": 1337}],
            "processes": ["bar_0"],
        }
    ],
}
RESPONSE_ACTION_TEMPLATE = {
    RESP_DEFAULT_FIELD: {RESP_SEVERITY_FILED: S_HIGH},
    RESP_ACTIONS_FIELD: [],
}
METADATA_TEMPLATES = {
    POL_TYPE_CONT: {
        METADATA_NAME_FIELD: METADATA_NAME_TEMPLATE,
        METADATA_TYPE_FIELD: POL_TYPE_CONT,
    },
    POL_TYPE_SVC: {
        METADATA_NAME_FIELD: METADATA_NAME_TEMPLATE,
        METADATA_TYPE_FIELD: POL_TYPE_SVC,
    },
}
SPEC_TEMPLATES = {
    POL_TYPE_CONT: {
        CONT_SELECTOR_FIELD: CONTAINER_SELECTOR_TEMPLATE,
        PROC_POLICY_FIELD: PROCESS_POLICY_TEMPLATE,
        NET_POLICY_FIELD: NETWORK_POLICY_TEMPLATE,
        RESPONSE_FIELD: RESPONSE_ACTION_TEMPLATE,
    },
    POL_TYPE_SVC: {
        SVC_SELECTOR_FIELD: SVC_SELECTOR_TEMPLATE,
        PROC_POLICY_FIELD: PROCESS_POLICY_TEMPLATE,
        NET_POLICY_FIELD: NETWORK_POLICY_TEMPLATE,
        RESPONSE_FIELD: RESPONSE_ACTION_TEMPLATE,
    },
}


class PolicyTypeError(Exception):
    pass


class InvalidPolicyArgument(Exception):
    pass


class Policy:
    def __init__(self, pol_type: str, fprint_or_pol: Dict = None) -> None:
        self.policy = {}
        if pol_type not in POL_TYPES:
            raise PolicyTypeError(f"{pol_type} is not a valid policy type")
        if fprint_or_pol:
            req_keys = [K8S_API_FIELD, K8S_METADATA_FIELD, K8S_SPEC_FIELD]
            for key in req_keys:
                if key not in fprint_or_pol:
                    raise InvalidPolicyArgument(
                        f"{key} field missing from input fingerprint or policy"
                    )
            self.policy[K8S_API_FIELD] = fprint_or_pol[K8S_API_FIELD]
            self.policy[K8S_KIND_FIELD] = POL_KIND
            self.policy[K8S_METADATA_FIELD] = fprint_or_pol[K8S_METADATA_FIELD]
            self.policy[K8S_SPEC_FIELD] = fprint_or_pol[K8S_SPEC_FIELD]
            self.spec.setdefault(RESPONSE_FIELD, RESPONSE_ACTION_TEMPLATE)
            if self.pol_type != pol_type:
                raise PolicyTypeError(
                    f"Policy type mismatch {self.pol_type} != {pol_type}"
                )
        else:
            self.policy.update(
                {
                    K8S_API_FIELD: API_VERSION,
                    K8S_KIND_FIELD: POL_KIND,
                    K8S_METADATA_FIELD: METADATA_TEMPLATES[pol_type],
                    K8S_SPEC_FIELD: SPEC_TEMPLATES[pol_type],
                }
            )

    @property
    def metadata(self) -> Dict:
        return self.policy[K8S_METADATA_FIELD]

    @property
    def spec(self) -> Dict:
        return self.policy[K8S_SPEC_FIELD]

    @property
    def pol_type(self) -> str:
        return self.metadata.get(METADATA_TYPE_FIELD)

    def get_uid(self) -> Optional[str]:
        return self.policy[K8S_METADATA_FIELD].get(METADATA_UID_FIELD)

    def get_output(self):
        copy_fields = [
            K8S_API_FIELD,
            K8S_KIND_FIELD,
            K8S_METADATA_FIELD,
            K8S_SPEC_FIELD,
        ]
        spec_copy_fields = [
            ENABLED_FIELD,
            CONT_SELECTOR_FIELD,
            SVC_SELECTOR_FIELD,
            MACHINE_SELECTOR_FIELD,
            POD_SELECTOR_FIELD,
            NAMESPACE_SELECTOR_FIELD,
            PROC_POLICY_FIELD,
            NET_POLICY_FIELD,
            RESPONSE_FIELD,
        ]
        rv = dict()
        for key in copy_fields:
            if key == K8S_SPEC_FIELD:
                spec = self.policy[key]
                rv[key] = {}
                for spec_key in spec_copy_fields:
                    if spec_key in spec:
                        rv[key][spec_key] = spec[spec_key]
            else:
                rv[key] = self.policy[key]
        return rv

    def get_data_for_api_call(self) -> Tuple[Optional[str], str]:
        policy = self.get_output()
        name = policy[K8S_METADATA_FIELD][METADATA_NAME_FIELD]
        type = policy[K8S_METADATA_FIELD][METADATA_TYPE_FIELD]
        tags = policy[K8S_METADATA_FIELD].get(METADATA_TAGS_FIELD)
        uid = policy[K8S_METADATA_FIELD].get(METADATA_UID_FIELD)
        policy_selectors = {
            key: value
            for key, value in policy[K8S_SPEC_FIELD].items()
            if key.endswith("Selector")
        }
        data = {
            API_REQ_FIELD_NAME: name[:32],
            API_REQ_FIELD_POLICY: policy,
            API_REQ_FIELD_POL_SELECTORS: policy_selectors,
            API_REQ_FIELD_TYPE: type,
        }
        if tags:
            data[API_REQ_FIELD_TAGS] = tags
        else:
            data[API_REQ_FIELD_TAGS] = []
        return uid, data

    def add_response_action(self, resp_action: Dict):
        resp_actions: List[Dict] = self.policy[K8S_SPEC_FIELD][RESPONSE_FIELD][
            RESP_ACTIONS_FIELD
        ]
        resp_actions.append(resp_action)

    def disable(self):
        spec = self.policy[K8S_SPEC_FIELD]
        spec[ENABLED_FIELD] = False

    def enable(self):
        spec = self.policy[K8S_SPEC_FIELD]
        if ENABLED_FIELD in spec:
            del spec[ENABLED_FIELD]
