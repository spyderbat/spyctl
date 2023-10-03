from __future__ import annotations

import ipaddress
from typing import Any, Dict, List, Optional, Union
from typing_extensions import Literal

from pydantic import (
    BaseModel,
    Extra,
    Field,
    IPvAnyNetwork,
    ValidationError,
    root_validator,
    validator,
)

import spyctl.spyctl_lib as lib


def valid_object(data: Dict, verbose=True, allow_obj_list=True) -> bool:
    kind = data.get(lib.KIND_FIELD)
    if kind not in KIND_TO_SCHEMA:
        if lib.ITEMS_FIELD not in data:
            lib.err_exit(
                f"Unable to validate {kind!r}, no schema exists for objects of"
                " that type."
            )
        elif not allow_obj_list:
            lib.err_exit("Nested item lists are not allowed.")
        try:
            GuardianObjectListModel(**data)
        except ValidationError as e:
            if verbose:
                lib.try_log(str(e), is_warning=True)
            return False
        for item in data[lib.ITEMS_FIELD]:
            if not valid_object(item, allow_obj_list=False):
                return False
        return True
    if kind == lib.POL_KIND:
        type = data.get(lib.METADATA_FIELD, {}).get(lib.METADATA_TYPE_FIELD)
        if type == lib.POL_TYPE_TRACE:
            kind = (kind, type)
    try:
        KIND_TO_SCHEMA[kind](**data)
    except ValidationError as e:
        if verbose:
            lib.try_log(str(e), is_warning=True)
        return False
    return True


def valid_context(context_data: Dict, verbose=True):
    try:
        ContextsModel(**context_data)
    except ValidationError as e:
        if verbose:
            lib.try_log(str(e), is_warning=True)
        return False
    return True


def handle_show_schema(kind: str) -> str:
    object = KIND_TO_SCHEMA.get(kind)
    return object.schema_json()


__PROC_IDS = {}

# -----------------------------------------------------------------------------
# Selectors -------------------------------------------------------------------
# -----------------------------------------------------------------------------


class MatchLabelsModel(BaseModel):
    match_labels: Dict[str, str] = Field(alias=lib.MATCH_LABELS_FIELD)

    class Config:
        extra = Extra.forbid


class ContainerSelectorModel(BaseModel):
    image: Optional[str] = Field(alias=lib.IMAGE_FIELD)
    image_id: Optional[str] = Field(alias=lib.IMAGEID_FIELD)
    container_name: Optional[str] = Field(alias=lib.CONTAINER_NAME_FIELD)
    container_id: Optional[str] = Field(alias=lib.CONTAINER_ID_FIELD)

    @root_validator(skip_on_failure=True)
    def ensure_one_field(cls, values: Dict):
        if not any([value for value in values.values()]):
            raise ValueError("")
        return values

    class Config:
        extra = Extra.forbid


class ServiceSelectorModel(BaseModel):
    cgroup: str = Field(alias=lib.CGROUP_FIELD)

    class Config:
        extra = Extra.forbid


class MachineSelectorModel(BaseModel):
    hostname: str = Field(alias=lib.HOSTNAME_FIELD)

    class Config:
        extra = Extra.forbid


class NamespaceSelectorModel(MatchLabelsModel):
    pass


class PodSelectorModel(MatchLabelsModel):
    pass


class TraceSelectorModel(BaseModel):
    trigger_class: Optional[List[str]] = Field(alias=lib.TRIGGER_CLASS_FIELD)
    trigger_ancestor: Optional[List[str]] = Field(
        alias=lib.TRIGGER_ANCESTORS_FIELD
    )

    class Config:
        extra = Extra.forbid


class UserSelectorModel(BaseModel):
    users: Optional[List[str]] = Field(alias=lib.USERS_FIELD)
    interactive_users: Optional[List[str]] = Field(
        alias=lib.INTERACTIVE_USERS_FIELD
    )
    non_interactive_users: Optional[List[str]] = Field(
        alias=lib.NON_INTERACTIVE_USERS_FIELD
    )

    class Config:
        extra = Extra.forbid


class ProcessSelectorModel(BaseModel):
    name: Optional[List[str]] = Field(alias=lib.NAME_FIELD, min_items=1)
    exe: Optional[List[str]] = Field(alias=lib.EXE_FIELD, min_items=1)
    euser: Optional[List[str]] = Field(alias=lib.EUSER_FIELD, min_items=1)
    interactive: Optional[bool] = Field(alias=lib.INTERACTIVE_FIELD)

    @root_validator(skip_on_failure=True)
    def ensure_one_field(cls, values: Dict):
        set_count = 0
        for v in values.values():
            if v is not None:
                set_count += 1
        if set_count == 0:
            raise ValueError("At least one key, value pair expected")
        return values

    class Config:
        extra = Extra.forbid


# -----------------------------------------------------------------------------
# Guardian Models -------------------------------------------------------------
# -----------------------------------------------------------------------------


# This is a reused validator ensuring that the objects have a required selector
def validate_selectors(_, values):
    type = getattr(values["metadata"], "type", "")
    if type == lib.POL_TYPE_CONT:
        s_val = getattr(values["spec"], "container_selector", None)
        if not s_val:
            raise ValueError(
                f"Type is '{lib.POL_TYPE_CONT}' and no "
                f"'{lib.CONT_SELECTOR_FIELD}' found in {lib.SPEC_FIELD}"
            )
    else:
        s_val = getattr(values["spec"], "service_selector", None)
        if not s_val:
            raise ValueError(
                f"Type is '{lib.POL_TYPE_SVC}' and no "
                f"'{lib.SVC_SELECTOR_FIELD}' found in {lib.SPEC_FIELD}"
            )
    return values


class GuardianSelectorsModel(BaseModel):
    container_selector: Optional[ContainerSelectorModel] = Field(
        alias=lib.CONT_SELECTOR_FIELD
    )
    service_selector: Optional[ServiceSelectorModel] = Field(
        alias=lib.SVC_SELECTOR_FIELD
    )
    machine_selector: Optional[MachineSelectorModel] = Field(
        alias=lib.MACHINE_SELECTOR_FIELD
    )
    namespace_selector: Optional[NamespaceSelectorModel] = Field(
        alias=lib.NAMESPACE_SELECTOR_FIELD
    )
    pod_selector: Optional[PodSelectorModel] = Field(
        alias=lib.POD_SELECTOR_FIELD
    )

    class Config:
        extra = Extra.forbid


class ActionSelectorsModel(BaseModel):
    namespace_selector: Optional[NamespaceSelectorModel] = Field(
        alias=lib.NAMESPACE_SELECTOR_FIELD
    )
    pod_selector: Optional[PodSelectorModel] = Field(
        alias=lib.POD_SELECTOR_FIELD
    )
    process_selector: Optional[ProcessSelectorModel] = Field(
        alias=lib.PROCESS_SELECTOR_FIELD
    )

    class Config:
        extra = Extra.forbid


class GuardianSpecOptionsModel(BaseModel):
    disable_processes: Optional[
        Literal[tuple(lib.DISABLE_PROCS_STRINGS)]  # type: ignore
    ] = Field(alias=lib.DISABLE_PROCS_FIELD)
    disable_connections: Optional[
        Literal[tuple(lib.DISABLE_CONNS_STRINGS)]  # type: ignore
    ] = Field(alias=lib.DISABLE_CONNS_FIELD)
    disable_private_conns: Optional[
        Literal[tuple(lib.DISABLE_CONNS_STRINGS)]  # type: ignore
    ] = Field(alias=lib.DISABLE_PR_CONNS_FIELD)
    disable_public_conns: Optional[
        Literal[tuple(lib.DISABLE_CONNS_STRINGS)]  # type: ignore
    ] = Field(alias=lib.DISABLE_PU_CONNS_FIELD)


# Network Models --------------------------------------------------------------


class DnsBlockModel(BaseModel):
    dns_selector: List[str] = Field(alias=lib.DNS_SELECTOR_FIELD)

    class Config:
        extra = Extra.forbid


class CIDRModel(BaseModel):
    cidr: IPvAnyNetwork = Field(alias=lib.CIDR_FIELD)
    except_cidr: Optional[List[IPvAnyNetwork]] = Field(
        alias=lib.EXCEPT_FIELD, max_items=10
    )

    @root_validator(skip_on_failure=True)
    def validate_except_within_cidr(cls, values):
        cidr = values["cidr"]
        try:
            cidr_net = ipaddress.IPv4Network(cidr)
        except ipaddress.AddressValueError:
            cidr_net = ipaddress.IPv6Network(cidr)
        net_type = type(cidr_net)
        if "except_cidr" in values and values["except_cidr"]:
            for e_cidr in values["except_cidr"]:
                try:
                    e_net = ipaddress.IPv4Network(e_cidr)
                except ipaddress.AddressValueError:
                    e_net = ipaddress.IPv6Network(e_cidr)
                if net_type != type(e_net):
                    raise ValueError("Network types are not the same")
                if not cidr_net.supernet_of(e_net):
                    raise ValueError(
                        f"'{e_net}' is not a subnet of '{cidr_net}'"
                    )
        return values

    class Config:
        extra = Extra.forbid


class IpBlockModel(BaseModel):
    ip_block: CIDRModel = Field(alias=lib.IP_BLOCK_FIELD)

    class Config:
        extra = Extra.forbid


class PortsModel(BaseModel):
    port: int = Field(alias=lib.PORT_FIELD, ge=0, le=65535)
    proto: Literal["UDP", "TCP"] = Field(alias=lib.PROTO_FIELD)
    endport: Optional[int] = Field(alias=lib.ENDPORT_FIELD, ge=0, le=66535)

    @root_validator(skip_on_failure=True)
    def endport_ge_port(cls, values):
        endport = values.get("endport")
        if endport is not None and endport < values["port"]:
            raise ValueError(
                f"{lib.ENDPORT_FIELD} must be greater than or equal to"
                f" {lib.PORT_FIELD}"
            )
        return values

    class Config:
        extra = Extra.forbid


class IngressNodeModel(BaseModel):
    from_field: List[Union[DnsBlockModel, IpBlockModel]] = Field(
        alias=lib.FROM_FIELD, min_items=1
    )
    processes: Optional[List[str]] = Field(
        alias=lib.PROCESSES_FIELD, min_items=1
    )
    ports: List[PortsModel] = Field(alias=lib.PORTS_FIELD, min_items=1)

    @validator("processes")
    def validate_proc_ids(cls, v):
        if not v:
            return v
        bad = []
        for proc_id in v:
            if not in_proc_ids(proc_id):
                bad.append(proc_id)
        if bad:
            raise ValueError(f"No process found with id(s) '{bad}'.")
        return v

    class Config:
        smart_union = True
        extra = Extra.forbid


class EgressNodeModel(BaseModel):
    to: List[Union[DnsBlockModel, IpBlockModel]] = Field(
        alias=lib.TO_FIELD, min_items=1
    )
    processes: Optional[List[str]] = Field(
        alias=lib.PROCESSES_FIELD, min_items=1
    )
    ports: List[PortsModel] = Field(alias=lib.PORTS_FIELD, min_items=1)

    @validator("processes")
    def validate_proc_ids(cls, v):
        if not v:
            return v
        bad = []
        for proc_id in v:
            if not in_proc_ids(proc_id):
                bad.append(proc_id)
        if bad:
            raise ValueError(f"No process found with id(s) '{bad}'.")
        return v

    class Config:
        smart_union = True
        extra = Extra.forbid


class NetworkPolicyModel(BaseModel):
    ingress: List[IngressNodeModel] = Field(alias=lib.INGRESS_FIELD)
    egress: List[EgressNodeModel] = Field(alias=lib.EGRESS_FIELD)


class DeviationNetworkPolicyModel(BaseModel):
    ingress: Optional[List[IngressNodeModel]] = Field(alias=lib.INGRESS_FIELD)
    egress: Optional[List[EgressNodeModel]] = Field(alias=lib.EGRESS_FIELD)


# Process Models --------------------------------------------------------------


class SimpleProcessNodeModel(BaseModel):
    name: str = Field(alias=lib.NAME_FIELD)
    exe: List[str] = Field(alias=lib.EXE_FIELD)
    euser: Optional[List[str]] = Field(alias=lib.EUSER_FIELD)


class ProcessNodeModel(SimpleProcessNodeModel):
    id: str = Field(alias=lib.ID_FIELD)
    listening_sockets: Optional[List[PortsModel]] = Field(
        alias=lib.LISTENING_SOCKETS
    )
    children: Optional[List[ProcessNodeModel]] = Field(
        alias=lib.CHILDREN_FIELD
    )

    @validator("id")
    def validate_no_duplicate_ids(cls, v):
        if in_proc_ids(v):
            raise ValueError(f"Duplicate id '{v}' detected.")
        add_proc_id(v)
        return v

    class Config:
        extra = Extra.forbid


class GuardDeviationProcessNodeModel(BaseModel):
    id: str = Field(alias=lib.ID_FIELD)
    children: Optional[List[ProcessNodeModel]] = Field(
        alias=lib.CHILDREN_FIELD
    )

    @validator("id")
    def validate_no_duplicate_ids(cls, v):
        if in_proc_ids(v):
            raise ValueError(f"Duplicate id '{v}' detected.")
        add_proc_id(v)
        return v

    # class Config:
    #     extra = Extra.forbid


class GuardDeviationNodeModel(BaseModel):
    policy_node: GuardDeviationProcessNodeModel = Field(alias="policyNode")

    class Config:
        extra = Extra.forbid


# Actions Models --------------------------------------------------------------


class SharedDefaultActionFieldsModel(BaseModel):
    enabled: Optional[bool] = Field(alias=lib.ENABLED_FIELD)

    class Config:
        extra = Extra.forbid


class SharedActionFieldsModel(ActionSelectorsModel):
    enabled: Optional[bool] = Field(alias=lib.ENABLED_FIELD)

    @root_validator(pre=True)
    def validate_has_selector(cls, fields: Dict):
        count = 0
        values_count = 0
        for key, value in fields.items():
            if key.endswith("Selector"):
                count += 1
            if value:
                values_count += 1
        if count == 0:
            raise ValueError(
                "At least one selector required for non-default actions."
            )
        if values_count != count:
            raise ValueError("All selectors must have values.")
        return fields

    class Config:
        extra = Extra.forbid


class DefaultMakeRedflagModel(SharedDefaultActionFieldsModel):
    content: Optional[str] = Field(alias=lib.FLAG_CONTENT, max_length=350)
    impact: Optional[str] = Field(alias=lib.FLAG_IMPACT, max_length=100)
    severity: Literal[tuple(lib.ALLOWED_SEVERITIES)] = Field(  # type: ignore
        alias=lib.FLAG_SEVERITY
    )

    class Config:
        extra = Extra.forbid


class MakeRedflagModel(SharedActionFieldsModel, DefaultMakeRedflagModel):
    pass


class DefaultMakeOpsflagModel(BaseModel):
    content: Optional[str] = Field(alias=lib.FLAG_CONTENT, max_length=350)
    description: Optional[str] = Field(
        alias=lib.FLAG_DESCRIPTION, max_length=350
    )
    severity: Literal[tuple(lib.ALLOWED_SEVERITIES)] = Field(  # type: ignore
        alias=lib.FLAG_SEVERITY
    )

    class Config:
        extra = Extra.forbid


class MakeOpsflagModel(SharedActionFieldsModel, DefaultMakeOpsflagModel):
    pass


class DefaultWebhookActionModel(BaseModel):
    url_destination: str = Field(
        alias=lib.URL_DESTINATION_FIELD, max_length=2048
    )
    template: Literal[tuple(lib.ALLOWED_TEMPLATES)] = Field(  # type: ignore
        alias=lib.TEMPLATE_FIELD
    )


class WebhookActionModel(SharedActionFieldsModel, DefaultWebhookActionModel):
    pass


class DefaultActionsModel(BaseModel):
    make_redflag: Optional[DefaultMakeRedflagModel] = Field(
        alias=lib.ACTION_MAKE_REDFLAG
    )
    make_opsflag: Optional[DefaultMakeOpsflagModel] = Field(
        alias=lib.ACTION_MAKE_OPSFLAG
    )
    webhook: Optional[DefaultWebhookActionModel] = Field(
        alias=lib.ACTION_WEBHOOK
    )
    agent_kill_pod: Optional[SharedDefaultActionFieldsModel] = Field(
        alias=lib.ACTION_KILL_POD
    )
    agent_kill_proc: Optional[SharedDefaultActionFieldsModel] = Field(
        alias=lib.ACTION_KILL_PROC
    )
    agent_kill_proc_group: Optional[SharedDefaultActionFieldsModel] = Field(
        alias=lib.ACTION_KILL_PROC_GRP
    )

    @root_validator(pre=True)
    def validate_only_one_action(cls, values: Dict):
        actions_count = len(values)
        if actions_count > 1:
            raise ValueError(
                "Detected multiple action definitions in one action. Each"
                " action definition must be a separate entry in the list."
            )
        return values

    class Config:
        extra = Extra.forbid


class ResponseActionsModel(BaseModel):
    make_redflag: Optional[MakeRedflagModel] = Field(
        alias=lib.ACTION_MAKE_REDFLAG
    )
    make_opsflag: Optional[MakeOpsflagModel] = Field(
        alias=lib.ACTION_MAKE_OPSFLAG
    )
    webhook: Optional[WebhookActionModel] = Field(alias=lib.ACTION_WEBHOOK)
    agent_kill_pod: Optional[SharedActionFieldsModel] = Field(
        alias=lib.ACTION_KILL_POD
    )
    agent_kill_proc: Optional[SharedActionFieldsModel] = Field(
        alias=lib.ACTION_KILL_PROC
    )
    agent_kill_proc_group: Optional[SharedActionFieldsModel] = Field(
        alias=lib.ACTION_KILL_PROC_GRP
    )

    @root_validator(pre=True)
    def validate_only_one_action(cls, values: Dict):
        actions_count = len(values)
        if actions_count > 1:
            raise ValueError(
                "Detected multiple action definitions in one action. Each"
                " action definition must be a separate entry in the list."
            )
        return values

    class Config:
        extra = Extra.forbid


class GuardianResponseModel(BaseModel):
    default_field: List[DefaultActionsModel] = Field(
        alias=lib.RESP_DEFAULT_FIELD
    )
    response_field: List[ResponseActionsModel] = Field(
        alias=lib.RESP_ACTIONS_FIELD
    )


# Metadata Models -------------------------------------------------------------


class GuardianMetadataModel(BaseModel):
    name: str = Field(alias=lib.METADATA_NAME_FIELD)
    type: Literal[tuple(lib.GUARDIAN_POL_TYPES)] = Field(  # type: ignore
        alias=lib.METADATA_TYPE_FIELD
    )
    create_time: Optional[Union[int, float, str]] = Field(
        alias=lib.METADATA_CREATE_TIME
    )
    first_timestamp: Optional[Union[int, float, str]] = Field(
        alias=lib.FIRST_TIMESTAMP_FIELD
    )
    latest_timestamp: Optional[Union[int, float, str]] = Field(
        alias=lib.LATEST_TIMESTAMP_FIELD
    )
    uid: Optional[str] = Field(alias=lib.METADATA_UID_FIELD)
    checksum: Optional[str] = Field(alias=lib.METADATA_S_CHECKSUM_FIELD)


class GuardianFingerprintGroupMetadataModel(BaseModel):
    image: Optional[str] = Field(alias=lib.IMAGE_FIELD)
    image_id: Optional[str] = Field(alias=lib.IMAGEID_FIELD)
    cgroup: Optional[str] = Field(alias=lib.CGROUP_FIELD)
    first_timestamp: Optional[Union[int, float]] = Field(
        alias=lib.FIRST_TIMESTAMP_FIELD
    )
    latest_timestamp: Optional[Union[int, float]] = Field(
        alias=lib.LATEST_TIMESTAMP_FIELD
    )


class GuardianDeviationMetadataModel(BaseModel):
    type: str = Field(alias=lib.METADATA_TYPE_FIELD)
    policy_uid: str = Field(alias="policy_uid")


# Spec Models -----------------------------------------------------------------


class GuardianPolicySpecModel(
    GuardianSelectorsModel, GuardianSpecOptionsModel
):
    enabled: Optional[bool] = Field(alias=lib.ENABLED_FIELD)
    mode: Literal[tuple(lib.POL_MODES)] = Field(  # type: ignore
        alias=lib.POL_MODE_FIELD
    )
    process_policy: List[ProcessNodeModel] = Field(alias=lib.PROC_POLICY_FIELD)
    network_policy: NetworkPolicyModel = Field(alias=lib.NET_POLICY_FIELD)
    response: GuardianResponseModel = Field(alias=lib.RESPONSE_FIELD)

    class Config:
        extra = Extra.forbid


class GuardianBaselineSpecModel(
    GuardianSelectorsModel, GuardianSpecOptionsModel
):
    process_policy: List[ProcessNodeModel] = Field(alias=lib.PROC_POLICY_FIELD)
    network_policy: NetworkPolicyModel = Field(alias=lib.NET_POLICY_FIELD)

    class Config:
        extra = Extra.forbid


class GuardianDeviationSpecModel(
    GuardianSelectorsModel, GuardianSpecOptionsModel
):
    process_policy: List[
        Union[ProcessNodeModel, GuardDeviationNodeModel]
    ] = Field(alias=lib.PROC_POLICY_FIELD)
    network_policy: Optional[DeviationNetworkPolicyModel] = Field(
        alias=lib.NET_POLICY_FIELD
    )

    class Config:
        extra = Extra.forbid


# Top-level Models ------------------------------------------------------------


class GuardianFingerprintModel(BaseModel):
    api_version: str = Field(alias=lib.API_FIELD)
    kind: Literal[lib.FPRINT_KIND] = Field(  # type: ignore
        alias=lib.KIND_FIELD
    )
    metadata: GuardianMetadataModel = Field(alias=lib.METADATA_FIELD)
    spec: GuardianBaselineSpecModel = Field(alias=lib.SPEC_FIELD)

    _selector_validator = root_validator(
        allow_reuse=True, skip_on_failure=True
    )(validate_selectors)

    def __init__(self, **data: Any):
        clear_proc_ids()
        super().__init__(**data)
        clear_proc_ids()

    class Config:
        extra = Extra.forbid


class FingerprintGroupDataModel(BaseModel):
    fingerprints: List[GuardianFingerprintModel] = Field(
        alias=lib.FPRINT_GRP_FINGERPRINTS_FIELD
    )
    cont_names: Optional[List[str]] = Field(
        alias=lib.FPRINT_GRP_CONT_NAMES_FIELD
    )
    cont_ids: Optional[List[str]] = Field(alias=lib.FPRINT_GRP_CONT_IDS_FIELD)
    machines: Optional[List[str]] = Field(alias=lib.FPRINT_GRP_MACHINES_FIELD)

    class Config:
        extra = Extra.forbid


class GuardianFingerprintGroupModel(BaseModel):
    api_version: str = Field(alias=lib.API_FIELD)
    kind: Literal[lib.FPRINT_GROUP_KIND] = Field(  # type: ignore
        alias=lib.KIND_FIELD
    )
    metadata: GuardianFingerprintGroupMetadataModel = Field(
        alias=lib.METADATA_FIELD
    )
    data: FingerprintGroupDataModel

    class Config:
        extra = Extra.ignore


class GuardianDeviationModel(BaseModel):
    api_version: str = Field(alias=lib.API_FIELD)
    kind: Literal[lib.DEVIATION_KIND] = Field(  # type: ignore
        alias=lib.KIND_FIELD
    )
    metadata: GuardianDeviationMetadataModel = Field(alias=lib.METADATA_FIELD)
    spec: GuardianDeviationSpecModel = Field(alias=lib.SPEC_FIELD)

    def __init__(self, **data: Any):
        clear_proc_ids()
        super().__init__(**data)
        clear_proc_ids()


class GuardianBaselineModel(BaseModel):
    api_version: str = Field(alias=lib.API_FIELD)
    kind: Literal[lib.BASELINE_KIND] = Field(  # type: ignore
        alias=lib.KIND_FIELD
    )
    metadata: GuardianMetadataModel = Field(alias=lib.METADATA_FIELD)
    spec: GuardianBaselineSpecModel = Field(alias=lib.SPEC_FIELD)

    _selector_validator = root_validator(
        allow_reuse=True, skip_on_failure=True
    )(validate_selectors)

    def __init__(self, **data: Any):
        clear_proc_ids()
        super().__init__(**data)
        clear_proc_ids()

    class Config:
        extra = Extra.ignore


class GuardianPolicyModel(BaseModel):
    api_version: str = Field(alias=lib.API_FIELD)
    kind: Literal[lib.POL_KIND] = Field(alias=lib.KIND_FIELD)  # type: ignore
    metadata: GuardianMetadataModel = Field(alias=lib.METADATA_FIELD)
    spec: GuardianPolicySpecModel = Field(alias=lib.SPEC_FIELD)

    _selector_validator = root_validator(
        allow_reuse=True, skip_on_failure=True
    )(validate_selectors)

    def __init__(self, **data: Any):
        clear_proc_ids()
        super().__init__(**data)
        clear_proc_ids()

    class Config:
        extra = Extra.forbid


class GuardianObjectModel(BaseModel):
    api_version: str = Field(alias=lib.API_FIELD)
    kind: str = Field(alias=lib.KIND_FIELD)
    metadata: Dict[str, str] = Field(alias=lib.METADATA_FIELD)
    spec: Dict = Field(alias=lib.SPEC_FIELD)

    class Config:
        extra = Extra.ignore


class GuardianObjectListModel(BaseModel):
    api_version: str = Field(alias=lib.API_FIELD)
    items: List[GuardianObjectModel] = Field(alias=lib.ITEMS_FIELD)


# -----------------------------------------------------------------------------
# Suppression Models ----------------------------------------------------------
# -----------------------------------------------------------------------------


class SuppressionPolicySelectorsModel(BaseModel):
    trace_selector: Optional[TraceSelectorModel] = Field(
        alias=lib.TRACE_SELECTOR_FIELD
    )
    user_selector: Optional[UserSelectorModel] = Field(
        alias=lib.USER_SELECTOR_FIELD
    )

    @root_validator
    def ensure_one_field(cls, values: Dict):
        if not any(
            value
            for field, value in values.items()
            if field.endswith("selector")
        ):
            # TODO fill out error
            raise ValueError("")
        return values

    class Config:
        extra = Extra.forbid


# Metadata Models -------------------------------------------------------------


class SuppressionPolicyMetadataModel(BaseModel):
    name: str = Field(alias=lib.METADATA_NAME_FIELD)
    type: Literal[tuple(lib.SUPPRESSION_POL_TYPES)] = Field(  # type: ignore
        alias=lib.METADATA_TYPE_FIELD
    )
    create_time: Optional[Union[int, float, str]] = Field(
        alias=lib.METADATA_CREATE_TIME
    )
    first_timestamp: Optional[Union[int, float]] = Field(
        alias=lib.FIRST_TIMESTAMP_FIELD
    )
    latest_timestamp: Optional[Union[int, float]] = Field(
        alias=lib.LATEST_TIMESTAMP_FIELD
    )
    uid: Optional[str] = Field(alias=lib.METADATA_UID_FIELD)
    checksum: Optional[str] = Field(alias=lib.METADATA_S_CHECKSUM_FIELD)


# Spec Models -----------------------------------------------------------------


class AllowedFlagsModel(BaseModel):
    class_field: str = Field(alias=lib.FLAG_CLASS)


class SuppressionPolicySpecModel(SuppressionPolicySelectorsModel):
    enabled: Optional[bool] = Field(alias=lib.ENABLED_FIELD)
    mode: Literal[tuple(lib.POL_MODES)] = Field(  # type: ignore
        alias=lib.POL_MODE_FIELD
    )
    allowed_flags: List[AllowedFlagsModel] = Field(
        alias=lib.ALLOWED_FLAGS_FIELD
    )

    class Config:
        extra = Extra.forbid


# Top-level Models ------------------------------------------------------------


class SuppressionPolicyModel(BaseModel):
    api_version: str = Field(alias=lib.API_FIELD)
    kind: Literal[lib.POL_KIND] = Field(alias=lib.KIND_FIELD)  # type: ignore
    metadata: SuppressionPolicyMetadataModel = Field(alias=lib.METADATA_FIELD)
    spec: SuppressionPolicySpecModel = Field(alias=lib.SPEC_FIELD)

    class Config:
        extra = Extra.forbid


# -----------------------------------------------------------------------------
# Config Models ----------------------------------------------------------
# -----------------------------------------------------------------------------


class ContextModel(BaseModel):
    org: str = Field(alias=lib.ORG_FIELD)
    cgroups: Optional[Union[str, List[str]]] = Field(alias=lib.CGROUP_FIELD)
    cluster: Optional[Union[str, List[str]]] = Field(alias=lib.CLUSTER_FIELD)
    container_ids: Optional[Union[str, List[str]]] = Field(
        alias=lib.CONTAINER_ID_FIELD
    )
    container_names: Optional[Union[str, List[str]]] = Field(
        alias=lib.CONTAINER_NAME_FIELD
    )
    image_ids: Optional[Union[str, List[str]]] = Field(alias=lib.IMAGEID_FIELD)
    images: Optional[Union[str, List[str]]] = Field(alias=lib.IMAGE_FIELD)
    machines: Optional[Union[str, List[str]]] = Field(alias=lib.MACHINES_FIELD)
    namespace: Optional[Union[str, List[str]]] = Field(
        alias=lib.NAMESPACE_FIELD
    )
    pods: Optional[Union[str, List[str]]] = Field(alias=lib.POD_FIELD)

    class Config:
        extra = Extra.forbid


# Metadata Models -------------------------------------------------------------


class SecretMetadataModel(BaseModel):
    name: str = Field(alias=lib.METADATA_NAME_FIELD)
    create_time: Optional[Union[float, int]] = Field(
        alias=lib.METADATA_CREATE_TIME
    )


# Top-level Models ------------------------------------------------------------


class SecretModel(BaseModel):
    api_version: str = Field(alias=lib.API_FIELD)
    kind: Literal[lib.SECRET_KIND] = Field(  # type: ignore
        alias=lib.KIND_FIELD
    )
    metadata: SecretMetadataModel = Field(alias=lib.METADATA_FIELD)
    data: Optional[Dict[str, str]] = Field(alias=lib.DATA_FIELD)
    string_data: Optional[Dict[str, str]] = Field(alias=lib.STRING_DATA_FIELD)

    class Config:
        extra = Extra.forbid


class ContextsModel(BaseModel):
    context_name: str = Field(alias=lib.CONTEXT_NAME_FIELD)
    secret: str = Field(alias=lib.SECRET_FIELD)
    context: ContextModel = Field(alias=lib.CONTEXT_FIELD)

    class Config:
        extra = Extra.forbid


class ConfigModel(BaseModel):
    api_version: str = Field(alias=lib.API_FIELD)
    kind: Literal[lib.CONFIG_KIND] = Field(  # type: ignore
        alias=lib.KIND_FIELD
    )
    contexts: List[ContextsModel] = Field(alias=lib.CONTEXTS_FIELD)
    current_context: str = Field(alias=lib.CURR_CONTEXT_FIELD)

    class Config:
        extra = Extra.forbid


# -----------------------------------------------------------------------------
# Misc Models -----------------------------------------------------------------
# -----------------------------------------------------------------------------


class UidListMetadataModel(BaseModel):
    start_time: Union[int, float] = Field(alias=lib.METADATA_START_TIME_FIELD)
    end_time: Union[int, float] = Field(alias=lib.METADATA_END_TIME_FIELD)

    @root_validator
    def valid_end_time(cls, values: Dict):
        start_time = values["start_time"]
        end_time = values["end_time"]
        if end_time <= start_time:
            raise ValueError(
                f"'{lib.METADATA_END_TIME_FIELD}' must be greater than"
                f" '{lib.METADATA_START_TIME_FIELD}'"
            )
        return values


class UidListDataModel(BaseModel):
    uids: List[str] = Field(alias=lib.UIDS_FIELD)

    class Config:
        extra = Extra.forbid


class UidListModel(BaseModel):
    api_version: str = Field(alias=lib.API_FIELD)
    kind: Literal[lib.UID_LIST_KIND] = Field(  # type: ignore
        alias=lib.KIND_FIELD
    )
    metadata: UidListMetadataModel = Field(alias=lib.METADATA_FIELD)
    data: UidListDataModel = Field(alias=lib.DATA_FIELD)

    class Config:
        extra = Extra.forbid


class SpyderbatObject(BaseModel):
    api_version: Literal[lib.API_VERSION] = Field(  # type: ignore
        alias=lib.API_FIELD
    )
    kind: str = Field(alias=lib.KIND_FIELD)

    @validator("kind")
    def valid_kind(cls, v):
        if v not in KIND_TO_SCHEMA:
            raise ValueError(f"Kind '{v}' not in {list(KIND_TO_SCHEMA)}")
        return v

    class Config:
        extra = Extra.allow


KIND_TO_SCHEMA: Dict[str, BaseModel] = {
    lib.BASELINE_KIND: GuardianBaselineModel,
    lib.CONFIG_KIND: ConfigModel,
    lib.FPRINT_GROUP_KIND: GuardianFingerprintGroupModel,
    lib.FPRINT_KIND: GuardianFingerprintModel,
    lib.POL_KIND: GuardianPolicyModel,
    (lib.POL_KIND, lib.POL_TYPE_TRACE): SuppressionPolicyModel,
    lib.SECRET_KIND: SecretModel,
    lib.UID_LIST_KIND: UidListModel,
    lib.DEVIATION_KIND: GuardianDeviationModel,
}


def clear_proc_ids():
    global __PROC_IDS
    __PROC_IDS.clear()


def in_proc_ids(id: str) -> bool:
    return id in __PROC_IDS


def add_proc_id(id: str):
    global __PROC_IDS
    __PROC_IDS[id] = True
