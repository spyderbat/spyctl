from typing import Dict

from spyctl.fingerprints import Fingerprint, InvalidFingerprintError

S_CRIT = "critical"
S_HIGH = "high"
S_MED = "medium"
S_LOW = "low"
API_VERSION = "spyderbat/v1"
POL_KIND = "SpyderbatPolicy"
POL_TYPE_CONT = "container"
POL_TYPE_SVC = "service"
POL_TYPES = {POL_TYPE_SVC, POL_TYPE_CONT}
K8S_API_FIELD = "apiVersion"
K8S_KIND_FIELD = "kind"
K8S_METADATA_FIELD = "metadata"
K8S_SPEC_FIELD = "spec"
METADATA_NAME_FIELD = "name"
METADATA_NAME_TEMPLATE = "foobar-policy"
METADATA_TYPE_FIELD = "type"
CONT_SELECTOR_FIELD = "containerSelector"
SVC_SELECTOR_FIELD = "serviceSelector"
PROC_POLICY_FIELD = "processPolicy"
NET_POLICY_FIELD = "networkPolicy"
RESPONSE_FIELD = "response"
CONTAINER_SELECTOR_TEMPLATE = {
    "image": "foo",
    "imageID": "sha256:bar",
    "containerName": "/foobar"
}
SVC_SELECTOR_TEMPLATE = {
    "cgroup": "systemd:/system.slice/foobar.service"
}
PROCESS_POLICY_TEMPLATE = [
    {
        "name": "foo",
        "exe": [
            "/usr/bin/foo",
            "/usr/sbin/foo"
        ],
        "id": "foo_0",
        "euser": [
            "root"
        ],
        "children": [
            {
                "name": "bar",
                "exe": [
                    "/usr/bin/bar"
                ],
                "id": "bar_0"
            }
        ]
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
            "ports": [
                {
                    "protocol": "TCP",
                    "port": 1337
                }
            ],
            "processes": [
                "foo_0"
            ]
        }
    ],
    "egress": [
        {
            "to": [
                {
                    "dnsSelector": [
                        "foobar.com"
                    ]
                }
            ],
            "ports": [
                {
                    "protocol": "TCP",
                    "port": 1337
                }
            ],
            "processes": [
                "bar_0"
            ]
        }
    ]
}
RESPONSE_ACTION_TEMPLATE = {
    "default": {
        "severity": S_HIGH
    },
    "actions": []
}
METADATA_TEMPLATES = {
    POL_TYPE_CONT: {
        METADATA_NAME_FIELD: METADATA_NAME_TEMPLATE,
        METADATA_TYPE_FIELD: POL_TYPE_CONT
    },
    POL_TYPE_SVC: {
        METADATA_NAME_FIELD: METADATA_NAME_TEMPLATE,
        METADATA_TYPE_FIELD: POL_TYPE_SVC
    }
}
SPEC_TEMPLATES = {
    POL_TYPE_CONT: {
        CONT_SELECTOR_FIELD: CONTAINER_SELECTOR_TEMPLATE,
        PROC_POLICY_FIELD: PROCESS_POLICY_TEMPLATE,
        NET_POLICY_FIELD: NETWORK_POLICY_TEMPLATE,
        RESPONSE_FIELD: RESPONSE_ACTION_TEMPLATE
    },
    POL_TYPE_SVC: {
        SVC_SELECTOR_FIELD: SVC_SELECTOR_TEMPLATE,
        PROC_POLICY_FIELD: PROCESS_POLICY_TEMPLATE,
        NET_POLICY_FIELD: NETWORK_POLICY_TEMPLATE,
        RESPONSE_FIELD: RESPONSE_ACTION_TEMPLATE
    }
}


class PolicyTypeError(Exception): ...


class Policy:
    def __init__(self, pol_type: str, fingerprint: Dict = None) -> None:
        self.policy = {}
        if pol_type not in POL_TYPES:
            raise PolicyTypeError(f"{pol_type} is not a valid policy type")
        if fingerprint:
            req_keys = [K8S_API_FIELD, K8S_METADATA_FIELD, K8S_SPEC_FIELD]
            for key in req_keys:
                if key not in fingerprint:
                    raise InvalidFingerprintError(
                            f"{key} field missing from fingerprint")
            self.policy[K8S_API_FIELD] = fingerprint[K8S_API_FIELD]
            self.policy[K8S_KIND_FIELD] = POL_KIND
            self.policy[K8S_METADATA_FIELD] = \
                fingerprint[K8S_METADATA_FIELD]
            self.policy[K8S_SPEC_FIELD] = fingerprint[K8S_SPEC_FIELD]
            self.spec.setdefault('response', RESPONSE_ACTION_TEMPLATE)
            if self.pol_type != pol_type:
                raise PolicyTypeError(
                        f"Policy type mismatch {self.pol_type} != {pol_type}")
        else:
            self.policy.update({
                K8S_API_FIELD: API_VERSION,
                K8S_KIND_FIELD: POL_KIND,
                K8S_METADATA_FIELD: METADATA_TEMPLATES[pol_type],
                K8S_SPEC_FIELD: SPEC_TEMPLATES[pol_type]
            })

    @property
    def metadata(self) -> Dict:
        return self.policy['metadata']

    @property
    def spec(self) -> Dict:
        return self.policy['spec']

    @property
    def pol_type(self) -> str:
        return self.metadata.get('type')

    def get_output(self):
        copy_fields = [
            K8S_API_FIELD, K8S_KIND_FIELD, K8S_METADATA_FIELD, K8S_SPEC_FIELD]
        rv = dict()
        for key in copy_fields:
            rv[key] = self.policy[key]
        return rv
