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
ADD_COLOR = "\x1b[38;5;35m"
SUB_COLOR = "\x1b[38;5;203m"
COLOR_END = "\x1b[0m"
API_CALL = False
DEBUG = False
LOG_VAR = []
ERR_VAR = []
USE_LOG_VARS = False


def disable_colorization():
    global COLORIZE_OUTPUT, WARNING_COLOR, COLOR_END, ADD_COLOR, SUB_COLOR
    COLORIZE_OUTPUT = False
    WARNING_COLOR = ""
    COLOR_END = ""
    SUB_COLOR = ""
    ADD_COLOR = ""


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
CLUSTERS_RESOURCE = Aliases(
    ["clusters", "cluster", "clust", "clusts", "clus"], "cluster", "clusters"
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
DEPLOYMENTS_RESOURCE = Aliases(
    ["deployments", "deployment", "deploys", "deploy"],
    "deployment",
    "deployments",
)
NAMESPACES_RESOURCE = Aliases(
    ["namespaces", "name", "names", "namesp", "namesps", "namespace"],
    "namespace",
    "namespaces",
)
MACHINES_RESOURCE = Aliases(
    ["machines", "mach", "machs", "machine"],
    "machine",
    "machines",
)
NODES_RESOURCE = Aliases(["nodes", "node"], "node", "nodes")
PODS_RESOURCE = Aliases(["pods", "pod"], "pod", "pods")
REDFLAGS_RESOURCE = Aliases(["redflags", "redflag"], "redflag", "redflags")
OPSFLAGS_RESOURCE = Aliases(["opsflags", "opsflag"], "opsflag", "opsflags")
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
SPYDERTRACE_RESOURCE = Aliases(
    ["spydertrace", "spydertraces", "spyder", "trace", "traces"],
    "spydertrace",
    "spydertraces",
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
]
DESC_RESOURCES: List[str] = [
    POLICIES_RESOURCE.name,
]
GET_RESOURCES: List[str] = [
    CLUSTERS_RESOURCE.name_plural,
    CONNECTIONS_RESOURCE.name_plural,
    CONTAINER_RESOURCE.name_plural,
    DEPLOYMENTS_RESOURCE.name_plural,
    FINGERPRINTS_RESOURCE.name_plural,
    MACHINES_RESOURCE.name_plural,
    NAMESPACES_RESOURCE.name_plural,
    NODES_RESOURCE.name_plural,
    OPSFLAGS_RESOURCE.name_plural,
    PODS_RESOURCE.name_plural,
    POLICIES_RESOURCE.name_plural,
    PROCESSES_RESOURCE.name_plural,
    REDFLAGS_RESOURCE.name_plural,
    # SPYDERTRACE_SUMMARY_RESOURCE.name_plural,
    SUPPRESSION_POLICY_RESOURCE.name_plural,
    CONTAINER_RESOURCE.name_plural,
    SPYDERTRACE_RESOURCE.name_plural,
]
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


# Spyderbat Schema Prefix'
SCHEMA_FIELD = "schema"
EVENT_REDFLAG_PREFIX = "event_redflag"
EVENT_OPSFLAG_PREFIX = "event_opsflag"
MODEL_FINGERPRINT_PREFIX = "model_fingerprint"
MODEL_SPYDERTRACE_PREFIX = "model_spydertrace"
MODEL_FINGERPRINT_SUBTYPE_MAP = {
    "container": "container",
    "linux-service": "linux_svc",
}

# Datatypes for searching via API
DATATYPE_SPYDERGRAPH = "spydergraph"
DATATYPE_FINGERPRINTS = "fingerprints"

# Resource Kinds
POL_KIND = "SpyderbatPolicy"
SUP_POL_KIND_ALIAS = "SuppressionPolicy"
BASELINE_KIND = "SpyderbatBaseline"
FPRINT_KIND = "SpyderbatFingerprint"
FPRINT_GROUP_KIND = "FingerprintGroup"
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
SVC_SELECTOR_FIELD = "serviceSelector"
TRACE_SELECTOR_FIELD = "traceSelector"
USER_SELECTOR_FIELD = "userSelector"
MATCH_LABELS_FIELD = "matchLabels"
# Machine Selector Fields
HOSTNAME_FIELD = "hostname"
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
POL_TYPE_CONT = "container"
POL_TYPE_SVC = "linux-service"
POL_TYPE_TRACE = "trace"
SUPPRESSION_POL_TYPES = [POL_TYPE_TRACE]
GUARDIAN_POL_TYPES = [POL_TYPE_CONT, POL_TYPE_SVC]
POL_TYPES = [POL_TYPE_SVC, POL_TYPE_CONT, POL_TYPE_TRACE]
ENABLED_FIELD = "enabled"
IGNORE_PROCS_FIELD = "ignoreProcesses"
IGNORE_PROCS_ALL = "all"
IGNORE_PROCS_STRINGS = [IGNORE_PROCS_ALL]
IGNORE_CONNS_ALL = "all"
IGNORE_CONNS_INGRESS = "all-ingress"
IGNORE_CONNS_EGRESS = "all-egress"
IGNORE_CONNS_PRIVATE = "private"
IGNORE_CONNS_PRIVATE_E = "private-egress"
IGNORE_CONNS_PRIVATE_I = "private-ingress"
IGNORE_CONNS_PUBLIC = "public"
IGNORE_CONNS_PUBLIC_E = "public-egress"
IGNORE_CONNS_PUBLIC_I = "public-ingress"
IGNORE_CONN_STRINGS = [
    IGNORE_CONNS_ALL,
    IGNORE_CONNS_EGRESS,
    IGNORE_CONNS_INGRESS,
    IGNORE_CONNS_PRIVATE,
    IGNORE_CONNS_PRIVATE_E,
    IGNORE_CONNS_PRIVATE_I,
    IGNORE_CONNS_PUBLIC,
    IGNORE_CONNS_PUBLIC_E,
    IGNORE_CONNS_PUBLIC_I,
]
IGNORE_CONNS_FIELD = "ignoreConnections"
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

# Processes
NAME_FIELD = "name"
EXE_FIELD = "exe"
ID_FIELD = "id"
EUSER_FIELD = "euser"
CHILDREN_FIELD = "children"
LISTENING_SOCKETS = "listeningSockets"

# Container
CONTAINER_NAME_FIELD = "name"
CONTAINER_ID_FIELD = "id"
CONTAINER_AGE = "age"
CONTAINER_IMAGE_NAME = "image-name"

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


def load_file(path: Path) -> Dict:
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
                            # single use, parse args twice will make dupes
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


def time_inp(time_str: str, cap_one_day=False) -> int:
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
    if API_CALL:
        if USE_LOG_VARS:
            global ERR_VAR
            ERR_VAR.append(f"{WARNING_COLOR}Error: {message}{COLOR_END}")
        if exception:
            raise exception
        elif USE_LOG_VARS:
            raise Exception()
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
    except Exception:
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


def set_debug():
    global DEBUG
    DEBUG = True
