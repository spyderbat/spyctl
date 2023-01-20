import copy
import inspect
import io
import json
import os
import sys
import time
from base64 import urlsafe_b64encode as b64url
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple, Union
from uuid import uuid4

import click
import dateutil.parser as dateparser
import yaml
import zulu
from click.shell_completion import (
    CompletionItem,
    BashComplete,
    add_completion_class,
)


class Aliases:
    def __init__(self, aliases: Iterable[str]) -> None:
        self.name = aliases[0]
        self.aliases = set(aliases)

    def __eq__(self, __o: object) -> bool:
        return __o in self.aliases


APP_NAME = "spyctl"

# Resource Aliases
CLUSTERS_RESOURCE = Aliases(["clusters", "cluster", "clust", "clusts", "clus"])
NAMESPACES_RESOURCE = Aliases(
    ["namespaces", "name", "names", "namesp", "namesps", "namespace"]
)
MACHINES_RESOURCE = Aliases(
    ["machines", "mach", "machs", "machine", "node", "nodes"]
)
PODS_RESOURCE = Aliases(["pods", "pod"])
FINGERPRINTS_RESOURCE = Aliases(
    [
        "fingerprints",
        "print",
        "prints",
        "fingerprint",
        "fprint",
        "f",
        "fprints",
    ]
)
POLICIES_RESOURCE = Aliases(
    [
        "policies",
        "spyderbat-policy",
        "spyderbat-policies",
        "spy-pol",
        "spol",
        "sp",
        "policy",
        "pol",
        "p",
    ]
)

DEL_RESOURCES: List[str] = [POLICIES_RESOURCE.name]
GET_RESOURCES: List[str] = [
    CLUSTERS_RESOURCE.name,
    FINGERPRINTS_RESOURCE.name,
    MACHINES_RESOURCE.name,
    NAMESPACES_RESOURCE.name,
    PODS_RESOURCE.name,
    POLICIES_RESOURCE.name,
]


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


# Resource Kinds
POL_KIND = "SpyderbatPolicy"
BASELINE_KIND = "SpyderbatBaseline"


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
ALLOWED_SEVERITIES = {S_CRIT, S_HIGH, S_MED, S_LOW, S_INFO}

# Config
API_KEY_FIELD = "apikey"
API_URL_FIELD = "apiurl"
LOCATION_FIELD = "location"
ORG_FIELD = "organization"
POD_FIELD = "pod"
CLUSTER_FIELD = "cluster"
NAMESPACE_FIELD = "namespace"
MACHINES_FIELD = "machines"
DEFAULT_API_URL = "https://api.spyderbat.com"

# Response Actions
ACTION_KILL_POD = "kill-pod"
ACTION_KILL_PROC = "kill-process"
ACTION_KILL_PROC_GRP = "kill-process-group"
ACTION_WEBHOOK = "webhook"
ALLOWED_TEMPLATES = {"json", "yaml", "slack"}
ALLOWED_ACTIONS = {
    ACTION_WEBHOOK,
    ACTION_KILL_POD,
    ACTION_KILL_PROC,
    ACTION_KILL_PROC_GRP,
}
RESPONSE_FIELD = "response"
RESP_DEFAULT_FIELD = "default"
RESP_ACTIONS_FIELD = "actions"
RESP_ACTION_NAME_FIELD = "actionName"
RESP_URL_FIELD = "url"
RESP_TEMPLATE_FIELD = "template"
RESP_SEVERITY_FIELD = "severity"

# Selectors
CONT_SELECTOR_FIELD = "containerSelector"
DNS_SELECTOR_FIELD = "dnsSelector"
MACHINE_SELECTOR_FIELD = "machineSelector"
NAMESPACE_SELECTOR_FIELD = "namespaceSelector"
POD_SELECTOR_FIELD = "podSelector"
SVC_SELECTOR_FIELD = "serviceSelector"
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
    CONT_SELECTOR_FIELD: [
        IMAGE_FIELD,
        IMAGEID_FIELD,
        CONT_NAME_FIELD,
        CONT_ID_FIELD,
    ],
    SVC_SELECTOR_FIELD: [CGROUP_FIELD],
    MACHINE_SELECTOR_FIELD: [],
    NAMESPACE_SELECTOR_FIELD: [MATCH_LABELS_FIELD],
    POD_SELECTOR_FIELD: [MATCH_LABELS_FIELD],
}

# Policies/Fingerprints
POL_TYPE_CONT = "container"
POL_TYPE_SVC = "service"
POL_TYPES = [POL_TYPE_SVC, POL_TYPE_CONT]
ENABLED_FIELD = "enabled"
METADATA_NAME_FIELD = "name"
METADATA_TAGS_FIELD = "tags"
METADATA_TYPE_FIELD = "type"
METADATA_UID_FIELD = "uid"
METADATA_CREATE_TIME = "creationTimestamp"
NET_POLICY_FIELD = "networkPolicy"
PROC_POLICY_FIELD = "processPolicy"
FIRST_TIMESTAMP_FIELD = "firstTimestamp"
LATEST_TIMESTAMP_FIELD = "latestTimestamp"

# Processes
NAME_FIELD = "name"
EXE_FIELD = "exe"
ID_FIELD = "id"
EUSER_FIELD = "euser"
CHILDREN_FIELD = "children"

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

# Output
OUTPUT_YAML = "yaml"
OUTPUT_JSON = "json"
OUTPUT_DEFAULT = "default"
OUTPUT_RAW = "raw"
OUTPUT_WIDE = "wide"
OUTPUT_CHOICES = [OUTPUT_YAML, OUTPUT_JSON, OUTPUT_DEFAULT]

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
RESPONSE_ACTION_TEMPLATE = {
    RESP_DEFAULT_FIELD: {RESP_SEVERITY_FIELD: S_HIGH},
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
            except Exception as e:
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
    SECTION_OTHER = "Other Commands"
    command_sections = [SECTION_BASIC, SECTION_OTHER]
    cmd_to_section_map = {
        "apply": SECTION_BASIC,
        "create": SECTION_BASIC,
        "delete": SECTION_BASIC,
        "diff": SECTION_BASIC,
        "get": SECTION_BASIC,
        "merge": SECTION_BASIC,
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


def try_log(*args, **kwargs):
    try:
        print(*args, **kwargs, file=sys.stderr)
        sys.stderr.flush()
    except BrokenPipeError:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stderr.fileno())
        sys.exit(1)


def time_inp(time_str: str) -> int:
    past_seconds = 0
    epoch_time = None
    try:
        try:
            epoch_time = int(time_str)
        except ValueError:
            if time_str.endswith(("s", "sc")):
                past_seconds = int(time_str[:-1])
            elif time_str.endswith(("m", "mn")):
                past_seconds = int(time_str[:-1]) * 60
            elif time_str.endswith(("h", "hr")):
                past_seconds = int(time_str[:-1]) * 60 * 60
            elif time_str.endswith(("d", "dy")):
                past_seconds = int(time_str[:-1]) * 60 * 60 * 24
            elif time_str.endswith(("w", "wk")):
                past_seconds = int(time_str[:-1]) * 60 * 60 * 24 * 7
            else:
                date = dateparser.parse(time_str)
                diff = datetime.now() - date
                past_seconds = diff.total_seconds()
    except (ValueError, dateparser.ParserError):
        raise ValueError("invalid time input (see documentation)") from None
    now = time.time()
    one_day_ago = now - 86400
    if epoch_time is not None:
        if epoch_time > now:
            raise ValueError("time must be in the past")
        # TODO: Make API calls robust to times older than one day
        if epoch_time < one_day_ago:
            epoch_time = one_day_ago
        return epoch_time
    else:
        if past_seconds < 0:
            raise ValueError("time must be in the past")
        # TODO: Make API calls robust to times older than one day
        if past_seconds > 86400:
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
    rv.update(filters)
    return rv


def make_uuid():
    return b64url(uuid4().bytes).decode("ascii").strip("=")


def err_exit(message: str):
    sys.stderr.write(f"Error: {message}\n")
    exit(1)


def load_resource_file(file: Union[str, io.TextIOWrapper]):
    try:
        if isinstance(file, io.TextIOWrapper):
            resrc_data = yaml.load(file, yaml.Loader)
        else:
            with open(file) as f:
                resrc_data = yaml.load(f, yaml.Loader)
    except Exception:
        try:
            if isinstance(file, io.TextIOWrapper):
                resrc_data = json.load(file)
            else:
                with open(file) as f:
                    resrc_data = json.load(f)
        except Exception:
            err_exit("Unable to load resource file.")
    if not isinstance(resrc_data, dict):
        err_exit("Resource file does not contain a dictionary.")
    return resrc_data


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


def _to_timestamp(zulu_str):
    return zulu.Zulu.parse(zulu_str).timestamp()
