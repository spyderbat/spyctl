import copy
import inspect
import io
import json
import os
import re
import sys
import time
import unicodedata
from base64 import urlsafe_b64encode as b64url
from datetime import timezone
from fnmatch import fnmatch
from hashlib import md5
from pathlib import Path
from typing import IO, Any, Dict, Iterable, List, Optional, Tuple, Union
from urllib.parse import urlparse
from uuid import uuid4

import click
import dateutil.parser as dateparser
import yaml
import zulu
from click.shell_completion import CompletionItem


class Aliases:
    def __init__(self, aliases: Iterable[str], name, name_plural="") -> None:
        self.name = name
        self.name_plural = name_plural
        self.aliases = set(aliases)

    def __eq__(self, __o: object) -> bool:
        plural_match = __o == self.name_plural if self.name_plural else False
        return __o in self.aliases or __o == self.name or plural_match

    def __str__(self) -> str:
        return self.name_plural or self.name


COLORIZE_OUTPUT = True
APP_NAME = "spyctl"
WARNING_MSG = "is_warning"
WARNING_COLOR = "\x1b[38;5;203m"
NOTICE_COLOR = "\x1b[38;5;75m"
ADD_COLOR = "\x1b[38;5;35m"
SUB_COLOR = "\x1b[38;5;203m"
COLOR_END = "\x1b[0m"
API_CALL = False
INTERACTIVE = False
DEBUG = False
LOG_VAR = []
ERR_VAR = []
USE_LOG_VARS = False


def disable_colorization():
    global COLORIZE_OUTPUT, WARNING_COLOR, COLOR_END
    global ADD_COLOR, SUB_COLOR, NOTICE_COLOR
    COLORIZE_OUTPUT = False
    WARNING_COLOR = ""
    COLOR_END = ""
    SUB_COLOR = ""
    ADD_COLOR = ""
    NOTICE_COLOR = ""


def flush_log_var() -> str:
    global LOG_VAR
    rv = "\n".join(LOG_VAR)
    LOG_VAR.clear()
    return rv


def flush_err_var() -> str:
    global ERR_VAR
    rv = "\n".join(ERR_VAR)
    ERR_VAR.clear()
    return rv


# Resource Aliases
AGENT_RESOURCE = Aliases(
    ["agents", "agent", "ag"],
    "agent",
    "agents",
)
BASELINES_RESOURCE = Aliases(
    [
        "baselines",
        "baseline",
        "spyderbat-baselines",
        "spyderbat-baseline",
        "base",
        "sb",
        "b",
    ],
    "baseline",
    "baselines",
)
CLUSTERS_RESOURCE = Aliases(
    ["clusters", "cluster", "clust", "clusts", "clus"], "cluster", "clusters"
)
CONTAINER_RESOURCE = Aliases(
    ["container", "containers", "cont" "c"],
    "container",
    "containers",
)
CONNECTIONS_RESOURCE = Aliases(
    [
        "connections",
        "connection",
        "connect",
        "connects",
        "conn",
        "conns",
        "con",
        "cons",
    ],
    "connection",
    "connections",
)
CONNECTION_BUN_RESOURCE = Aliases(
    ["connection-bundle", "connection-bundles", "conn_bun", "conn_buns", "cb"],
    "connection-bundle",
    "connection-bundles",
)
DEPLOYMENTS_RESOURCE = Aliases(
    ["deployments", "deployment", "deploys", "deploy"],
    "deployment",
    "deployments",
)
DEVIATIONS_RESOURCE = Aliases(
    ["deviations", "deviation", "dev"],
    "deviation",
    "deviations",
)
DAEMONSET_RESOURCE = Aliases(
    ["daemonset", "daemonsets", "daemon", "ds"],
    "daemonset",
    "daemonsets",
)
FINGERPRINT_GROUP_RESOURCE = Aliases(
    ["fingerprint-group", "fingerprint-groups", "fprint-group", "fg"],
    "fingerprint-group",
    "fingerprint-groups",
)
FINGERPRINTS_RESOURCE = Aliases(
    [
        "fingerprints",
        "print",
        "prints",
        "fingerprint",
        "fprint",
        "f",
        "fprints",
        "fingerprint-group",
        "fingerprint-groups",
    ],
    "fingerprint",
    "fingerprints",
)
MACHINES_RESOURCE = Aliases(
    ["machines", "mach", "machs", "machine"],
    "machine",
    "machines",
)
NAMESPACES_RESOURCE = Aliases(
    ["namespaces", "name", "names", "namesp", "namesps", "namespace"],
    "namespace",
    "namespaces",
)
NOTIFICATION_CONFIGS_RESOURCE = Aliases(
    [
        "notification-config",
        "notification-configs",
        "notification-policy",
        "nc",
    ],
    "notification-config",
    "notification-configs",
)
NOTIFICATION_CONFIG_TEMPLATES_RESOURCE = Aliases(
    [
        "notification-config-template",
        "notification-config-templates",
        "notification-config-tmpls",
        "notif-config-tmpl",
        "notif-config-tmpls",
        "nct",
    ],
    "notification-config-template",
    "notification-config-templates",
)
NOTIFICATION_TARGETS_RESOURCE = Aliases(
    [
        "target",
        "targets",
        "notification-target",
        "notification-targets",
        "nt",
    ],
    "notification-target",
    "notification-targets",
)
NODES_RESOURCE = Aliases(["nodes", "node"], "node", "nodes")
OPSFLAGS_RESOURCE = Aliases(["opsflags", "opsflag"], "opsflag", "opsflags")
PODS_RESOURCE = Aliases(["pods", "pod"], "pod", "pods")
REDFLAGS_RESOURCE = Aliases(["redflags", "redflag"], "redflag", "redflags")
POLICIES_RESOURCE = Aliases(
    [
        "policies",
        "spyderbat-policy",
        "spyderbat-policies",
        "spy-pol",
        "spol",
        "policy",
        "pol",
        "p",
    ],
    "policy",
    "policies",
)
PROCESSES_RESOURCE = Aliases(
    [
        "processes",
        "process",
        "proc",
        "procs",
    ],
    "process",
    "processes",
)
SOURCES_RESOURCE = Aliases(["source", "sources", "src"], "source", "sources")
SPYDERTRACE_RESOURCE = Aliases(
    ["spydertrace", "spydertraces", "spyder", "trace", "traces"],
    "spydertrace",
    "spydertraces",
)
SPYDERTRACE_SUMMARY_RESOURCE = Aliases(
    [
        "spydertrace-summary",
        "spydertrace-summaries",
        "trace-summary",
        "trace-summaries",
        "t-sum",
    ],
    "spydertrace-summary",
    "spydertrace-summaries",
)
REPLICASET_RESOURCE = Aliases(
    ["replicaset", "replicasets", "rs", "replica"],
    "replicaset",
    "replicasets",
)
SUPPRESSION_POLICY_RESOURCE = Aliases(
    [
        "suppression-policy",
        "suppression-policies",
        "sp",
        "s-pol",
        "trace-policy",
    ],
    "suppression-policy",
    "suppression-policies",
)
UID_LIST_RESOURCE = Aliases(
    ["uid-list", "uid-lists", "uid", "uids-list"], "uid-list", "uid-lists"
)

SECRETS_ALIAS = Aliases(["secret", "secrets", "sec", "s"], "secret", "secrets")
CONFIG_ALIAS = Aliases(
    ["config", "configs", "conf", "cfg", "configuration", "configurations"],
    "config",
    "configs",
)

ALL_RESOURCES: List[Aliases] = [
    g_var
    for g_var_name, g_var in globals().items()
    if g_var_name.endswith("RESOURCE")
]


def get_plural_name_from_alias(alias: str):
    for resource in ALL_RESOURCES:
        if alias == resource:
            return resource.name_plural
    return None


DEL_RESOURCES: List[str] = [
    POLICIES_RESOURCE.name,
    SUPPRESSION_POLICY_RESOURCE.name,
    NOTIFICATION_CONFIGS_RESOURCE.name,
    NOTIFICATION_TARGETS_RESOURCE.name,
]
DESC_RESOURCES: List[str] = [
    POLICIES_RESOURCE.name,
]
EDIT_RESOURCES: List[str] = [
    POLICIES_RESOURCE.name,
    SUPPRESSION_POLICY_RESOURCE.name,
    NOTIFICATION_CONFIGS_RESOURCE.name,
    NOTIFICATION_TARGETS_RESOURCE.name,
]
GET_RESOURCES: List[str] = [
    AGENT_RESOURCE.name_plural,
    CLUSTERS_RESOURCE.name_plural,
    CONNECTIONS_RESOURCE.name_plural,
    CONNECTION_BUN_RESOURCE.name_plural,
    CONTAINER_RESOURCE.name_plural,
    DEPLOYMENTS_RESOURCE.name_plural,
    DEVIATIONS_RESOURCE.name_plural,
    FINGERPRINTS_RESOURCE.name_plural,
    MACHINES_RESOURCE.name_plural,
    NAMESPACES_RESOURCE.name_plural,
    NODES_RESOURCE.name_plural,
    NOTIFICATION_CONFIGS_RESOURCE.name_plural,
    NOTIFICATION_CONFIG_TEMPLATES_RESOURCE.name_plural,
    NOTIFICATION_TARGETS_RESOURCE.name_plural,
    OPSFLAGS_RESOURCE.name_plural,
    PODS_RESOURCE.name_plural,
    POLICIES_RESOURCE.name_plural,
    PROCESSES_RESOURCE.name_plural,
    REDFLAGS_RESOURCE.name_plural,
    SOURCES_RESOURCE.name_plural,
    # SPYDERTRACE_SUMMARY_RESOURCE.name_plural,
    SUPPRESSION_POLICY_RESOURCE.name_plural,
    CONTAINER_RESOURCE.name_plural,
    SPYDERTRACE_RESOURCE.name_plural,
]
LOGS_RESOURCES: List[str] = [POLICIES_RESOURCE.name]
VAL_RESOURCES: List[str] = [
    BASELINES_RESOURCE.name,
    POLICIES_RESOURCE.name,
    SECRETS_ALIAS.name,
    CONFIG_ALIAS.name,
]
RESOURCES_WITH_SCHEMAS = [
    BASELINES_RESOURCE.name,
    CONFIG_ALIAS.name,
    FINGERPRINTS_RESOURCE.name,
    FINGERPRINT_GROUP_RESOURCE.name,
    POLICIES_RESOURCE.name,
    SECRETS_ALIAS.name,
    SUPPRESSION_POLICY_RESOURCE.name,
    UID_LIST_RESOURCE.name,
]

CMD_ORG_FIELD = "org"


def tmp_context_options(function):
    function = click.option(f"--{CMD_ORG_FIELD}", hidden=True)(function)
    function = click.option(f"--{API_KEY_FIELD}", hidden=True)(function)
    function = click.option(f"--{API_URL_FIELD}", hidden=True)(function)
    return function


def colorization_option(function):
    function = click.option(
        "--colorize/--no-colorize",
        help="Specify coloration on or off. Default is on.",
        default=True,
    )(function)
    return function


class DelResourcesParam(click.ParamType):
    name = "del_resources"

    def shell_complete(
        self, ctx: click.Context, param: click.Parameter, incomplete: str
    ) -> List["CompletionItem"]:
        return [
            CompletionItem(resrc_name)
            for resrc_name in DEL_RESOURCES
            if resrc_name.startswith(incomplete)
        ]


class DescribeResourcesParam(click.ParamType):
    name = "del_resources"

    def shell_complete(
        self, ctx: click.Context, param: click.Parameter, incomplete: str
    ) -> List["CompletionItem"]:
        return [
            CompletionItem(resrc_name)
            for resrc_name in DESC_RESOURCES
            if resrc_name.startswith(incomplete)
        ]


class EditResourcesParam(click.ParamType):
    name = "edit_resources"

    def shell_complete(
        self, ctx: click.Context, param: click.Parameter, incomplete: str
    ) -> List["CompletionItem"]:
        return [
            CompletionItem(resrc_name)
            for resrc_name in EDIT_RESOURCES
            if resrc_name.startswith(incomplete)
        ]


class GetResourcesParam(click.ParamType):
    name = "get_resources"

    def shell_complete(
        self, ctx: click.Context, param: click.Parameter, incomplete: str
    ) -> List["CompletionItem"]:
        return [
            CompletionItem(resrc_name)
            for resrc_name in GET_RESOURCES
            if resrc_name.startswith(incomplete)
        ]


class LogsResourcesParam(click.ParamType):
    name = "logs_resources"

    def shell_complete(
        self, ctx: click.Context, param: click.Parameter, incomplete: str
    ) -> List["CompletionItem"]:
        return [
            CompletionItem(resrc_name)
            for resrc_name in LOGS_RESOURCES
            if resrc_name.startswith(incomplete)
        ]


class SuppressionPolTypeParam(click.ParamType):
    name = "get_resources"

    def shell_complete(
        self, ctx: click.Context, param: click.Parameter, incomplete: str
    ) -> List["CompletionItem"]:
        return [
            CompletionItem(resrc_name)
            for resrc_name in [POL_TYPE_TRACE]
            if resrc_name.startswith(incomplete)
        ]


class LabelParam(click.ParamType):
    def convert(
        self,
        value: Any,
        param: Optional[click.Parameter],
        ctx: Optional[click.Context],
    ) -> Any:
        rv = label_input_to_dict()
        if rv is None:
            self.fail("Invalid label input", param, ctx)
        return value


class ListParam(click.ParamType):
    def convert(
        self,
        value: Any,
        param: Optional[click.Parameter],
        ctx: Optional[click.Context],
    ) -> Any:
        if "," in value:
            rv = value.split(",")
        else:
            rv = value.split(" ")
        for i, v in enumerate(rv):
            rv[i] = v.strip(" ")
        return rv


class ListDictParam(click.ParamType):
    def convert(
        self,
        value: Any,
        param: Optional[click.Parameter],
        ctx: Optional[click.Context],
    ) -> Any:
        rv = []
        rv_dict = {}
        if "," in value:
            args_list = value.split(",")
        for v in args_list:
            if "=" in v:
                key, val = v.split("=")[:2]
                rv_dict[key] = val
            else:
                rv.append(v)
        if rv_dict:
            rv.append(rv_dict)
        return rv


class FileList(click.File):
    def convert(
        self,
        value: Any,
        param: Optional[click.Parameter],
        ctx: Optional[click.Context],
    ) -> Any:
        rv = []
        if isinstance(value, Iterable) and not isinstance(value, str):
            for string in value:
                rv.extend(self.__handle_string(string, param, ctx))
        else:
            rv.extend(self.__handle_string(value, param, ctx))
        return rv

    def __handle_string(self, input: str, param, ctx) -> List[str]:
        rv = []
        if "," in input:
            filenames = input.split(",")
        else:
            filenames = [input]
        for fn in filenames:
            fn = fn.strip(" ")
            if "*" in fn:
                match_fns = self.fnmatch_files(fn, param, ctx)
                for match_fn in match_fns:
                    rv.append(super().convert(match_fn, param, ctx))
            else:
                rv.append(super().convert(fn, param, ctx))
        return rv

    def fnmatch_files(self, fnmatch_str: str, param, ctx):
        rv = []
        path, tail = os.path.split(fnmatch_str)
        if not path:
            path = Path.cwd()
        else:
            path = Path(path).expanduser().resolve()
        if not tail:
            self.fail("Directory wildcards are not supported.", param, ctx)
        else:
            try:
                for file in path.iterdir():
                    if fnmatch(file.name, tail):
                        rv.append(str(file))
            except Exception:
                self.fail(f"Unable to list files in {str(path)}")
        if not rv:
            self.fail(f"No files matching {fnmatch_str}.", param, ctx)
        return rv


SCHEMA_FIELD = "schema"

# Spyderbat Event Schema Prefix'
EVENT_METRICS_PREFIX = "event_metric"
EVENT_AUDIT_PREFIX = "event_audit"
EVENT_OPSFLAG_PREFIX = "event_opsflag"
EVENT_REDFLAG_PREFIX = "event_redflag"

EVENT_METRIC_SUBTYPE_MAP = {
    "agent": "agent",
    "machine": "machine",
}

EVENT_AUDIT_SUBTYPE_MAP = {
    "deviation": "guardian_deviation",
    "action": "guardian_action",
    "redflag": "guardian_redflag",
    "opsflag": "guardian_opsflag",
}

# Spyderbat Model Schema Prefix'
MODEL_AGENT_SCHEMA_PREFIX = "model_agent"
MODEL_CLUSTER_PREFIX = "model_k8s_cluster"
MODEL_CONNECTION_PREFIX = "model_connection"
MODEL_CONN_BUN_PREFIX = "model_bundled_connection"
MODEL_CONTAINER_PREFIX = "model_container"
MODEL_DEPLOYMENT_PREFIX = "model_k8s_deployment"
MODEL_FINGERPRINT_PREFIX = "model_fingerprint"
MODEL_MACHINE_PREFIX = "model_machine"
MODEL_NAMESPACE_PREFIX = "model_k8s_namespace"
MODEL_NODE_PREFIX = "model_k8s_node"
MODEL_POD_PREFIX = "model_k8s_pod"
MODEL_REPLICASET_PREFIX = "model_k8s_replicaset"
MODEL_PROCESS_PREFIX = "model_process"
MODEL_SPYDERTRACE_PREFIX = "model_spydertrace"
MODEL_DAEMONSET_PREFIX = "model_k8s_daemonset"
MODEL_FINGERPRINT_SUBTYPE_MAP = {
    "container": "container",
    "linux-service": "linux_svc",
}

# Datatypes for searching via API
DATATYPE_AUDIT = "audit"
DATATYPE_AGENTS = "agent_status"
DATATYPE_FINGERPRINTS = "fingerprints"
DATATYPE_K8S = "k8s"
DATATYPE_REDFLAGS = "redflags"
DATATYPE_SPYDERGRAPH = "spydergraph"

# Resource Kinds
BASELINE_KIND = "SpyderbatBaseline"
DEVIATION_KIND = "GuardianDeviation"
FPRINT_GROUP_KIND = "FingerprintGroup"
FPRINT_KIND = "SpyderbatFingerprint"
NOTIFICATION_KIND = "NotificationConfiguration"
NOTIF_TMPL_KIND = "NotificationConfigTemplate"
POL_KIND = "SpyderbatPolicy"
SUP_POL_KIND_ALIAS = "SuppressionPolicy"
TARGET_KIND = "NotificationTarget"
UID_LIST_KIND = "UidList"

# CONFIG Kinds
CONFIG_KIND = "Config"
SECRET_KIND = "APISecret"

# Top-level yaml Fields
API_FIELD = "apiVersion"
API_VERSION = "spyderbat/v1"
DATA_FIELD = "data"
ITEMS_FIELD = "items"
KIND_FIELD = "kind"
METADATA_FIELD = "metadata"
SPEC_FIELD = "spec"
STATUS_FIELD = "status"
STRING_DATA_FIELD = "stringData"
TYPE_FIELD = "type"

# Redflag Severities
S_CRIT = "critical"
S_HIGH = "high"
S_MED = "medium"
S_LOW = "low"
S_INFO = "info"
ALLOWED_SEVERITIES = [S_CRIT, S_HIGH, S_MED, S_LOW, S_INFO]

# Abbreviated Classes
CLASS_LONG_NAMES = {
    "conn": "connection",
    "redflag": "redflag",
    "opsflag": "opsflag",
    "mach": "machine",
    "proc": "process",
    "sess": "session",
    "sock": "socket",
    "cont": "container",
    "pod": "pod",
}

# Config
CURR_CONTEXT_FIELD = "current-context"
CONTEXTS_FIELD = "contexts"
CONTEXT_FIELD = "context"
CONTEXT_NAME_FIELD = "name"
SECRET_FIELD = "secret"
API_KEY_FIELD = "apikey"
API_URL_FIELD = "apiurl"
LOCATION_FIELD = "location"
ORG_FIELD = "organization"
POD_FIELD = "pod"
CLUSTER_FIELD = "cluster"
NAMESPACE_FIELD = "namespace"
NAMESPACE_LABELS_FIELD = "namespace-labels"
POD_LABELS_FIELD = "pod-labels"
MACHINES_FIELD = "machines"
DEFAULT_API_URL = "https://api.spyderbat.com"
POLICY_UID_FIELD = "policy"
POLICIES_FIELD = "policies"


# Response Actions
ACTION_KILL_POD = "agentKillPod"
ACTION_KILL_PROC = "agentKillProcess"
ACTION_KILL_PROC_GRP = "agentKillProcessGroup"
ACTION_WEBHOOK = "webhook"
ACTION_MAKE_REDFLAG = "makeRedFlag"
ACTION_MAKE_OPSFLAG = "makeOpsFlag"
ALLOWED_TEMPLATES = {"json", "yaml", "slack"}
ALLOWED_ACTIONS = {
    ACTION_WEBHOOK,
    ACTION_KILL_POD,
    ACTION_KILL_PROC,
    ACTION_KILL_PROC_GRP,
    ACTION_MAKE_REDFLAG,
    ACTION_MAKE_OPSFLAG,
}
RESPONSE_FIELD = "response"
RESP_DEFAULT_FIELD = "default"
RESP_ACTIONS_FIELD = "actions"
RESP_ACTION_NAME_FIELD = "actionName"
RESP_URL_FIELD = "url"
RESP_TEMPLATE_FIELD = "template"
RESP_SEVERITY_FIELD = "severity"
# makeFlag fields
FLAG_IMPACT = "impact"
FLAG_CONTENT = "content"
FLAG_SEVERITY = "severity"
FLAG_DESCRIPTION = "description"
# webhook fields
URL_DESTINATION_FIELD = "urlDestination"
TEMPLATE_FIELD = "template"


# Selectors
CONT_SELECTOR_FIELD = "containerSelector"
DNS_SELECTOR_FIELD = "dnsSelector"
MACHINE_SELECTOR_FIELD = "machineSelector"
NAMESPACE_SELECTOR_FIELD = "namespaceSelector"
POD_SELECTOR_FIELD = "podSelector"
PROCESS_SELECTOR_FIELD = "processSelector"
SVC_SELECTOR_FIELD = "serviceSelector"
TRACE_SELECTOR_FIELD = "traceSelector"
USER_SELECTOR_FIELD = "userSelector"
MATCH_LABELS_FIELD = "matchLabels"
# Machine Selector Fields
HOSTNAME_FIELD = "hostname"
MACHINE_UID_FIELD = "machineUID"
# Container Selector Fields
IMAGE_FIELD = "image"
IMAGEID_FIELD = "imageID"
CONT_NAME_FIELD = "containerName"
CONT_ID_FIELD = "containerID"
# Service Selector Fields
CGROUP_FIELD = "cgroup"

SELECTOR_FIELDS = {
    CONT_SELECTOR_FIELD,
    SVC_SELECTOR_FIELD,
    MACHINE_SELECTOR_FIELD,
    NAMESPACE_SELECTOR_FIELD,
    POD_SELECTOR_FIELD,
    TRACE_SELECTOR_FIELD,
    USER_SELECTOR_FIELD,
}

# Policies/Fingerprints
BE_POL_UID_FIELD = (
    "policy_uid"  # not in the policy objects themselves but in other records
)
POL_TYPE_CONT = "container"
POL_TYPE_SVC = "linux-service"
POL_TYPE_TRACE = "trace"
SUPPRESSION_POL_TYPES = [POL_TYPE_TRACE]
GUARDIAN_POL_TYPES = [POL_TYPE_CONT, POL_TYPE_SVC]
POL_TYPES = [POL_TYPE_SVC, POL_TYPE_CONT, POL_TYPE_TRACE]
POL_MODE_ENFORCE = "enforce"
POL_MODE_AUDIT = "audit"
POL_MODES = [POL_MODE_ENFORCE, POL_MODE_AUDIT]
POL_MODE_FIELD = "mode"
ENABLED_FIELD = "enabled"
DISABLE_PROCS_FIELD = "disableProcesses"
DISABLE_PROCS_ALL = "all"
DISABLE_PROCS_STRINGS = [DISABLE_PROCS_ALL]
DISABLE_CONNS_ALL = "all"
DISABLE_CONNS_INGRESS = "ingress"
DISABLE_CONNS_EGRESS = "egress"
DISABLE_CONNS_PRIVATE = "private"
DISABLE_CONNS_PRIVATE_E = "private-egress"
DISABLE_CONNS_PRIVATE_I = "private-ingress"
DISABLE_CONNS_PUBLIC = "public"
DISABLE_CONNS_PUBLIC_E = "public-egress"
DISABLE_CONNS_PUBLIC_I = "public-ingress"
DISABLE_CONNS_STRINGS = [
    DISABLE_CONNS_ALL,
    DISABLE_CONNS_EGRESS,
    DISABLE_CONNS_INGRESS,
]
DISABLE_CONN_OPTIONS_STRINGS = [
    DISABLE_CONNS_ALL,
    DISABLE_CONNS_EGRESS,
    DISABLE_CONNS_INGRESS,
    DISABLE_CONNS_PRIVATE,
    DISABLE_CONNS_PRIVATE_E,
    DISABLE_CONNS_PRIVATE_I,
    DISABLE_CONNS_PUBLIC,
    DISABLE_CONNS_PUBLIC_E,
    DISABLE_CONNS_PUBLIC_I,
]
DISABLE_CONNS_FIELD = "disableConnections"
DISABLE_PR_CONNS_FIELD = "disablePrivateConnections"
DISABLE_PU_CONNS_FIELD = "disablePublicConnections"
METADATA_NAME_FIELD = "name"
METADATA_TAGS_FIELD = "tags"
METADATA_TYPE_FIELD = "type"
METADATA_UID_FIELD = "uid"
METADATA_CREATE_TIME = "creationTimestamp"
METADATA_NAMESPACE_FIELD = "namespace"
METADATA_S_CHECKSUM_FIELD = "selectorHash"
METADATA_START_TIME_FIELD = "startTime"
METADATA_END_TIME_FIELD = "endTime"
NET_POLICY_FIELD = "networkPolicy"
PROC_POLICY_FIELD = "processPolicy"
FIRST_TIMESTAMP_FIELD = "firstTimestamp"
LATEST_TIMESTAMP_FIELD = "latestTimestamp"
TRIGGER_CLASS_FIELD = "triggerClass"
TRIGGER_ANCESTORS_FIELD = "triggerAncestors"
USERS_FIELD = "users"
INTERACTIVE_FIELD = "interactive"
INTERACTIVE_USERS_FIELD = "interactiveUsers"
NON_INTERACTIVE_USERS_FIELD = "nonInteractiveUsers"
ALLOWED_FLAGS_FIELD = "allowedFlags"
FLAG_SUMMARY_FIELD = "flagSummary"
FLAGS_FIELD = "flags"
# For the Spyderbat API
API_REQ_FIELD_NAME = "name"
API_REQ_FIELD_POLICY = "policy"
API_REQ_FIELD_POL_SELECTORS = "selectors"
API_REQ_FIELD_TAGS = "tags"
API_REQ_FIELD_TYPE = "type"
API_REQ_FIELD_UID = "uid"
API_HAS_TAGS_FIELD = "has_tags"
# Suppression Policy cmdline fields
SUP_POL_CMD_TRIG_ANCESTORS = "trigger-ancestors"
SUP_POL_CMD_TRIG_CLASS = "trigger-class"
SUP_POL_CMD_USERS = "users"
SUP_POL_CMD_INT_USERS = "interactive-users"
SUP_POL_CMD_N_INT_USERS = "non-interactive-users"
SUP_POL_SELECTOR_FIELDS = [
    SUP_POL_CMD_TRIG_ANCESTORS,
    SUP_POL_CMD_TRIG_CLASS,
    SUP_POL_CMD_USERS,
    SUP_POL_CMD_INT_USERS,
    SUP_POL_CMD_N_INT_USERS,
]
TRACE_SUMMARY_FIELD = "trace_summary"

NOT_AVAILABLE = "N/A"
# Fingerprint Groups
FPRINT_GRP_FINGERPRINTS_FIELD = "fingerprints"
FPRINT_GRP_CONT_NAMES_FIELD = "containerNames"
FPRINT_GRP_CONT_IDS_FIELD = "containerIDs"
FPRINT_GRP_MACHINES_FIELD = "machines"
# UID List
UIDS_FIELD = "uniqueIdentifiers"

# Any Object
VERSION_FIELD = "version"
VALID_FROM_FIELD = "valid_from"

# K8s Objects
BE_K8S_STATUS = "k8s_status"
BE_PHASE = "phase"
BE_KUID_FIELD = "kuid"

# Connections
PROC_NAME_FIELD = "proc_name"
CONN_ID = "id"
REMOTE_HOSTNAME_FIELD = "remote_hostname"
PROTOCOL_FIELD = "proto"
REMOTE_PORT = "remote_port"
LOCAL_PORT = "local_port"

# Connection Bundles
CLIENT_IP = "client_ip"
CLIENT_DNS = "client_dns_name"
CLIENT_PORT = "client_port"
SERVER_IP = "server_ip"
SERVER_DNS = "server_dns_name"
SERVER_PORT = "server_port"
NUM_CONNECTIONS = "num_connections"

# Deployments
REPLICAS_FIELD = "replicas"
AVAILABLE_REPLICAS_FIELD = "availableReplicas"
READY_REPLICAS_FIELD = "readyReplicas"
UPDATED_REPLICAS_FIELD = "updatedReplicas"

# Deviations
CHECKSUM_FIELD = "checksum"

# Nodes
NODE_INFO_FIELD = "nodeInfo"
KUBELET_VERSION_FIELD = "kubeletVersion"

# Pods
CONTAINER_STATUSES_FIELD = "containerStatuses"

# Processes
NAME_FIELD = "name"
EXE_FIELD = "exe"
ID_FIELD = "id"
EUSER_FIELD = "euser"
CHILDREN_FIELD = "children"
LISTENING_SOCKETS = "listeningSockets"

# Container
CONTAINER_NAME_FIELD = "containerName"
CONTAINER_ID_FIELD = "containerID"
CONTAINER_AGE = "age"
CONTAINER_IMAGE_NAME = "image-name"
# Backend Container Fields
BE_CONTAINER_IMAGE = "image"
BE_CONTAINER_IMAGE_ID = "image_id"
BE_CONTAINER_NAME = "container_name"
BE_CONTAINER_ID = "container_id"

# Agents
AGENT_HEALTH_CRIT = "Critical"
AGENT_HEALTH_DEL = "Deleted"
AGENT_HEALTH_ERR = "Error"
AGENT_HEALTH_NORM = "Normal"
AGENT_HEALTH_OFFLINE = "Offline"
AGENT_HEALTH_RESTARTED = "Restarted"
AGENT_HEALTH_RESTARTING = "Restarting"
AGENT_HEALTH_STARTED = "Started"
AGENT_HEALTH_STARTING = "Starting"
AGENT_HEALTH_WARN = "Warning"
HEALTH_PRIORITY = {
    AGENT_HEALTH_CRIT: 20,
    AGENT_HEALTH_ERR: 30,
    AGENT_HEALTH_WARN: 40,
    AGENT_HEALTH_NORM: 50,
    AGENT_HEALTH_OFFLINE: 10,
    AGENT_HEALTH_RESTARTED: 70,
    AGENT_HEALTH_RESTARTING: 60,
    AGENT_HEALTH_STARTED: 90,
    AGENT_HEALTH_STARTING: 80,
    AGENT_HEALTH_DEL: 100,
}
AGENT_STATUS = "status"
AGENT_HOSTNAME = "hostname"
AGENT_ID = "id"
AGENT_BAT_STATUSES = "bat_statuses"

# Spydertraces
BE_TRIGGER_NAME = "trigger_short_name"
BE_SCORE = "score"
BE_SUPPRESSED = "suppressed"
BE_ROOT_PROC_NAME = "root_proc_name"
BE_UNIQUE_FLAG_COUNT = "unique_flag_count"
BE_OBJECT_COUNT = "object_count"
BE_PROCESSES = "processes"
BE_DEPTH = "depth"
BE_SYSTEMS = "machines"
BE_CONNECTIONS = "connections"

# Network
CIDR_FIELD = "cidr"
EGRESS_FIELD = "egress"
EXCEPT_FIELD = "except"
FROM_FIELD = "from"
INGRESS_FIELD = "ingress"
IP_BLOCK_FIELD = "ipBlock"
PORTS_FIELD = "ports"
PORT_FIELD = "port"
ENDPORT_FIELD = "endPort"
PROCESSES_FIELD = "processes"
PROTO_FIELD = "protocol"
TO_FIELD = "to"


# Notifications
NOTIF_TYPE_ALL = "all"
NOTIF_TYPE_OBJECT = "object"
NOTIF_TYPE_METRICS = "metrics"
NOTIF_TYPE_DASHBOARD = "dashboard"
NOTIF_TYPES = [
    NOTIF_TYPE_ALL,
    NOTIF_TYPE_OBJECT,
    NOTIF_TYPE_METRICS,
    NOTIF_TYPE_DASHBOARD,
]
NOTIF_TYPE_FIELD = "type"
NOTIF_TMPL_TYPES = ["agent-health", "security", "operations", "guardian"]
NOTIF_TMPL_MAP = {
    "agent-health": "agent_health",
    "security": "security",
    "operations": "operations",
    "guardian": "guardian",
}
DST_TYPE_ORG = "org_uid"
DST_TYPE_EMAIL = "emails"
DST_TYPE_SLACK = "slack"
DST_TYPE_SNS = "sns"
DST_TYPE_USERS = "users"
DST_TYPE_WEBHOOK = "webhook"
DST_NAME_EMAIL = "Email"
DST_NAME_SLACK = "Slack"
DST_NAME_SNS = "SNS"
DST_NAME_WEBHOOK = "Webhook"
DST_TYPES = [
    DST_TYPE_EMAIL,
    DST_TYPE_SLACK,
    DST_TYPE_SNS,
    DST_TYPE_WEBHOOK,
]
DST_NAMES = [
    DST_NAME_EMAIL,
    DST_NAME_SLACK,
    DST_NAME_SNS,
    DST_NAME_WEBHOOK,
]
DST_NAME_TO_TYPE = {
    DST_NAME_EMAIL: DST_TYPE_EMAIL,
    DST_NAME_SLACK: DST_TYPE_SLACK,
    DST_NAME_SNS: DST_TYPE_SNS,
    DST_NAME_WEBHOOK: DST_TYPE_WEBHOOK,
}
DST_TYPE_TO_NAME = {
    DST_TYPE_EMAIL: DST_NAME_EMAIL,
    DST_TYPE_SLACK: DST_NAME_SLACK,
    DST_TYPE_SNS: DST_NAME_SNS,
    DST_TYPE_WEBHOOK: DST_NAME_WEBHOOK,
}
DST_TYPE_TO_DESC = {
    DST_TYPE_EMAIL: "A list of email addresses to send notifications to.",
    DST_TYPE_SLACK: "A Slack hook URL to send notifications to.",
    DST_TYPE_SNS: "An AWS sns endpoint to send notifications to.",
    DST_TYPE_WEBHOOK: "A generic webhook URL to send notifications to.",
}
ROUTES_FIELD = "routes"
TARGETS_FIELD = "targets"
DST_DESCRIPTION = "description"
DST_DATA = "data"
DST_SNS_TOPIC_ARN = "sns_topic_arn"
DST_SNS_CROSS_ACCOUNT_ROLE = "cross_account_iam_role"
DST_WEBHOOK_URL = "url"
DST_WEBHOOK_TLS_VAL = "no_tls_validation"
DST_SLACK_URL = "url"
ROUTE_TARGETS = "targets"
ROUTE_DESTINATION = "destination"
ROUTE_DATA = "data"
ROUTE_DATA_ANA_SETTINGS = "analyticsSettings"
ROUTE_DESCRIPTION = "description"
ROUTE_EXPR = "expr"
TGT_DESCRIPTION_FIELD = "description"
TMPL_DESCRIPTION_FIELD = "description"
TMPL_CONFIG_VALUES_FIELD = "configValues"

NOTIF_ADDITIONAL_FIELDS = "additionalFields"
NOTIF_DST_TGTS = "targets"
NOTIF_DATA_FIELD = "data"
NOTIF_CONDITION_FIELD = "condition"
NOTIF_COOLDOWN_FIELD = "cooldown"
NOTIF_COOLDOWN_BY_FIELD_FIELD = "byField"
NOTIF_COOLDOWN_SECONDS_FIELD = "forSeconds"
NOTIF_FOR_DURATION_FIELD = "forDuration"
NOTIF_SETTINGS_FIELD = "analyticsConfiguration"
NOTIF_NAME_FIELD = "name"
NOTIF_INTERVAL_FIELD = "interval"
NOTIF_TITLE_FIELD = "title"
NOTIF_MESSAGE_FIELD = "message"
NOTIF_ICON_FIELD = "icon"
NOTIF_NOTIFY_FIELD = "notify"
NOTIF_CREATE_TIME = "createTime"
NOTIF_LAST_UPDATED = "lastUpdated"
NOTIF_TEMPLATE_FIELD = "template"
NOTIF_TARGET_FIELD = "target"
NOTIF_DEFAULT_SCHEMA = "schemaType"
NOTIF_SUB_SCHEMA = "subSchema"
ANA_NOTIF_TYPE_AGENT_HEALTH = "agent_health"
ANA_NOTIF_TYPE_CUSTOM = "custom"


def get_dst_type(name):
    return DST_NAME_TO_TYPE[name]


def get_dst_name(type):
    return DST_NAME_TO_TYPE[type]


# Flags
FLAG_CLASS = "class"

# Output
OUTPUT_YAML = "yaml"
OUTPUT_JSON = "json"
OUTPUT_DEFAULT = "default"
OUTPUT_RAW = "raw"
OUTPUT_WIDE = "wide"
# used internally when updating objects directly via the API
OUTPUT_API = "api"
OUTPUT_CHOICES = [OUTPUT_YAML, OUTPUT_JSON, OUTPUT_DEFAULT]
OUTPUT_DEST_DEFAULT = "default"  # stdout
OUTPUT_DEST_FILE = "file"
OUTPUT_DEST_API = "api"
OUTPUT_DEST_STDOUT = "stdout"
OUTPUT_DEST_PAGER = "pager"

# spyctl Options
CLUSTER_OPTION = "cluster"
NAMESPACE_OPTION = "namespace"

# deviations
DEVIATION_FIELD = "deviation"
DEVIATION_DESCRIPTION = "deviationDescription"

# Templates
METADATA_NAME_TEMPLATE = "foobar-policy"

CONTAINER_SELECTOR_TEMPLATE = {
    IMAGE_FIELD: "foo",
    IMAGEID_FIELD: "sha256:bar",
    CONT_NAME_FIELD: "/foobar",
}
SVC_SELECTOR_TEMPLATE = {CGROUP_FIELD: "systemd:/system.slice/foobar.service"}
PROCESS_POLICY_TEMPLATE = [
    {
        NAME_FIELD: "foo",
        EXE_FIELD: ["/usr/bin/foo", "/usr/sbin/foo"],
        ID_FIELD: "foo_0",
        EUSER_FIELD: ["root"],
        CHILDREN_FIELD: [
            {NAME_FIELD: "bar", EXE_FIELD: ["/usr/bin/bar"], ID_FIELD: "bar_0"}
        ],
    }
]
NETWORK_POLICY_TEMPLATE = {
    INGRESS_FIELD: [
        {
            FROM_FIELD: [
                {
                    IP_BLOCK_FIELD: {
                        CIDR_FIELD: "0.0.0.0/0",
                    }
                }
            ],
            PORTS_FIELD: [{PROTO_FIELD: "TCP", PORT_FIELD: 1337}],
            PROCESSES_FIELD: ["foo_0"],
        }
    ],
    EGRESS_FIELD: [
        {
            TO_FIELD: [{DNS_SELECTOR_FIELD: ["foobar.com"]}],
            PORTS_FIELD: [{PROTO_FIELD: "TCP", PORT_FIELD: 1337}],
            PROCESSES_FIELD: ["bar_0"],
        }
    ],
}
DEFAULT_ACTION_TEMPLATE = {ACTION_MAKE_REDFLAG: {FLAG_SEVERITY: S_HIGH}}
RESPONSE_ACTION_TEMPLATE = {
    RESP_DEFAULT_FIELD: [DEFAULT_ACTION_TEMPLATE],
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


def valid_api_version(api_ver: str) -> bool:
    return api_ver == API_VERSION


def valid_kind(rec_kind, kind):
    return rec_kind == kind


def walk_up_tree(
    global_path: Path, local_path: Path, cwd: Path = None
) -> List[Tuple[Path, Dict]]:
    """Walks up the directory tree from cwd joining each directory with
    local_path. If a local_path file exists, loads the file and appends
    it to the return value. Finally, the file at global_path is loaded.

    Returns:
        List[Dict]: List of tuples (strpath, filedata). List[0] is the
        most specific local file. List[-1] is the global
        file if one exists.
    """
    rv = []
    if cwd is None:
        cwd = Path.cwd()
    config_path = Path.joinpath(cwd, local_path)
    if Path.is_file(config_path):
        conf = load_file(config_path)
        if conf is not None:
            rv.append((config_path, conf))
    for parent in cwd.parents:
        config_path = Path.joinpath(parent, local_path)
        if Path.is_file(config_path):
            conf = load_file(config_path)
            if conf is not None:
                rv.append((config_path, conf))
    if Path.is_file(global_path):
        conf = load_file(global_path)
        if conf is not None:
            rv.append((global_path, conf))
    return rv


def load_file(path: Path):
    try:
        with path.open("r") as f:
            try:
                file_data = yaml.load(f, yaml.Loader)
            except Exception:
                try:
                    file_data = json.load(f)
                except Exception:
                    try_log(
                        f"Unable to load file at {str(path)}."
                        f" Is it valid yaml or json?"
                    )
                return None
    except IOError:
        try_log(f"Unable to read file at {str(path)}. Check permissions.")
    return file_data


class CustomGroup(click.Group):
    SECTION_BASIC = "Basic Commands"
    SECTION_ALERT_MGMT = "Alert Management"
    SECTION_OTHER = "Other Commands"
    command_sections = [SECTION_BASIC, SECTION_ALERT_MGMT, SECTION_OTHER]
    cmd_to_section_map = {
        "apply": SECTION_BASIC,
        "create": SECTION_BASIC,
        "close": SECTION_ALERT_MGMT,
        "delete": SECTION_BASIC,
        "diff": SECTION_BASIC,
        "get": SECTION_BASIC,
        "merge": SECTION_BASIC,
        "snooze": SECTION_ALERT_MGMT,
        "suppress": SECTION_ALERT_MGMT,
        "validate": SECTION_BASIC,
    }

    def format_help(
        self, ctx: click.Context, formatter: click.HelpFormatter
    ) -> None:
        self.format_help_text(ctx, formatter)
        self.format_options(ctx, formatter)
        self.format_usage(ctx, formatter)
        self.format_epilog(ctx, formatter)

    def format_help_text(
        self, ctx: click.Context, formatter: click.HelpFormatter
    ) -> None:
        text = self.help if self.help is not None else ""

        if text:
            text = inspect.cleandoc(text).partition("\f")[0]
            formatter.write_paragraph()
            formatter.write_text(text)

    def format_usage(
        self, ctx: click.Context, formatter: click.HelpFormatter
    ) -> None:
        formatter.write_paragraph()
        formatter.write_text("Usage:")
        formatter.indent()
        formatter.write_text("spyctl [command] [options]")
        formatter.dedent()

    def format_epilog(
        self, ctx: click.Context, formatter: click.HelpFormatter
    ) -> None:
        """Writes the epilog into the formatter if it exists."""
        if self.epilog:
            epilog = inspect.cleandoc(self.epilog)
            formatter.write_paragraph()
            formatter.write_text(epilog)

    def format_commands(
        self, ctx: click.Context, formatter: click.HelpFormatter
    ) -> None:
        commands = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            # What is this, the tool lied about a command.  Ignore it
            if cmd is None:
                continue
            if cmd.hidden:
                continue

            commands.append((subcommand, cmd))

        # allow for 3 times the default spacing
        if len(commands):
            limit = formatter.width - 6 - max(len(cmd[0]) for cmd in commands)

            sections: Dict[str, List] = {}
            for section_title in self.command_sections:
                sections.setdefault(section_title, [])
            for subcommand, cmd in commands:
                section_title = self.cmd_to_section_map.get(subcommand)
                if not section_title:
                    section_title = self.SECTION_OTHER
                help = cmd.get_short_help_str(limit)
                sections[section_title].append((subcommand, help))

            for title, rows in sections.items():
                if rows:
                    with formatter.section(title):
                        formatter.write_dl(rows, col_spacing=4)


class CustomSubGroup(click.Group):
    def group(self, *args, **kwargs):
        """Behaves the same as `click.Group.group()` except if passed
        a list of names, all after the first will be aliases for the first.
        """

        def decorator(f):
            aliased_group = []
            if isinstance(args[0], list):
                # we have a list so create group aliases
                _args = [args[0][0]] + list(args[1:])
                for alias in args[0][1:]:
                    grp = super(CustomSubGroup, self).group(
                        alias, *args[1:], **kwargs
                    )(f)
                    grp.short_help = "Alias for '{}'".format(_args[0])
                    aliased_group.append(grp)
            else:
                _args = args

            # create the main group
            grp = super(CustomSubGroup, self).group(*_args, **kwargs)(f)

            # for all of the aliased groups, share the main group commands
            for aliased in aliased_group:
                aliased.commands = grp.commands

            return grp

        return decorator

    def format_help(
        self, ctx: click.Context, formatter: click.HelpFormatter
    ) -> None:
        self.format_help_text(ctx, formatter)
        self.format_options(ctx, formatter)
        self.format_usage(ctx, formatter)
        self.format_epilog(ctx, formatter)

    def format_help_text(
        self, ctx: click.Context, formatter: click.HelpFormatter
    ) -> None:
        text = self.help if self.help is not None else ""

        if text:
            text = inspect.cleandoc(text).partition("\f")[0]
            formatter.write_paragraph()
            formatter.write_text(text)

    def format_usage(
        self, ctx: click.Context, formatter: click.HelpFormatter
    ) -> None:
        formatter.write_paragraph()
        prefix = "Usage:\n  "
        pieces = self.collect_usage_pieces(ctx)
        formatter.write_usage(
            ctx.command_path, " ".join(pieces), prefix=prefix
        )
        formatter.dedent()

    def format_epilog(
        self, ctx: click.Context, formatter: click.HelpFormatter
    ) -> None:
        """Writes the epilog into the formatter if it exists."""
        if self.epilog:
            epilog = inspect.cleandoc(self.epilog)
            formatter.write_paragraph()
            formatter.write_text(epilog)

    def format_commands(
        self, ctx: click.Context, formatter: click.HelpFormatter
    ) -> None:
        commands = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            # What is this, the tool lied about a command.  Ignore it
            if cmd is None:
                continue
            if cmd.hidden:
                continue

            commands.append((subcommand, cmd))

        # allow for 3 times the default spacing
        if len(commands):
            limit = formatter.width - 6 - max(len(cmd[0]) for cmd in commands)

            rows = []
            for subcommand, cmd in commands:
                help = cmd.get_short_help_str(limit)
                rows.append((subcommand, help))

            if rows:
                with formatter.section("Available Commands"):
                    formatter.write_dl(rows, col_spacing=4)


class CustomCommand(click.Command):
    def format_help(
        self, ctx: click.Context, formatter: click.HelpFormatter
    ) -> None:
        self.format_help_text(ctx, formatter)
        self.format_options(ctx, formatter)
        self.format_usage(ctx, formatter)
        self.format_epilog(ctx, formatter)

    def format_help_text(
        self, ctx: click.Context, formatter: click.HelpFormatter
    ) -> None:
        text = self.help if self.help is not None else ""

        if text:
            text = inspect.cleandoc(text).partition("\f")[0]
            formatter.write_paragraph()
            formatter.write_text(text)

    def format_usage(
        self, ctx: click.Context, formatter: click.HelpFormatter
    ) -> None:
        formatter.write_paragraph()
        prefix = "Usage:\n  "
        pieces = self.collect_usage_pieces(ctx)
        formatter.write_usage(
            ctx.command_path, " ".join(pieces), prefix=prefix
        )
        formatter.dedent()

    def format_epilog(
        self, ctx: click.Context, formatter: click.HelpFormatter
    ) -> None:
        """Writes the epilog into the formatter if it exists."""
        if self.epilog:
            epilog = inspect.cleandoc(self.epilog)
            formatter.write_paragraph()
            formatter.write_text(epilog)


class ArgumentParametersCommand(CustomCommand):
    argument_value_parameters = []
    argument_name = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_param_count = len(self.params)
        self.argument_value = self.argument_name
        self.unspecific = True

    def parse_args(self, ctx, args: List[str]) -> List[str]:
        self.__reset_params()
        args_cpy = args.copy()
        parser = self.make_parser(ctx)
        parser.ignore_unknown_options = True
        opts, args_cpy, param_order = parser.parse_args(args=args_cpy)
        for param in self.get_params(ctx):
            if param.name == self.argument_name:
                try:
                    param.handle_parse_result(ctx, opts, args_cpy)
                except Exception:
                    pass
                break
        argument_value = ctx.params.get(self.argument_name)
        if argument_value:
            self.unspecific = False
            for obj in self.argument_value_parameters:
                for value_option in obj[self.argument_name]:
                    if argument_value == value_option:
                        self.argument_value = str(value_option)
                        for arg_maker in obj["args"]:
                            arg_maker(self)
                        break
        return super().parse_args(ctx, args)

    def format_options(self, ctx, formatter):
        """Writes all the options into the formatter if they exist."""
        opts = []
        specif_opts = []
        specific_index = {}
        if self.unspecific:
            for obj in self.argument_value_parameters:
                index = ", ".join(
                    str(option) for option in obj[self.argument_name]
                )
                specific_index[index] = len(obj["args"])
                for arg_maker in obj["args"]:
                    arg_maker(self)
        for i, param in enumerate(self.get_params(ctx)):
            rv = param.get_help_record(ctx)
            if rv is not None:
                if i < self.base_param_count:
                    opts.append(rv)
                else:
                    specif_opts.append(rv)

        if opts:
            with formatter.section("Options"):
                formatter.write_dl(opts)
        if specif_opts:
            if self.unspecific:
                index = 0
                for options, num in specific_index.items():
                    with formatter.section(f"Options for {options}"):
                        formatter.write_dl(
                            specif_opts[index : index + num]  # noqa E203
                        )
                    index = index + num
            else:
                with formatter.section(f"Options for {self.argument_value}"):
                    formatter.write_dl(specif_opts)

    def __reset_params(self):
        self.params = self.params[: self.base_param_count]


class MutuallyExclusiveOption(click.Option):
    def __init__(self, *args, **kwargs):
        self.mutually_exclusive = set(kwargs.pop("mutually_exclusive", []))
        help = kwargs.get("help", "")
        if self.mutually_exclusive:
            ex_str = ", ".join(self.mutually_exclusive)
            kwargs["help"] = help + (
                " This argument is mutually exclusive with "
                " arguments: [" + ex_str + "]."
            )
        super(MutuallyExclusiveOption, self).__init__(*args, **kwargs)

    def handle_parse_result(self, ctx, opts, args):
        if self.mutually_exclusive.intersection(opts) and self.name in opts:
            raise click.UsageError(
                f"Illegal usage: `{self.name}` is mutually exclusive with "
                f"arguments `{', '.join(self.mutually_exclusive)}`."
            )
        return super(MutuallyExclusiveOption, self).handle_parse_result(
            ctx, opts, args
        )


class OptionEatAll(click.Option):
    # https://stackoverflow.com/questions/48391777/nargs-equivalent-for-options-in-click  # noqa E501

    def __init__(self, *args, **kwargs):
        self.save_other_options = kwargs.pop("save_other_options", True)
        nargs = kwargs.pop("nargs", -1)
        assert nargs == -1, "nargs, if set, must be -1 not {}".format(nargs)
        super(OptionEatAll, self).__init__(*args, **kwargs)
        self._previous_parser_process = None
        self._eat_all_parser = None

    def add_to_parser(self, parser, ctx):
        def parser_process(value, state):
            # method to hook to the parser.process
            done = False
            value = [value]
            if self.save_other_options:
                # grab everything up to the next option
                while state.rargs and not done:
                    for prefix in self._eat_all_parser.prefixes:
                        if state.rargs[0].startswith(prefix):
                            done = True
                    if not done:
                        value.append(state.rargs.pop(0))
            else:
                # grab everything remaining
                value += state.rargs
                state.rargs[:] = []
            value = tuple(value)

            # call the actual process
            self._previous_parser_process(value, state)

        retval = super(OptionEatAll, self).add_to_parser(parser, ctx)
        for name in self.opts:
            our_parser = parser._long_opt.get(name) or parser._short_opt.get(
                name
            )
            if our_parser:
                self._eat_all_parser = our_parser
                self._previous_parser_process = our_parser.process
                our_parser.process = parser_process
                break
        return retval


class MutuallyExclusiveEatAll(MutuallyExclusiveOption, OptionEatAll):
    def __init__(self, *args, **kwargs):
        self.mutually_exclusive = set(kwargs.pop("mutually_exclusive", []))
        help = kwargs.get("help", "")
        if self.mutually_exclusive:
            ex_str = ", ".join(self.mutually_exclusive)
            kwargs["help"] = help + (
                " This argument is mutually exclusive with "
                " arguments: [" + ex_str + "]."
            )
        self.save_other_options = kwargs.pop("save_other_options", True)
        nargs = kwargs.pop("nargs", -1)
        assert nargs == -1, "nargs, if set, must be -1 not {}".format(nargs)
        self._previous_parser_process = None
        self._eat_all_parser = None
        super(MutuallyExclusiveEatAll, self).__init__(*args, **kwargs)


def try_log(*args, **kwargs):
    global LOG_VAR
    try:
        if kwargs.pop(WARNING_MSG, False):
            msg = f"{WARNING_COLOR}{' '.join(args)}{COLOR_END}"
            if USE_LOG_VARS:
                LOG_VAR.append(msg)
            print(msg, **kwargs, file=sys.stderr)
        else:
            msg = " ".join(args)
            if USE_LOG_VARS:
                LOG_VAR.append(msg)
            print(*args, **kwargs, file=sys.stderr)
        sys.stderr.flush()
    except BrokenPipeError:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stderr.fileno())
        err_exit("Broken Pipe")


def api_log(*args, **kwargs):
    global LOG_VAR
    try:
        if kwargs.pop(WARNING_MSG, False):
            msg = f"{WARNING_COLOR}{' '.join(args)}{COLOR_END}"
            print(msg, **kwargs, file=sys.stderr)
        else:
            print(*args, **kwargs, file=sys.stderr)
        sys.stderr.flush()
    except BrokenPipeError:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stderr.fileno())
        err_exit("Broken Pipe")


def time_inp(time_str: str, cap_one_day=False) -> Optional[int]:
    if time_str is None:
        return None
    past_seconds = 0
    epoch_time = None
    try:
        try:
            epoch_time = int(time_str)
        except ValueError:
            if time_str.endswith(("s", "sc")):
                past_seconds = int(time_str.split("s")[0])
            elif time_str.endswith(("m", "mn")):
                past_seconds = int(time_str.split("m")[0]) * 60
            elif time_str.endswith(("h", "hr")):
                past_seconds = int(time_str.split("h")[0]) * 60 * 60
            elif time_str.endswith(("d", "dy")):
                past_seconds = int(time_str.split("d")[0]) * 60 * 60 * 24
            elif time_str.endswith(("w", "wk")):
                past_seconds = int(time_str.split("w")[0]) * 60 * 60 * 24 * 7
            else:
                date = dateparser.parse(time_str)
                date = date.replace(tzinfo=date.tzinfo or timezone.utc)
                past_seconds = int(time.time()) - date.timestamp()
    except (ValueError, dateparser.ParserError):
        raise ValueError("invalid time input (see documentation)") from None
    now = time.time()
    one_day_ago = now - 86400
    if epoch_time is not None:
        if epoch_time > now:
            raise ValueError("time must be in the past")
        if epoch_time < one_day_ago and cap_one_day:
            epoch_time = one_day_ago
        return epoch_time
    else:
        if past_seconds < 0:
            raise ValueError("time must be in the past")
        if past_seconds > 86400 and cap_one_day:
            past_seconds = 86400
        return int(now - past_seconds)


def selectors_to_filters(resource: Dict, **filters) -> Dict:
    """Generates filters based on the selectors found in a resource's
    spec field. Does not overwrite filters inputted from cmdline. Does
    overwrite filters from current-context.

    Args:
        resource (Dict): A dictionary containing data for a given
            resource.

    Returns:
        Dict: A dictionary of filters build from a resource's selectors.
    """
    if not isinstance(resource, dict):
        try_log("Unable to find selectors, resource is not a dictionary")
        return filters
    spec = resource.get(SPEC_FIELD, {})
    if not isinstance(spec, dict):
        try_log("Unable to find selectors, spec is not a dictionary")
        return filters
    rv: Dict = copy.deepcopy(spec.get(CONT_SELECTOR_FIELD, {}))
    rv.update(copy.deepcopy(spec.get(SVC_SELECTOR_FIELD, {})))
    namespace_labels = copy.deepcopy(
        spec.get(NAMESPACE_SELECTOR_FIELD, {}).get(MATCH_LABELS_FIELD, {})
    )
    if namespace_labels:
        rv.update({NAMESPACE_LABELS_FIELD: namespace_labels})
    pod_labels = copy.deepcopy(
        spec.get(POD_SELECTOR_FIELD, {}).get(MATCH_LABELS_FIELD, {})
    )
    if pod_labels:
        rv.update({POD_LABELS_FIELD: pod_labels})
    rv.update(filters)
    return rv


def label_input_to_dict(input: Union[str, List[str], Dict]) -> Optional[Dict]:
    in_str = " in "
    notin_str = " notin "

    def parse_str_input(inp: str) -> Optional[Dict]:
        def parse_only_key(key_inp: str) -> Optional[Dict]:
            key_inp = key_inp.strip(" ")
            if " " in key_inp:
                return None
            return {key_inp: "*"}

        def parse_equality_based(eq_inp: str) -> Optional[Dict]:
            rv = {}
            kv_pairs = eq_inp.split(",")
            for pair in kv_pairs:
                try:
                    k, v = pair.split("=")
                    k = k.strip(" ")
                    v = v.strip(" ")
                    rv[k] = v
                except Exception:
                    only_key = parse_only_key(pair)
                    if not only_key:
                        try_log(
                            f"{pair} is an invalid format. Use 'key=value' or"
                            " only 'key'",
                            is_warning=True,
                        )
                        return None
                    rv.update(only_key)
            if not rv:
                return None
            return rv

        def parse_set_based(set_inp) -> Optional[Dict]:
            rv = {}
            import re

            # split input on commas not in parenthesis
            pat = re.compile(r",(?![^(]*\))")
            for set_str in re.split(pat, set_inp):
                if in_str in set_str:
                    try:
                        k, s = set_str.split(in_str)
                        s = s.replace("(", "").replace(")", "").split(",")
                        s = [
                            value.strip(" ") for value in s if value.strip(" ")
                        ]
                        if not s:
                            try_log(
                                f"{set_str} cannot contain an empty",
                                is_warning=True,
                            )
                            return None
                        if len(s) == 1:
                            s = s[0]
                        rv[k] = s
                    except Exception:
                        try_log(
                            f"{set_str} is an invalid format use 'key in"
                            " (value1,value2)' or only 'key'",
                            is_warning=True,
                        )
                        return None
                else:
                    only_key = parse_only_key(set_str)
                    if not only_key:
                        try_log(
                            f"{set_str} is an invalid format use 'key in"
                            " (value1,value2)' or only 'key'",
                            is_warning=True,
                        )
                        return None
                    rv.update(only_key)
            if not rv:
                return None
            return rv

        rv = None
        if "=" in inp:
            rv = parse_equality_based(inp)
        elif in_str in inp:
            if notin_str in inp:
                try_log("notin not supported", is_warning=True)
                return None
            rv = parse_set_based(inp)
        elif notin_str in inp:
            if notin_str in inp:
                try_log("notin not supported", is_warning=True)
                return None
        else:
            rv = {}
            only_keys = inp.split(",")
            for key in only_keys:
                parsed_key = parse_only_key(key)
                if parsed_key is None:
                    return None
                rv.update(parsed_key)
        if not rv:
            return None
        return rv

    rv = {}
    if isinstance(input, str):
        parsed = parse_str_input(input)
        if not parsed:
            return None
        rv.update(parsed)
    elif isinstance(input, list):
        for item in input:
            if not isinstance(item, str):
                try_log(
                    f"label list contains items other than a string. {input}",
                    is_warning=True,
                )
                return None
            parsed = parse_str_input(item)
            if not parsed:
                return None
            rv.update(parsed)
    elif isinstance(input, dict):
        if not input:
            return None
        rv.update(input)
    else:
        try_log("label input is not str, list, or dict", is_warning=True)
        return None
    if not rv:
        return None
    return rv


def make_uuid():
    return b64url(uuid4().bytes).decode("ascii").strip("=")


def err_exit(message: str, exception: Exception = None):
    if API_CALL or INTERACTIVE:
        raise Exception(f"{WARNING_COLOR}Error: {message}{COLOR_END}")
    sys.exit(f"{WARNING_COLOR}Error: {message}{COLOR_END}")


def dict_raise_on_duplicates(ordered_pairs):
    """Reject duplicate keys.

    source: https://stackoverflow.com/questions/14902299/json-loads-allows-duplicate-keys-in-a-dictionary-overwriting-the-first-value # noqa E501
    """
    d = {}
    for k, v in ordered_pairs:
        if k in d:
            raise ValueError(f"Duplicate {k!r} key found in JSON.")
        else:
            d[k] = v
    return d


class UniqueKeyLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        mapping = set()
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in mapping:
                raise ValueError(
                    f"Duplicate key {key!r} found in {self.name!r}."
                )
            mapping.add(key)
        return super().construct_mapping(node, deep)


def load_resource_file(file: Union[str, IO], validate_cmd: bool = False):
    try:
        name, resrc_data = __load_yaml_file(file)
    except ValueError as e:
        if validate_cmd:
            try_log(" ".join(e.args))
            sys.exit(0)
        err_exit(" ".join(e.args))
    except Exception as e:
        if file.name.endswith(".yaml"):
            err_exit("Error decoding yaml" + str(e.args))
        try:
            name, resrc_data = __load_json_file(file)
        except json.JSONDecodeError as e:
            if validate_cmd:
                try_log("Error decoding json" + " ".join(e.args))
                sys.exit(0)
            err_exit("Error decoding json" + " ".join(e.args))
        except ValueError as e:
            if validate_cmd:
                try_log(" ".join(e.args))
                sys.exit(0)
            err_exit(" ".join(e.args))
        except Exception:
            err_exit("Unable to load resource file.")
    __validate_data_structure_on_load(resrc_data, validate_cmd)
    if isinstance(resrc_data, dict):
        __validate_resource_on_load(resrc_data, name, validate_cmd)
    else:
        for i, data in enumerate(resrc_data):
            __validate_resource_on_load(data, name, validate_cmd, index=i)
    if isinstance(file, io.TextIOWrapper):
        file.seek(0, 0)
    return resrc_data


def __validate_data_structure_on_load(resrc_data: Any, validate_cmd=False):
    if not isinstance(resrc_data, dict) and not isinstance(resrc_data, list):
        if validate_cmd:
            try_log(
                "Resource file does not contain a dictionary or list of"
                " dictionaries."
            )
            sys.exit(0)
        err_exit(
            "Resource file does not contain a dictionary or list of"
            " dictionaries."
        )


def __validate_resource_on_load(
    resrc_data: Dict, name, validate_cmd=False, index=None
):
    msg_suffix = "" if index is None else f" at index {index}"
    from spyctl.schemas_v2 import valid_object

    if not valid_object(resrc_data, verbose=True):
        if validate_cmd:
            try_log(f"Invalid object in {name!r}{msg_suffix}. See error logs.")
            sys.exit(0)
        err_exit(f"Invalid object in {name!r}{msg_suffix}. See error logs.")


def __load_yaml_file(file: Union[str, IO]) -> Tuple[str, Any]:
    try:
        if isinstance(file, io.TextIOWrapper):
            name = file.name
            resrc_data = yaml.load(file, UniqueKeyLoader)
        else:
            name = file
            with open(file) as f:
                resrc_data = yaml.load(f, UniqueKeyLoader)
    except IOError as e:
        err_exit(" ".join(e.args))
    return name, resrc_data


def __load_json_file(file: Union[str, IO]) -> Tuple[str, Any]:
    try:
        if isinstance(file, io.TextIOWrapper):
            name = file.name
            resrc_data = json.load(
                file, object_pairs_hook=dict_raise_on_duplicates
            )
        else:
            name = file
            with open(file) as f:
                resrc_data = json.load(
                    f, object_pairs_hook=dict_raise_on_duplicates
                )
    except IOError as e:
        err_exit(" ".join(e.args))
    return name, resrc_data


def dictionary_mod(fn) -> Dict:
    def wrapper(obj_list, fields: Union[List[str], str] = None) -> Dict:
        ret = dict()
        if fields is not None:
            if isinstance(fields, str):
                fields = [fields]
            fn(obj_list, ret, fields)
        else:
            fn(obj_list, ret)
        return ret

    return wrapper


def to_timestamp(zulu_str):
    try:
        return zulu.Zulu.parse(zulu_str).timestamp()
    except Exception:
        return zulu_str


def epoch_to_zulu(epoch):
    try:
        return (
            zulu.Zulu.fromtimestamp(epoch).format("YYYY-MM-ddTHH:mm:ss") + "Z"
        )
    except Exception:
        return epoch


def truncate_hour_epoch(input_epoch: float) -> float:
    rv = input_epoch - (input_epoch % 3600)
    return rv


def get_metadata_name(resource: Dict) -> Optional[str]:
    metadata = resource.get(METADATA_FIELD, {})
    name = metadata.get(METADATA_NAME_FIELD)
    return name


def get_metadata_type(resource: Dict) -> Optional[str]:
    metadata = resource.get(METADATA_FIELD, {})
    type = metadata.get(METADATA_TYPE_FIELD)
    return type


def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py  # noqa E501
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        value = (
            unicodedata.normalize("NFKD", value)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-_")


FILE_EXT_MAP = {
    OUTPUT_YAML: ".yaml",
    OUTPUT_JSON: ".json",
    OUTPUT_DEFAULT: ".yaml",
}


def find_resource_filename(data: Dict, default: str = "spyctl_output") -> str:
    """Checks metadata for a suitable filename, if not it
    resorts to the kind field lowercased and spaces removed.
    If all else fails, uses the default.

    Args:
        data (Dict): The resource that will be outputted
        default (str): Default string to use for filename if all else fails.

    Returns:
        str: A valid filename for use in saving data to disk.
    """
    rv = data.get(METADATA_FIELD, {}).get(METADATA_NAME_FIELD)
    if rv:
        rv = slugify(rv)
        rv.replace(" ", "_")
    if not rv:
        rv: str = data.get(KIND_FIELD)
        if rv:
            rv = rv.strip(" ").replace(" ", "_").lower()
    if not rv:
        rv = default
    return rv


def unique_fn(fn: str, output_format) -> Optional[str]:
    count = 1
    file_ext = FILE_EXT_MAP[output_format]
    try:
        filepath = Path(fn + file_ext)
        new_fn = fn
        while filepath.exists():
            new_fn = fn + f"_{count}"
            filepath = Path(new_fn + file_ext)
            count += 1
    except Exception:
        try_log(f"Unable to build unique filename for {fn}", is_warning=True)
        return
    return str(new_fn)


def make_checksum(dictionary: Dict) -> str:
    dict_str = json.dumps(dictionary, sort_keys=True)
    hash = md5(dict_str.encode("utf-8"))
    return hash.hexdigest()


def simple_glob_to_regex(input_str: str):
    rv = input_str.replace(".", "\\.")
    rv = rv.replace("^", "\\^")
    rv = rv.replace("$", "\\$")
    rv = rv.replace("*", ".*")
    rv = rv.replace("?", ".")
    rv = f"^{rv}$"
    return rv


def set_api_call():
    global API_CALL, USE_LOG_VARS
    API_CALL = True
    USE_LOG_VARS = True
    disable_colorization()


def set_interactive():
    global INTERACTIVE, USE_LOG_VARS
    INTERACTIVE = True
    USE_LOG_VARS = True
    disable_colorization()


def set_debug():
    global DEBUG
    DEBUG = True


def load_file_for_api_test(file: IO):
    try:
        _, resrc_data = __load_yaml_file(file)
    except ValueError as e:
        err_exit(" ".join(e.args))
    except Exception:
        try:
            _, resrc_data = __load_json_file(file)
        except json.JSONDecodeError as e:
            err_exit("Error decoding json" + " ".join(e.args))
        except ValueError as e:
            err_exit(" ".join(e.args))
        except Exception:
            err_exit("Unable to load resource file.")
    return resrc_data


def is_private_dns(hostname: str) -> bool:
    if hostname.endswith(".local"):
        return True
    return False


def is_public_dns(hostname: str) -> bool:
    if not is_private_dns(hostname):
        return True
    return False


def is_redirected() -> bool:
    return os.fstat(0) != os.fstat(1)


def calc_age(time_float: float):
    creation_timestamp = zulu.parse(time_float)
    age_delta = zulu.now() - creation_timestamp
    if age_delta.days > 0:
        age = f"{age_delta.days}d"
        return age
    elif age_delta.seconds >= 3600:
        age = f"{age_delta.seconds // 3600}h"
        return age
    else:
        age = f"{age_delta.seconds//60}m"
        return age


TGT_NAME_VALID_SYMBOLS = ["-", "_"]
NOTIF_NAME_VALID_SYMBOLS = ["-", "_"]

TGT_NAME_ERROR_MSG = (
    "Target name must contain only letters, numbers, and"
    f" {TGT_NAME_VALID_SYMBOLS}. It must also be less than 64"
    " characters."
)

NOTIF_CONF_NAME_ERROR_MSG = "Name must be less than 64 characters."


def is_valid_tgt_name(input_string):
    pattern = r"^[a-zA-Z0-9\-_]+$"

    if re.match(pattern, input_string) and len(input_string) <= 64:
        return True
    else:
        return False


def is_valid_notification_name(input_string) -> str:
    if len(input_string) <= 64:
        return True
    return False


def valid_notification_name(input_string) -> str:
    pattern = r"^[a-zA-Z0-9\-_]+$"
    if re.match(pattern, input_string) and len(input_string) <= 64:
        return input_string
    raise click.UsageError(
        "Notification name must contain only letters, numbers, and"
        f" {NOTIF_NAME_VALID_SYMBOLS}. It must also be less than 64"
        " characters."
    )


def valid_schema(input_string) -> str:
    if " " in input_string:
        raise click.UsageError("Schemas may not have spaces.")
    return input_string


def is_valid_email(email):
    # Define a regular expression pattern for a valid email address
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"

    # Use the re.match function to check if the email matches the pattern
    if re.match(pattern, email):
        return True
    else:
        return False


def is_valid_url(url):
    try:
        result = urlparse(url)
        return all(
            [result.scheme, result.netloc]
        )  # Check if both scheme and network location are present
    except ValueError:
        return False


def is_valid_slack_url(url: str):
    try:
        result = urlparse(url)
        if not all(
            [result.scheme, result.netloc]
        ):  # Check if both scheme and network location are present
            return False
        if not url.startswith("https://hooks.slack.com/services/"):
            return False
        return True
    except ValueError:
        return False


def encode_int(x, length=4):
    b = int(x).to_bytes(length, byteorder="big")
    return b64url(b).decode("ascii").strip("=")


def build_ctx() -> str:
    return f"{encode_int(time.time())}.{make_uuid()[:5]}"


def is_guardian_obj(obj: Dict):
    kind = obj.get(KIND_FIELD)
    type = obj.get(METADATA_FIELD, {}).get(METADATA_TYPE_FIELD)
    if kind in [BASELINE_KIND, POL_KIND] and type in GUARDIAN_POL_TYPES:
        return True
