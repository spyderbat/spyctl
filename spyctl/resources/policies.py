import json
from typing import Dict, List, Optional, Tuple

import spyctl.spyctl_lib as lib

# For the Spyderbat API
API_REQ_FIELD_NAME = "name"
API_REQ_FIELD_POLICY = "policy"
API_REQ_FIELD_POL_SELECTORS = "policy_selectors"
API_REQ_FIELD_TAGS = "tags"
API_REQ_FIELD_TYPE = "type"
API_REQ_FIELD_UID = "uid"


class PolicyTypeError(Exception):
    pass


class InvalidPolicyArgument(Exception):
    pass


class Policy:
    def __init__(self, pol_type: str, fprint_or_pol: Dict = None) -> None:
        self.policy = {}
        if pol_type not in lib.POL_TYPES:
            raise PolicyTypeError(f"{pol_type} is not a valid policy type")
        if fprint_or_pol:
            req_keys = [lib.API_FIELD, lib.METADATA_FIELD, lib.SPEC_FIELD]
            for key in req_keys:
                if key not in fprint_or_pol:
                    raise InvalidPolicyArgument(
                        f"{key} field missing from input fingerprint or policy"
                    )
            self.policy[lib.API_FIELD] = fprint_or_pol[lib.API_FIELD]
            self.policy[lib.KIND_FIELD] = lib.POL_KIND
            self.policy[lib.METADATA_FIELD] = fprint_or_pol[lib.METADATA_FIELD]
            self.policy[lib.SPEC_FIELD] = fprint_or_pol[lib.SPEC_FIELD]
            self.spec.setdefault(
                lib.RESPONSE_FIELD, lib.RESPONSE_ACTION_TEMPLATE
            )
            if self.pol_type != pol_type:
                raise PolicyTypeError(
                    f"Policy type mismatch {self.pol_type} != {pol_type}"
                )
        else:
            self.policy.update(
                {
                    lib.API_FIELD: lib.API_VERSION,
                    lib.KIND_FIELD: lib.POL_KIND,
                    lib.METADATA_FIELD: lib.METADATA_TEMPLATES[pol_type],
                    lib.SPEC_FIELD: lib.SPEC_TEMPLATES[pol_type],
                }
            )

    @property
    def metadata(self) -> Dict:
        return self.policy[lib.METADATA_FIELD]

    @property
    def spec(self) -> Dict:
        return self.policy[lib.SPEC_FIELD]

    @property
    def pol_type(self) -> str:
        return self.metadata.get(lib.METADATA_TYPE_FIELD)

    def get_uid(self) -> Optional[str]:
        return self.policy[lib.METADATA_FIELD].get(lib.METADATA_UID_FIELD)

    def get_output(self):
        copy_fields = [
            lib.API_FIELD,
            lib.KIND_FIELD,
            lib.METADATA_FIELD,
            lib.SPEC_FIELD,
        ]
        spec_copy_fields = [
            lib.ENABLED_FIELD,
            lib.CONT_SELECTOR_FIELD,
            lib.SVC_SELECTOR_FIELD,
            lib.MACHINE_SELECTOR_FIELD,
            lib.POD_SELECTOR_FIELD,
            lib.NAMESPACE_SELECTOR_FIELD,
            lib.PROC_POLICY_FIELD,
            lib.NET_POLICY_FIELD,
            lib.RESPONSE_FIELD,
        ]
        rv = dict()
        for key in copy_fields:
            if key == lib.SPEC_FIELD:
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
        name = policy[lib.METADATA_FIELD][lib.METADATA_NAME_FIELD]
        type = policy[lib.METADATA_FIELD][lib.METADATA_TYPE_FIELD]
        tags = policy[lib.METADATA_FIELD].get(lib.METADATA_TAGS_FIELD)
        uid = policy[lib.METADATA_FIELD].get(lib.METADATA_UID_FIELD)
        policy_selectors = {
            key: value
            for key, value in policy[lib.SPEC_FIELD].items()
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
