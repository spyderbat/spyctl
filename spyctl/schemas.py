import ipaddress as ipaddr
from typing import Dict, List
from base64 import b64decode

from schema import And, Optional, Or, Schema, SchemaError, Use

import spyctl.spyctl_lib as lib


def valid_object(data: Dict, verbose=True) -> bool:
    kind = data.get(lib.KIND_FIELD)
    if kind not in KIND_TO_SCHEMA:
        lib.err_exit(
            f"Unable to validate {kind!r}, no schema exists for objects of"
            " that type."
        )
    try:
        KIND_TO_SCHEMA[kind].validate(data)
    except SchemaError as e:
        if verbose:
            output = []
            found_key_msg = False
            for msg in reversed(e.autos):
                if not msg:
                    continue
                msg: str = msg
                if not found_key_msg and not msg.startswith("Key"):
                    output.append(msg)
                elif msg.startswith("Key"):
                    found_key_msg = True
                    output.append(msg)
            output = "\n".join(reversed(output))
            lib.try_log(output, is_warning=True)
        return False
    return True


def valid_context(context_data: Dict, verbose=True):
    try:
        context_schema.validate(context_data)
    except SchemaError as e:
        if verbose:
            output = []
            found_key_msg = False
            for msg in reversed(e.autos):
                if not msg:
                    continue
                msg: str = msg
                if not found_key_msg and not msg.startswith("Key"):
                    output.append(msg)
                elif msg.startswith("Key"):
                    found_key_msg = True
                    output.append(msg)
            output = "\n".join(reversed(output))
            lib.try_log(output, is_warning=True)
        return False
    return True


class PortsSchema(Schema):
    def validate(self, data, **kwargs):
        val_schema = Schema(
            self.schema,
            self._error,
            self._ignore_extra_keys,
            self._name,
            self._description,
            self.as_reference,
        )
        rv = val_schema.validate(data, **kwargs)
        e = self._error
        for port in data:
            endport = port.get(lib.ENDPORT_FIELD)
            if endport is not None:
                if endport < port[lib.PORT_FIELD]:
                    message = (
                        f"{lib.ENDPORT_FIELD} {endport} should be greater than"
                        f" or equal to {lib.PORT_FIELD} {port[lib.PORT_FIELD]}"
                    )
                    raise SchemaError(message, e.format(port) if e else None)
        return rv


class IP_Block_Schema(Schema):
    def validate(self, data, **kwargs):
        val_schema = Schema(
            self.schema,
            self._error,
            self._ignore_extra_keys,
            self._name,
            self._description,
            self.as_reference,
        )
        rv = val_schema.validate(data, **kwargs)
        e = self._error
        if lib.EXCEPT_FIELD not in data[lib.IP_BLOCK_FIELD]:
            return rv
        cidr = data[lib.IP_BLOCK_FIELD][lib.CIDR_FIELD]
        try:
            network = ipaddr.IPv4Network(cidr)
        except ipaddr.AddressValueError:
            network = ipaddr.IPv6Network(cidr)

        for except_cidr in data[lib.IP_BLOCK_FIELD][lib.EXCEPT_FIELD]:
            try:
                except_net = ipaddr.IPv4Address(except_cidr)
            except ipaddr.AddressValueError:
                except_net = ipaddr.IPv6Address(except_cidr)
            try:
                if not network.supernet_of(except_net):
                    message = (
                        f"Except CIDR {except_cidr} must be a subnet of {cidr}"
                    )
                    raise SchemaError(message, e.format(data) if e else None)
            except TypeError:
                message = (
                    f"{except_cidr} and {cidr} must be the same IP version"
                )
                raise SchemaError(message, e.format(data) if e else None)
        return rv


class Spec_Schema(Schema):
    def __init__(
        self,
        schema,
        error=None,
        ignore_extra_keys=False,
        name=None,
        description=None,
        as_reference=False,
    ):
        self.process_ids = set()
        super().__init__(
            schema, error, ignore_extra_keys, name, description, as_reference
        )

    def validate(self, data, **kwargs):
        val_schema = Schema(
            self.schema,
            self._error,
            self._ignore_extra_keys,
            self._name,
            self._description,
            self.as_reference,
        )
        rv = val_schema.validate(data, **kwargs)
        process_list = data[lib.PROC_POLICY_FIELD]
        self.__validate_unique_ids(process_list)
        ingress_list = data[lib.NET_POLICY_FIELD][lib.INGRESS_FIELD]
        self.__validate_network_processes(ingress_list)
        egress_list = data[lib.NET_POLICY_FIELD][lib.EGRESS_FIELD]
        self.__validate_network_processes(egress_list)
        self.__reset_proc_ids()
        return rv

    def __reset_proc_ids(self):
        self.process_ids = set()

    def __validate_unique_ids(self, process_list: List[Dict]):
        e = self._error
        for process_node in process_list:
            id = process_node[lib.ID_FIELD]
            if id in self.process_ids:
                message = (
                    f"Duplicate process ID detected {id}. All IDs in"
                    f" the {lib.PROC_POLICY_FIELD} must be unique"
                )
                raise SchemaError(
                    message, e.format(process_list) if e else None
                )
            else:
                self.process_ids.add(id)
                if lib.CHILDREN_FIELD in process_node:
                    self.__validate_unique_ids(
                        process_node[lib.CHILDREN_FIELD]
                    )

    def __validate_network_processes(self, net_node_list: List[Dict]):
        e = self._error
        for net_node in net_node_list:
            processes = net_node[lib.PROCESSES_FIELD]
            for proc_id in processes:
                if proc_id not in self.process_ids:
                    message = (
                        f"Process ID {proc_id!r} in {lib.NET_POLICY_FIELD} not"
                        f" found in {lib.PROC_POLICY_FIELD}."
                    )
                    raise SchemaError(
                        message, e.format(net_node) if e else None
                    )


class ResponseActionsSchema(Schema):
    def validate(self, data, **kwargs):
        val_schema = Schema(
            self.schema,
            self._error,
            self._ignore_extra_keys,
            self._name,
            self._description,
            self.as_reference,
        )
        rv = val_schema.validate(data, **kwargs)
        e = self._error
        for action_dict in data:
            action = next(iter(action_dict))
            found_selector = False
            for values_dict in action_dict.values():
                for k, v in values_dict.items():
                    if k in lib.SELECTOR_FIELDS:
                        found_selector = True
            if not found_selector:
                message = (
                    f"Action {action} missing a selector. Do you want this"
                    " to be a default action?"
                )
                raise SchemaError(message, e.format(data) if e else None)
        return rv


class SpyderbatObjSchema(Schema):
    """A base schema class for fingerprints, baselines, and policies"""

    def validate(self, data, **kwargs):
        e = self._error
        val_schema = Schema(
            self.schema,
            self._error,
            self._ignore_extra_keys,
            self._name,
            self._description,
            self.as_reference,
        )
        rv = val_schema.validate(data, **kwargs)
        type = data[lib.METADATA_FIELD][lib.METADATA_TYPE_FIELD]
        spec = data[lib.SPEC_FIELD]
        if type == lib.POL_TYPE_CONT and lib.CONT_SELECTOR_FIELD not in spec:
            message = (
                f"Missing {lib.CONT_SELECTOR_FIELD} in {lib.SPEC_FIELD} field"
            )
            raise SchemaError(message, e.format(spec) if e else None)
        elif type == lib.POL_TYPE_SVC and lib.SVC_SELECTOR_FIELD not in spec:
            message = (
                f"Missing {lib.SVC_SELECTOR_FIELD} in {lib.SPEC_FIELD} field"
            )
            raise SchemaError(message, e.format(spec) if e else None)
        return rv


class APISecretSchema(Schema):
    def validate(self, data, **kwargs):
        val_schema = Schema(
            self.schema,
            self._error,
            self._ignore_extra_keys,
            self._name,
            self._description,
            self.as_reference,
        )
        rv = val_schema.validate(data, **kwargs)
        self.__validate_fields(data)
        return rv

    def __validate_fields(self, data: Dict[str, Dict]) -> bool:
        e = self._error
        api_key = None
        api_url = None
        base64_data: Dict[str, str] = data.get(lib.DATA_FIELD)
        if base64_data:
            b64_api_key = base64_data.get(lib.API_KEY_FIELD)
            if b64_api_key:
                api_key = b64decode(b64_api_key).decode("ascii")
            b64_api_url = base64_data.get(lib.API_URL_FIELD)
            if b64_api_url:
                api_url = b64decode(b64_api_url).decode("ascii")
        string_data: Dict[str, str] = data.get(lib.STRING_DATA_FIELD)
        if string_data:
            if not api_key:
                api_key = string_data.get(lib.API_KEY_FIELD)
            if not api_url:
                api_url = string_data.get(lib.API_URL_FIELD)
        missing = []
        if not api_key:
            missing.append(lib.API_KEY_FIELD)
        if not api_url:
            missing.append(lib.API_URL_FIELD)
        if len(missing) > 0:
            message = (
                f"Missing {', '.join(missing)} field(s)"
                f" in {lib.STRING_DATA_FIELD!r} field."
            )
            raise SchemaError(message, e.format(data) if e else None)


config_schema = Schema(
    {
        lib.API_FIELD: lib.API_VERSION,
        lib.KIND_FIELD: lib.CONFIG_KIND,
        lib.CONTEXTS_FIELD: [dict],
        lib.CURR_CONTEXT_FIELD: str,
    }
)

context_schema = Schema(
    {
        lib.CONTEXT_NAME_FIELD: str,
        lib.SECRET_FIELD: str,
        lib.CONTEXT_FIELD: {
            lib.ORG_FIELD: str,
            Optional(lib.CLUSTER_FIELD): Or(str, [str]),
            Optional(lib.MACHINES_FIELD): Or(str, [str]),
            Optional(lib.POD_FIELD): Or(str, [str]),
            Optional(lib.NAMESPACE_FIELD): Or(str, [str]),
            Optional(lib.CGROUP_FIELD): Or(str, [str]),
            Optional(lib.CONT_NAME_FIELD): Or(str, [str]),
            Optional(lib.CONT_ID_FIELD): Or(str, [str]),
            Optional(lib.IMAGE_FIELD): Or(str, [str]),
            Optional(lib.IMAGEID_FIELD): Or(str, [str]),
        },
    }
)

secret_schema = APISecretSchema(
    {
        lib.API_FIELD: lib.API_VERSION,
        lib.KIND_FIELD: lib.SECRET_KIND,
        lib.METADATA_FIELD: {
            lib.METADATA_NAME_FIELD: str,
            Optional(lib.METADATA_CREATE_TIME): Or(float, int),
        },
        Optional(lib.DATA_FIELD): {Optional(str): str},
        Optional(lib.STRING_DATA_FIELD): {Optional(str): str},
    }
)

ports_schema = PortsSchema(
    [
        {
            lib.PORT_FIELD: And(Use(int), lambda n: 0 <= n <= 65535),
            lib.PROTO_FIELD: And(
                "TCP", error="Only TCP ports are supported at this time"
            ),
            Optional(lib.ENDPORT_FIELD): And(
                Use(int), lambda n: 0 <= n <= 65535
            ),
        }
    ]
)


def validate_process_schema(data: list):
    return child_processes_schema.validate(data)


child_processes_schema = Schema(
    [
        {
            lib.NAME_FIELD: And(str, lambda x: len(x) > 0),
            lib.EXE_FIELD: [And(str, lambda x: len(x) > 0)],
            lib.ID_FIELD: And(str, lambda x: len(x) > 0),
            Optional(lib.EUSER_FIELD): And([str], lambda x: len(x) > 0),
            Optional(lib.LISTENING_SOCKETS): ports_schema,
            Optional(lib.CHILDREN_FIELD): validate_process_schema,
        }
    ]
)

process_policy_schema = Schema(
    [
        {
            lib.NAME_FIELD: And(str, lambda x: len(x) > 0),
            lib.EXE_FIELD: [And(str, lambda x: len(x) > 0)],
            lib.ID_FIELD: And(str, lambda x: len(x) > 0),
            lib.EUSER_FIELD: [And(str, lambda x: len(x) > 0)],
            Optional(lib.LISTENING_SOCKETS): ports_schema,
            Optional(lib.CHILDREN_FIELD): child_processes_schema,
        }
    ]
)

ip_block_schema = IP_Block_Schema(
    {
        lib.IP_BLOCK_FIELD: {
            lib.CIDR_FIELD: Or(
                Use(ipaddr.IPv4Network), Use(ipaddr.IPv6Network)
            ),
            Optional(lib.EXCEPT_FIELD): [
                Or(Use(ipaddr.IPv4Network), Use(ipaddr.IPv6Network))
            ],
        }
    }
)

dns_schema = Schema({lib.DNS_SELECTOR_FIELD: [And(str, lambda x: len(x) > 0)]})

ingress_schema = Schema(
    [
        {
            lib.FROM_FIELD: [Or(dns_schema, ip_block_schema)],
            lib.PROCESSES_FIELD: [And(str, lambda x: len(x) > 0)],
            lib.PORTS_FIELD: ports_schema,
        }
    ]
)

egress_schema = Schema(
    [
        {
            lib.TO_FIELD: [Or(dns_schema, ip_block_schema)],
            lib.PROCESSES_FIELD: [And(str, lambda x: len(x) > 0)],
            lib.PORTS_FIELD: ports_schema,
        }
    ]
)

svc_selector_schema = {lib.CGROUP_FIELD: And(str, lambda x: len(x) > 0)}

container_selector_schema = {
    Or(
        lib.IMAGE_FIELD,
        lib.IMAGEID_FIELD,
        lib.CONT_NAME_FIELD,
        lib.CONT_ID_FIELD,
    ): And(str, lambda x: len(x) > 0)
}

# TODO: Update machine selector
machine_selector_schema = {Optional(str): str}

match_labels_schema = {lib.MATCH_LABELS_FIELD: {str: str}}

pod_selector_schema = match_labels_schema
namespace_selector_schema = match_labels_schema

all_selectors_schema = {
    # Optional(lib.CONT_SELECTOR_FIELD): container_selector_schema,
    # Optional(lib.SVC_SELECTOR_FIELD): svc_selector_schema,
    # Optional(lib.MACHINE_SELECTOR_FIELD): machine_selector_schema,
    # Optional(lib.POD_SELECTOR_FIELD): pod_selector_schema,
    # Optional(lib.NAMESPACE_SELECTOR_FIELD): namespace_selector_schema,
}

SELECTOR_TO_SCHEMA_MAP = {
    lib.CONT_SELECTOR_FIELD: container_selector_schema,
    lib.SVC_SELECTOR_FIELD: svc_selector_schema,
    lib.MACHINE_SELECTOR_FIELD: machine_selector_schema,
    lib.NAMESPACE_SELECTOR_FIELD: pod_selector_schema,
    lib.POD_SELECTOR_FIELD: namespace_selector_schema,
}

for selector_field in lib.SELECTOR_FIELDS:
    all_selectors_schema[Optional(selector_field)] = SELECTOR_TO_SCHEMA_MAP[
        selector_field
    ]

baseline_spec_schema = Spec_Schema(
    {
        Optional(lib.ENABLED_FIELD): bool,
        **all_selectors_schema,
        lib.PROC_POLICY_FIELD: process_policy_schema,
        lib.NET_POLICY_FIELD: {
            lib.INGRESS_FIELD: ingress_schema,
            lib.EGRESS_FIELD: egress_schema,
        },
    }
)

make_redflag_schema = {
    Optional(lib.ENABLED_FIELD): bool,
    Optional(lib.FLAG_CONTENT): And(str, lambda s: len(s) < 350),
    Optional(lib.FLAG_IMPACT): And(str, lambda s: len(s) < 100),
    lib.FLAG_SEVERITY: Or(*lib.ALLOWED_SEVERITIES),
}
make_opsflag_schema = {
    Optional(lib.ENABLED_FIELD): bool,
    Optional(lib.FLAG_CONTENT): And(str, lambda s: len(s) < 350),
    Optional(lib.FLAG_DESCRIPTION): And(str, lambda s: len(s) < 350),
    lib.FLAG_SEVERITY: Or(*lib.ALLOWED_SEVERITIES),
}
webhook_schema = {
    Optional(lib.ENABLED_FIELD): bool,
    lib.URL_DESTINATION_FIELD: And(str, lambda s: len(s) < 2048),
    lib.TEMPLATE_FIELD: Or(*lib.ALLOWED_TEMPLATES),
}
agent_kill_pod_schema = {
    Optional(lib.ENABLED_FIELD): bool,
    **all_selectors_schema,
}
agent_kill_proc_schema = {
    Optional(lib.ENABLED_FIELD): bool,
    **all_selectors_schema,
}
agent_kill_proc_group_schema = {
    Optional(lib.ENABLED_FIELD): bool,
    **all_selectors_schema,
}

default_response_actions_schema = And(
    [
        Optional(
            Or(
                {lib.ACTION_MAKE_REDFLAG: make_redflag_schema},
                {lib.ACTION_MAKE_OPSFLAG: make_opsflag_schema},
                {lib.ACTION_WEBHOOK: webhook_schema},
            ),
        )
    ],
    lambda d: len(d) < 4,
)
response_actions_schema = ResponseActionsSchema(
    [
        Optional(
            Or(
                {
                    lib.ACTION_MAKE_REDFLAG: {
                        **make_redflag_schema,
                        **all_selectors_schema,
                    }
                },
                {
                    lib.ACTION_MAKE_OPSFLAG: {
                        **make_opsflag_schema,
                        **all_selectors_schema,
                    }
                },
                {
                    lib.ACTION_WEBHOOK: {
                        **webhook_schema,
                        **all_selectors_schema,
                    }
                },
                {lib.ACTION_KILL_POD: agent_kill_pod_schema},
                {lib.ACTION_KILL_PROC: agent_kill_proc_schema},
                {lib.ACTION_KILL_PROC_GRP: agent_kill_proc_group_schema},
            )
        )
    ]
)

# TODO: Update response actions format
# TODO: Create schemas for various response actions
policy_spec_schema = Spec_Schema(
    {
        Optional(lib.ENABLED_FIELD): bool,
        lib.PROC_POLICY_FIELD: process_policy_schema,
        **all_selectors_schema,
        lib.NET_POLICY_FIELD: {
            lib.INGRESS_FIELD: ingress_schema,
            lib.EGRESS_FIELD: egress_schema,
        },
        lib.RESPONSE_FIELD: {
            lib.RESP_DEFAULT_FIELD: default_response_actions_schema,
            lib.RESP_ACTIONS_FIELD: response_actions_schema,
        },
    }
)

# TODO: Add type to fingerprint group metadata
fprint_group_metadata_schema = Schema(
    {
        Optional(lib.IMAGE_FIELD): str,
        Optional(lib.IMAGEID_FIELD): str,
        Optional(lib.CGROUP_FIELD): str,
        Optional(lib.FIRST_TIMESTAMP_FIELD): Or(int, float),
        Optional(lib.LATEST_TIMESTAMP_FIELD): Or(int, float),
    },
    ignore_extra_keys=True,
)

fprint_metadata_schema = Schema(
    {
        lib.METADATA_NAME_FIELD: And(str, lambda x: len(x) > 0),
        lib.METADATA_TYPE_FIELD: Or(
            lib.POL_TYPE_CONT,
            lib.POL_TYPE_SVC,
            error=(
                f"Fingerprint type must be {lib.POL_TYPE_CONT} or"
                f" {lib.POL_TYPE_SVC}"
            ),
        ),
        Optional(lib.FIRST_TIMESTAMP_FIELD): Or(int, float),
        Optional(lib.LATEST_TIMESTAMP_FIELD): Or(
            int, float, lib.NOT_AVAILABLE
        ),
    },
    ignore_extra_keys=True,
)

baseline_metadata_schema = Schema(
    {
        lib.METADATA_NAME_FIELD: And(str, lambda x: len(x) > 0),
        lib.METADATA_TYPE_FIELD: Or(
            lib.POL_TYPE_CONT,
            lib.POL_TYPE_SVC,
            error=(
                f"Fingerprint type must be {lib.POL_TYPE_CONT} or"
                f" {lib.POL_TYPE_SVC}"
            ),
        ),
        Optional(lib.LATEST_TIMESTAMP_FIELD): Or(
            int, float, lib.NOT_AVAILABLE
        ),
    },
)

policy_metadata_schema = Schema(
    {
        lib.METADATA_NAME_FIELD: And(str, lambda x: len(x) > 0),
        lib.METADATA_TYPE_FIELD: Or(
            lib.POL_TYPE_CONT,
            lib.POL_TYPE_SVC,
            error=(
                f"Fingerprint type must be {lib.POL_TYPE_CONT} or"
                f" {lib.POL_TYPE_SVC}"
            ),
        ),
        Optional(lib.METADATA_CREATE_TIME): Or(str, int, float),
        Optional(lib.LATEST_TIMESTAMP_FIELD): Or(
            int, float, lib.NOT_AVAILABLE
        ),
        Optional(lib.METADATA_UID_FIELD): str,
    },
)

fprint_schema = SpyderbatObjSchema(
    {
        lib.API_FIELD: lib.API_VERSION,
        lib.KIND_FIELD: lib.FPRINT_KIND,
        lib.METADATA_FIELD: fprint_metadata_schema,
        lib.SPEC_FIELD: baseline_spec_schema,
    }
)

fprint_group_schema = Schema(
    {
        lib.API_FIELD: lib.API_VERSION,
        lib.KIND_FIELD: lib.FPRINT_GROUP_KIND,
        lib.METADATA_FIELD: fprint_group_metadata_schema,
        lib.DATA_FIELD: {
            lib.FPRINT_GRP_FINGERPRINTS_FIELD: [fprint_schema],
            Optional(lib.FPRINT_GRP_CONT_NAMES_FIELD): [str],
            Optional(lib.FPRINT_GRP_CONT_NAMES_FIELD): [str],
            Optional(lib.FPRINT_GRP_MACHINES_FIELD): [str],
            Optional(lib.FPRINT_GRP_CONT_IDS_FIELD): [str],
        },
    }
)

baseline_schema = SpyderbatObjSchema(
    {
        lib.API_FIELD: lib.API_VERSION,
        lib.KIND_FIELD: lib.BASELINE_KIND,
        lib.METADATA_FIELD: baseline_metadata_schema,
        lib.SPEC_FIELD: baseline_spec_schema,
    }
)

policy_schema = SpyderbatObjSchema(
    {
        lib.API_FIELD: lib.API_VERSION,
        lib.KIND_FIELD: lib.POL_KIND,
        lib.METADATA_FIELD: policy_metadata_schema,
        lib.SPEC_FIELD: policy_spec_schema,
    }
)

KIND_TO_SCHEMA: Dict[str, Schema] = {
    lib.BASELINE_KIND: baseline_schema,
    lib.FPRINT_KIND: fprint_schema,
    lib.FPRINT_GROUP_KIND: fprint_group_schema,
    lib.POL_KIND: policy_schema,
    lib.CONFIG_KIND: config_schema,
    lib.SECRET_KIND: secret_schema,
}
