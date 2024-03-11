"""Handles the 'get' command for spyctl."""

import fnmatch
import time
from typing import IO, Dict, List, Tuple

import click

import spyctl.config.configs as cfg
import spyctl.filter_resource as filt
import spyctl.resources.agents as spy_agents
import spyctl.resources.api_filters as _af
import spyctl.resources.clusterrolebindings as spyctl_crb
import spyctl.resources.clusterroles as spyctl_clusterroles
import spyctl.resources.clusters as spyctl_clusts
import spyctl.resources.connection_bundles as spyctl_cb
import spyctl.resources.connections as spyctl_conns
import spyctl.resources.containers as spyctl_cont
import spyctl.resources.daemonsets as spyctl_daemonset
import spyctl.resources.deployments as spyctl_deployments
import spyctl.resources.deviations as spyctl_dev
import spyctl.resources.fingerprints as spyctl_fprints
import spyctl.resources.flags as spyctl_flags
import spyctl.resources.machines as spyctl_machines
import spyctl.resources.namespaces as spyctl_names
import spyctl.resources.nodes as spyctl_nodes
import spyctl.resources.notification_configs as spyctl_notif
import spyctl.resources.notification_targets as spyctl_tgt
import spyctl.resources.pods as spyctl_pods
import spyctl.resources.policies as spyctl_policies
import spyctl.resources.processes as spyctl_procs
import spyctl.resources.replicasets as spyctl_replicaset
import spyctl.resources.rolebindings as spyctl_rolebinding
import spyctl.resources.roles as spyctl_roles
import spyctl.resources.rulesets as spyctl_ruleset
import spyctl.resources.sources as spyctl_src
import spyctl.resources.spydertraces as spyctl_spytrace
import spyctl.resources.suppression_policies as s_pol
import spyctl.spyctl_lib as lib
from spyctl import api, cli

# ----------------------------------------------------------------- #
#                          Get Subcommand                           #
# ----------------------------------------------------------------- #


class GetCommand(lib.ArgumentParametersCommand):
    argument_name = "resource"
    argument_value_parameters = [
        {
            "resource": [
                lib.AGENT_RESOURCE,
                lib.CONNECTIONS_RESOURCE,
                lib.CONTAINER_RESOURCE,
                lib.DEPLOYMENTS_RESOURCE,
                lib.FINGERPRINTS_RESOURCE,
                lib.MACHINES_RESOURCE,
                lib.NODES_RESOURCE,
                lib.NODES_RESOURCE,
                lib.OPSFLAGS_RESOURCE,
                lib.PODS_RESOURCE,
                lib.PROCESSES_RESOURCE,
                lib.REDFLAGS_RESOURCE,
                lib.SPYDERTRACE_RESOURCE,
            ],
            "args": [
                click.option(
                    "--latest_model",
                    help="Use additional memory when outputting json or yaml"
                    " to ensure only the latest version of each model is"
                    " returned.",
                    is_flag=True,
                ),
            ],
        },
        {
            "resource": [lib.REDFLAGS_RESOURCE, lib.OPSFLAGS_RESOURCE],
            "args": [
                click.option(
                    "--severity",
                    lib.FLAG_SEVERITY,
                    help="Only show flags with the given"
                    " severity or higher.",
                ),
            ],
        },
        {
            "resource": [lib.REDFLAGS_RESOURCE],
            "args": [
                click.option(
                    "--include-exceptions",
                    "exceptions",
                    is_flag=True,
                    help="Include redflags marked as exceptions in output."
                    " Off by default.",
                ),
            ],
        },
        {
            "resource": [lib.NOTIFICATION_CONFIGS_RESOURCE],
            "args": [
                click.option(
                    "--full-policy",
                    "full_policy",
                    is_flag=True,
                    default=False,
                    help="Emit the full organization notification policy"
                    " object when using yaml or json output format.",
                ),
            ],
        },
        {
            "resource": [lib.NOTIFICATION_CONFIG_TEMPLATES_RESOURCE],
            "args": [
                click.option(
                    "--type",
                    metavar="",
                    type=click.Choice(lib.NOTIF_TMPL_TYPES),
                    help="Emit the full organization notification policy"
                    " object when using yaml or json output format.",
                ),
            ],
        },
        {
            "resource": [lib.DEVIATIONS_RESOURCE],
            "args": [
                click.option(
                    f"--{lib.POLICIES_FIELD}",
                    "policies",
                    help="Policies to get deviations from.",
                    type=lib.ListParam(),
                    metavar="",
                ),
                click.option(
                    "--non-unique",
                    is_flag=True,
                    help="By default json or yaml output will be unique. Set"
                    " this flag to include all relevant deviations.",
                ),
                click.option(
                    "--raw-data",
                    is_flag=True,
                    help="Return the raw event_audit:guardian_deviation data.",
                ),
                click.option(
                    "--include-irrelevant",
                    is_flag=True,
                    help="Return deviations tied to a policy even if they"
                    " are no longer relevant. The default behavior is to"
                    " exclude deviations that have already been merged into"
                    " the policy.",
                ),
            ],
        },
        {
            "resource": [lib.AGENT_RESOURCE],
            "args": [
                click.option(
                    "--usage-csv",
                    help="Outputs the usage metrics for 1 or more agents to"
                    " a specified csv file.",
                    type=click.File(mode="w"),
                ),
                click.option(
                    "--usage-json",
                    help="Outputs the usage metrics for 1 or more agents to"
                    " stdout in json format.",
                    is_flag=True,
                    default=False,
                ),
                click.option(
                    "--raw-metrics-json",
                    help="Outputs the raw metrics records for 1 or more agents"
                    " to stdout in json format.",
                    is_flag=True,
                    default=False,
                ),
                click.option(
                    "--health-only",
                    help="This flag returns the agents list, but doesn't query"
                    " metrics (Faster) in the '-o wide' output. You will still"
                    " see the agent's health.",
                    default=False,
                    is_flag=True,
                ),
            ],
        },
        {
            "resource": [lib.FINGERPRINTS_RESOURCE],
            "args": [
                click.option(
                    "-T",
                    "--type",
                    type=click.Choice(
                        [lib.POL_TYPE_CONT, lib.POL_TYPE_SVC],
                        case_sensitive=False,
                    ),
                    required=True,
                    help="The type of fingerprint to return.",
                ),
                click.option(
                    "--raw-data",
                    is_flag=True,
                    help="When outputting to yaml or json, this outputs the"
                    " raw fingerprint data, instead of the fingerprint groups",
                ),
                click.option(
                    "--group-by",
                    type=lib.ListParam(),
                    metavar="",
                    help="Group by fields in the fingerprint, comma delimited. Such as"  # noqa: E501
                    " cluster_name,namespace. At a basic level"
                    " fingerprints are always grouped by image + image_id."
                    " This option allows you to group by additional fields.",
                ),
                click.option(
                    "--sort-by",
                    metavar="",
                    type=lib.ListParam(),
                    help="Group by fields in the fingerprint, comma delimited. Such as"  # noqa: E501
                    " cluster_name,namespace. At a basic level"
                    " fingerprints are always grouped by image + image_id."
                    " This option allows you to group by additional fields.",
                ),
            ],
        },
        {
            "resource": [lib.CONNECTIONS_RESOURCE],
            "args": [
                click.option(
                    "--ignore-ips",
                    "ignore_ips",
                    is_flag=True,
                    help="Ignores differing ips in the table output."
                    " Off by default.",
                ),
                click.option(
                    "--remote-port",
                    lib.REMOTE_PORT,
                    help="The port number on the remote side of the connection.",  # noqa: E501
                    type=click.INT,
                ),
                click.option(
                    "--local-port",
                    lib.LOCAL_PORT,
                    help="The port number on the local side of the connection.",  # noqa: E501
                    type=click.INT,
                ),
            ],
        },
        {
            "resource": [lib.POLICIES_RESOURCE],
            "args": [
                click.option(
                    "-f",
                    "--filename",
                    help="Policy files for use with the --policy-coverage and"
                    " --has-matching options. If neither of those options are"
                    " set this returns a table of policies supplied in the"
                    " file(s).",
                    metavar="",
                    type=lib.FileList(),
                    cls=lib.OptionEatAll,
                ),
                click.option(
                    "-H",
                    "--has-matching",
                    "--has-matching-fingerprints",
                    is_flag=True,
                    help="Gets applied policies or takes supplied policy files"
                    " and checks for matching fingerprints. Outputs two tables"
                    ", one with policies that had no matching fingerprints in"
                    " the search window, and another with policies that had"
                    " matching fingerprints. This can be used to determine if"
                    " a policy is [still] relevant to your organization.",
                ),
                click.option(
                    "-O",
                    "--output-to-file",
                    help="Should output policies to a file. Unique filename"
                    " created from the name in each policy's metadata.",
                    is_flag=True,
                ),
                click.option(
                    "--raw-data",
                    is_flag=True,
                    hidden=True,
                ),
                click.option(
                    "--get-deviations",
                    help="In the summary output, show deviations count for the"
                    " provided time window",
                    is_flag=True,
                ),
                click.option(
                    "--from-archive",
                    is_flag=True,
                    help="Retrieve archived ruleset versions.",
                ),
                click.option(
                    "--version",
                    type=click.INT,
                    help="Retrieve archived rulesets with a specific version.",
                    metavar="",
                ),
            ],
        },
        {
            "resource": [lib.CLUSTER_RULESET_RESOURCE],
            "args": [
                click.option(
                    "--from-archive",
                    is_flag=True,
                    help="Retrieve archived ruleset versions.",
                ),
                click.option(
                    "--version",
                    type=click.INT,
                    help="Retrieve archived rulesets with a specific version.",
                    metavar="",
                ),
            ],
        },
    ]


@click.command("get", cls=GetCommand, epilog=lib.SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.argument("resource", type=lib.GetResourcesParam())
@click.argument("name_or_id", required=False)
@click.option(
    "--image",
    cfg.IMG_FIELD,
    help="Only show resources tied to this container image."
    " Overrides value current context if it exists.",
    type=lib.ListParam(),
    metavar="",
)
@click.option(
    "--image-id",
    cfg.IMGID_FIELD,
    help="Only show resources tied to containers running with this"
    " image id. Overrides value current context if it exists.",
    type=lib.ListParam(),
    metavar="",
)
@click.option(
    "--container-name",
    cfg.CONTAINER_NAME_FIELD,
    help="Only show resources tied to containers running with this"
    " container name. Overrides value current context if it exists.",
    type=lib.ListParam(),
    metavar="",
)
@click.option(
    "--container-id",
    cfg.CONT_ID_FIELD,
    help="Only show resources tied to containers running with this"
    " container id. Overrides value current context if it exists.",
    type=lib.ListParam(),
    metavar="",
)
@click.option(
    "--cgroup",
    cfg.CGROUP_FIELD,
    help="Only show resources tied to machines running Linux services with"
    " this cgroup. Overrides value current context if it exists.",
    type=lib.ListParam(),
    metavar="",
)
@click.option(
    "--pod",
    cfg.POD_FIELD,
    help="Only show resources tied to this pod uid."
    " Overrides value current context if it exists.",
    type=lib.ListParam(),
    metavar="",
)
@click.option(
    f"--{cfg.MACHINES_FIELD}",
    "--nodes",
    help="Only show resources to these nodes."
    " Overrides value current context if it exists.",
    type=lib.ListParam(),
    metavar="",
)
@click.option(
    f"--{cfg.NAMESPACE_FIELD}",
    help="Only show resources tied to this namespace."
    " Overrides value current context if it exists.",
    type=lib.ListParam(),
    metavar="",
)
@click.option(
    f"--{cfg.CLUSTER_FIELD}",
    help="Only show resources tied to this cluster."
    " Overrides value current context if it exists.",
    type=lib.ListParam(),
    metavar="",
)
@click.option(
    "-o",
    "--output",
    default=lib.OUTPUT_DEFAULT,
    type=click.Choice(
        lib.OUTPUT_CHOICES + [lib.OUTPUT_WIDE], case_sensitive=False
    ),
)
@click.option(
    "-E",
    "--exact",
    "--exact-match",
    is_flag=True,
    help="Exact match for NAME_OR_ID. This command's default behavior"
    "displays any resource that contains the NAME_OR_ID.",
)
@click.option(
    "-t",
    "--start-time",
    "st",
    help="Start time of the query. Default is 24 hours ago.",
    default=None,
    type=lib.time_inp,
)
@click.option(
    "-e",
    "--end-time",
    "et",
    help="End time of the query. Default is now.",
    default=time.time(),
    type=lib.time_inp,
)
@click.option(
    "--ndjson",
    help="If output is 'json' this outputs each json record on its own line",
    is_flag=True,
)
def get(
    resource,
    st,
    et,
    output,
    filename=None,
    exact=False,
    name_or_id=None,
    latest=None,
    **filters,
):
    """Display one or many Spyderbat Resources.

    See https://spyctl.readthedocs.io/en/latest/user/resources.html for a full
    list of available resource.

    \b
    Some resources are retrieved from from databases where a time range can
    be specified:
    - ClusterRoles
    - ClusterRoleBindings
    - Connections
    - Connection Bundles
    - Containers
    - Daemonsets
    - Deployments
    - Deviations
    - Fingerprints
    - Namespaces
    - Nodes
    - OpsFlags
    - Pods
    - Processes
    - RedFlags
    - Replicasets
    - Roles
    - RoleBindings
    - Spydertraces
    - Agents

    \b
    Other resources come from databases where time ranges are not applicable:
    - Clusters
    - Machines
    - Policies

    \b
    Examples:
      # Get all observed Pods for the last hour:
      spyctl get pods -t 1h\n
    \b
      # Get all observed Pods from 4 hours ago to 2 hours ago
      spyctl get pods -t 4h -e 2h\n
    \b
      # Get observed pods for a specific time range (using epoch timestamps)
      spyctl get pods -t 1675364629 -e 1675368229\n
    \b
      # Get a Fingerprint Group of all runs of httpd.service for the last 24
      # hours and output to a yaml file
      spyctl get fingerprints httpd.service -o yaml > fprints.yaml\n
    \b
      # Get the latest fingerprints related to a policy yaml file
      spyctl get fingerprints -f policy.yaml --latest
    \b
      # Get all the containers
      spyctl get containers
    \b
      # Get the containers for specific time range (using epoch timestamps)
      spyctl get containers -t 1675364629 -e 1675368229\n
    \b
      # Get the containers for specific time range
      spyctl get containers -t 2h or spyctl get containers -t 1d -e 2h
    \b
      # Get the specific container with that image name
      spyctl get containers --name spyderbat/container


    For time field options such as --start-time and --end-time you can
    use (m) for minutes, (h) for hours (d) for days, and (w) for weeks back
    from now or provide timestamps in epoch format.

    Note: Long time ranges or "get" commands in a context consisting of
    multiple machines can take a long time.
    """
    if st is None:
        st = lib.time_inp(_af.get_default_time_window(resource))
    filters = {
        key: value for key, value in filters.items() if value is not None
    }
    handle_get(
        resource,
        name_or_id,
        st,
        et,
        filename,
        latest,
        exact,
        output,
        **filters,
    )


# ----------------------------------------------------------------- #
#                            Get Handlers                           #
# ----------------------------------------------------------------- #

ALL = "all"
not_time_based = [
    lib.SOURCES_RESOURCE,
    lib.POLICIES_RESOURCE,
    lib.CLUSTERS_RESOURCE,
    lib.NOTIFICATION_CONFIGS_RESOURCE,
    lib.NOTIFICATION_TARGETS_RESOURCE,
    lib.NOTIFICATION_CONFIG_TEMPLATES_RESOURCE,
]
resource_with_global_src = [lib.AGENT_RESOURCE, lib.FINGERPRINTS_RESOURCE]

LIMIT_MEM = True
NDJSON = False


def handle_get(
    resource, name_or_id, st, et, file, latest, exact, output, **filters
):
    global LIMIT_MEM, NDJSON
    # If latest_model is true we won't limit memory usage
    LIMIT_MEM = not filters.pop("latest_model", False)
    NDJSON = filters.pop("ndjson", False)

    __output_time_log(resource, st, et)
    if name_or_id and not exact:
        name_or_id = name_or_id + "*" if name_or_id[-1] != "*" else name_or_id
        name_or_id = "*" + name_or_id if name_or_id[0] != "*" else name_or_id

    if resource == lib.AGENT_RESOURCE:
        handle_get_agents(name_or_id, st, et, output, **filters)
    elif resource == lib.CLUSTERS_RESOURCE:
        handle_get_clusters(name_or_id, output, **filters)
    elif resource == lib.CLUSTER_RULESET_RESOURCE:
        handle_get_rulesets(
            name_or_id, lib.RULESET_TYPE_CLUS, output, **filters
        )
    elif resource == lib.CONNECTIONS_RESOURCE:
        handle_get_connections(name_or_id, st, et, output, **filters)
    elif resource == lib.CONNECTION_BUN_RESOURCE:
        handle_get_conn_buns(name_or_id, st, et, output, **filters)
    elif resource == lib.CONTAINER_RESOURCE:
        handle_get_containers(name_or_id, st, et, output, **filters)
    elif resource == lib.DEPLOYMENTS_RESOURCE:
        handle_get_deployments(name_or_id, st, et, output, **filters)
    elif resource == lib.DEVIATIONS_RESOURCE:
        handle_get_deviations(name_or_id, st, et, output, **filters)
    elif resource == lib.DAEMONSET_RESOURCE:
        handle_get_daemonsets(name_or_id, st, et, output, **filters)
    elif resource == lib.FINGERPRINTS_RESOURCE:
        handle_get_fingerprints(
            name_or_id, st, et, output, file, latest, **filters
        )
    elif resource == lib.MACHINES_RESOURCE:
        handle_get_machines(name_or_id, st, et, output, **filters)
    elif resource == lib.NAMESPACES_RESOURCE:
        handle_get_namespaces(name_or_id, st, et, output, **filters)
    elif resource == lib.NODES_RESOURCE:
        handle_get_nodes(name_or_id, st, et, output, **filters)
    elif resource == lib.NOTIFICATION_CONFIGS_RESOURCE:
        handle_get_notification_configs(name_or_id, output, **filters)
    elif resource == lib.NOTIFICATION_CONFIG_TEMPLATES_RESOURCE:
        handle_get_notif_config_templates(name_or_id, output, **filters)
    elif resource == lib.NOTIFICATION_TARGETS_RESOURCE:
        handle_get_notification_targets(name_or_id, output, **filters)
    elif resource == lib.OPSFLAGS_RESOURCE:
        handle_get_opsflags(name_or_id, st, et, output, **filters)
    elif resource == lib.PODS_RESOURCE:
        handle_get_pods(name_or_id, st, et, output, **filters)
    elif resource == lib.POLICIES_RESOURCE:
        handle_get_policies(name_or_id, output, file, st, et, **filters)
    elif resource == lib.PROCESSES_RESOURCE:
        handle_get_processes(name_or_id, st, et, output, **filters)
    elif resource == lib.REDFLAGS_RESOURCE:
        handle_get_redflags(name_or_id, st, et, output, **filters)
    elif resource == lib.ROLES_RESOURCE:
        handle_get_roles(name_or_id, st, et, output, **filters)
    elif resource == lib.CLUSTERROLES_RESOURCE:
        handle_get_clusterroles(name_or_id, st, et, output, **filters)
    elif resource == lib.REPLICASET_RESOURCE:
        handle_get_replicasets(name_or_id, st, et, output, **filters)
    elif resource == lib.SOURCES_RESOURCE:
        handle_get_sources(name_or_id, output, **filters)
    elif resource == lib.SPYDERTRACE_RESOURCE:
        handle_get_spydertraces(name_or_id, st, et, output, **filters)
    elif resource == lib.SUPPRESSION_POLICY_RESOURCE:
        handle_get_suppression_policies(name_or_id, st, et, output, **filters)
    elif resource == lib.ROLEBINDING_RESOURCE:
        handle_get_rolebinding(name_or_id, st, et, output, **filters)
    elif resource == lib.CLUSTERROLE_BINDING_RESOURCE:
        handle_get_clusterrolebinding(name_or_id, st, et, output, **filters)
    else:
        cli.err_exit(f"The 'get' command is not supported for {resource}")


# ----------------------------------------------------------------- #
#                        SQL-Based Resources                        #
# ----------------------------------------------------------------- #


def handle_get_clusters(name_or_id, output: str, **filters: Dict):
    ctx = cfg.get_current_context()
    clusters = api.get_clusters(*ctx.get_api_data())
    clusters = filt.filter_clusters(clusters, **filters)
    if name_or_id:
        clusters = filt.filter_obj(clusters, ["name", "uid"], name_or_id)
    if output in [lib.OUTPUT_DEFAULT, lib.OUTPUT_WIDE]:
        summary = spyctl_clusts.clusters_summary_output(clusters)
        cli.show(summary, lib.OUTPUT_RAW)
    else:
        for cluster in clusters:
            cli.show(cluster, output, ndjson=NDJSON)


def handle_get_notification_configs(name_or_id, output: str, **filters: Dict):
    full_policy = filters.get("full_policy", False)
    ctx = cfg.get_current_context()
    notif_type = filters.get(lib.NOTIF_TYPE_FIELD, lib.NOTIF_TYPE_ALL)
    n_pol = api.get_notification_policy(*ctx.get_api_data())
    if n_pol is None or not isinstance(n_pol, dict):
        cli.err_exit("Could not load notification policy")
    routes = n_pol.get(lib.ROUTES_FIELD, [])
    if name_or_id:
        routes = filt.filter_obj(routes, ["data.id", "data.name"], name_or_id)
    if output == lib.OUTPUT_DEFAULT:
        summary = spyctl_notif.notifications_summary_output(routes, notif_type)
        cli.show(summary, lib.OUTPUT_RAW)
    elif output == lib.OUTPUT_WIDE:
        summary = spyctl_notif.notifications_wide_output(routes, notif_type)
        cli.show(summary, lib.OUTPUT_RAW)
    else:
        if not full_policy:
            for route in routes:
                config = route.get(lib.DATA_FIELD, {}).get(
                    lib.NOTIF_SETTINGS_FIELD
                )
                if config:
                    cli.show(config, output, ndjson=NDJSON)
                else:
                    cli.show(route, output, ndjson=NDJSON)
        else:
            cli.show(n_pol, output, ndjson=NDJSON)


def handle_get_notification_targets(
    name_or_id: str, output: str, **filters: Dict
):
    ctx = cfg.get_current_context()
    n_pol = api.get_notification_policy(*ctx.get_api_data())
    if n_pol is None or not isinstance(n_pol, dict):
        cli.err_exit("Could not load notification targets")
    targets: Dict = n_pol.get(lib.TARGETS_FIELD, {})
    if name_or_id:
        tmp_tgts = {}
        for tgt_name, tgt_data in targets.items():
            tgt_obj = spyctl_tgt.Target(backend_target={tgt_name: tgt_data})
            if tgt_obj.id == name_or_id.strip("*") or fnmatch.fnmatch(
                tgt_name, name_or_id
            ):
                tmp_tgts[tgt_name] = tgt_data
        targets = tmp_tgts
    if output == lib.OUTPUT_DEFAULT:
        summary = spyctl_tgt.targets_summary_output(targets)
        cli.show(summary, lib.OUTPUT_RAW)
    elif output == lib.OUTPUT_WIDE:
        summary = spyctl_tgt.targets_wide_output(targets)
        cli.show(summary, lib.OUTPUT_RAW)
    else:
        for tgt_name, tgt_data in targets.items():
            target = spyctl_tgt.Target(backend_target={tgt_name: tgt_data})
            cli.show(target.as_dict(), output, ndjson=NDJSON)


def handle_get_sources(name_or_id, output: str, **filters: Dict):
    ctx = cfg.get_current_context()
    sources = api.get_sources(*ctx.get_api_data())
    sources = filt.filter_sources(sources, **filters)
    if name_or_id:
        sources = filt.filter_obj(sources, ["name", "uid"], name_or_id)
    if output in [lib.OUTPUT_DEFAULT, lib.OUTPUT_WIDE]:
        summary = spyctl_src.sources_summary_output(sources)
        cli.show(summary, lib.OUTPUT_RAW)
    else:
        for source in sources:
            cli.show(source, output, ndjson=NDJSON)


# ----------------------------------------------------------------- #
#                       Source-Based Resources                      #
# ----------------------------------------------------------------- #


def handle_get_agents(
    name_or_id,
    st,
    et,
    output,
    **filters: Dict,
):
    ctx = cfg.get_current_context()
    usage_csv_file: IO = filters.pop("usage_csv", None)
    usage_json: bool = filters.pop("usage_json", None)
    raw_metrics_json: bool = filters.pop("raw_metrics_json", False)
    include_latest_metrics = not filters.pop("health_only", False)
    sources, filters = _af.Agents.build_sources_and_filters(**filters)
    pipeline = _af.Agents.generate_pipeline(
        name_or_id, None, True, filters=filters
    )
    if usage_csv_file:
        agent_st = __st_at_least_2hrs(st)
        agents = list(
            api.get_agents(
                *ctx.get_api_data(),
                sources,
                time=(agent_st, et),
                pipeline=pipeline,
                limit_mem=LIMIT_MEM,
            )
        )
        # We're only outputting the metrics data to a csv file
        handle_agent_usage_csv(agents, st, et, usage_csv_file)
    elif usage_json:
        agent_st = __st_at_least_2hrs(st)
        agents = list(
            api.get_agents(
                *ctx.get_api_data(),
                sources,
                time=(agent_st, et),
                pipeline=pipeline,
                limit_mem=LIMIT_MEM,
            )
        )
        handle_agent_usage_json(agents, st, et)
    elif raw_metrics_json:
        agent_st = __st_at_least_2hrs(st)
        agents = list(
            api.get_agents(
                *ctx.get_api_data(),
                sources,
                time=(agent_st, et),
                pipeline=pipeline,
                limit_mem=LIMIT_MEM,
            )
        )
        handle_agent_metrics_json(agents, st, et)
    else:
        # Normal path for output
        agents = list(
            api.get_agents(
                *ctx.get_api_data(),
                sources,
                time=(st, et),
                pipeline=pipeline,
                limit_mem=LIMIT_MEM,
            )
        )
        if output == lib.OUTPUT_DEFAULT:
            summary = spy_agents.agent_summary_output(agents)
            cli.show(summary, lib.OUTPUT_RAW)
        elif output == lib.OUTPUT_WIDE:
            cli.try_log("Retrieving source data for agent(s).")
            sources_data = api.get_sources_data_for_agents(*ctx.get_api_data())
            summary = spy_agents.agents_output_wide(
                agents, sources_data, include_latest_metrics
            )
            cli.show(summary, lib.OUTPUT_RAW)
        else:
            for agent in agents:
                cli.show(agent, output, ndjson=NDJSON)


def handle_get_containers(name_or_id, st, et, output, **filters):
    ctx = cfg.get_current_context()
    sources, filters = _af.Containers.build_sources_and_filters(**filters)
    pipeline = _af.Containers.generate_pipeline(name_or_id, filters=filters)
    if output in [lib.OUTPUT_DEFAULT, lib.OUTPUT_WIDE]:
        summary = spyctl_cont.cont_summary_output(
            ctx, sources, (st, et), pipeline, LIMIT_MEM
        )
        cli.show(summary, lib.OUTPUT_RAW)
    else:
        for container in api.get_containers(
            *ctx.get_api_data(),
            sources,
            (st, et),
            pipeline=pipeline,
            limit_mem=LIMIT_MEM,
            disable_pbar_on_first=not lib.is_redirected(),
        ):
            cli.show(container, output, ndjson=NDJSON)


def handle_get_connections(name_or_id, st, et, output, **filters):
    ctx = cfg.get_current_context()
    ignore_ips = filters.pop("ignore_ips", False)
    sources, filters = _af.Connections.build_sources_and_filters(**filters)
    pipeline = _af.Connections.generate_pipeline(name_or_id, filters=filters)
    if output in [lib.OUTPUT_DEFAULT, lib.OUTPUT_WIDE]:
        summary = spyctl_conns.conn_summary_output(
            ctx,
            sources,
            (st, et),
            ignore_ips,
            pipeline=pipeline,
            limit_mem=LIMIT_MEM,
        )
        cli.show(summary, lib.OUTPUT_RAW)
    else:
        for connection in api.get_connections(
            *ctx.get_api_data(),
            sources,
            (st, et),
            pipeline=pipeline,
            limit_mem=LIMIT_MEM,
            disable_pbar_on_first=not lib.is_redirected(),
        ):
            cli.show(connection, output, ndjson=NDJSON)


def handle_get_conn_buns(name_or_id, st, et, output, **filters):
    ctx = cfg.get_current_context()
    sources, filters = _af.ConnectionBundles.build_sources_and_filters(
        **filters
    )
    pipeline = _af.ConnectionBundles.generate_pipeline(
        name_or_id, filters=filters
    )
    if output in [lib.OUTPUT_DEFAULT, lib.OUTPUT_WIDE]:
        summary = spyctl_cb.conn_bun_summary_output(
            ctx, sources, (st, et), pipeline, LIMIT_MEM
        )
        cli.show(summary, lib.OUTPUT_RAW)
    else:
        for conn_bun in api.get_connection_bundles(
            *ctx.get_api_data(),
            sources,
            (st, et),
            pipeline,
            LIMIT_MEM,
            not lib.is_redirected(),
        ):
            cli.show(conn_bun, output, ndjson=NDJSON)


def handle_get_deployments(name_or_id, st, et, output, **filters):
    ctx = cfg.get_current_context()
    sources, filters = _af.Deployments.build_sources_and_filters(**filters)
    pipeline = _af.Deployments.generate_pipeline(name_or_id, filters=filters)
    if output in [lib.OUTPUT_DEFAULT, lib.OUTPUT_WIDE]:
        summary = spyctl_deployments.deployments_stream_summary_output(
            ctx, sources, (st, et), pipeline, LIMIT_MEM
        )
        cli.show(summary, lib.OUTPUT_RAW)
    else:
        for deployment in api.get_deployments(
            *ctx.get_api_data(),
            sources,
            (st, et),
            pipeline,
            LIMIT_MEM,
            disable_pbar_on_first=not lib.is_redirected(),
        ):
            cli.show(deployment, output, ndjson=NDJSON)


def handle_get_deviations(name_or_id: str, st, et, output, **filters):
    unique = not filters.pop("non_unique", False)  # Default is unique
    raw_data = filters.pop("raw_data", False)
    include_irrelevant = filters.pop("include_irrelevant", False)
    ctx = cfg.get_current_context()
    sources, filters = _af.Deviations.build_sources_and_filters(**filters)
    if _af.POLICIES_CACHE:
        policies = _af.POLICIES_CACHE
    else:
        policies = api.get_policies(*ctx.get_api_data())
    sources_set = set(sources)
    if name_or_id:
        dev_uid = (
            name_or_id if name_or_id.strip("*").startswith("audit:") else None
        )
        if not dev_uid:
            policies = filt.filter_obj(
                policies,
                [
                    [lib.METADATA_FIELD, lib.NAME_FIELD],
                    [lib.METADATA_FIELD, lib.METADATA_UID_FIELD],
                ],
                name_or_id,
            )
            sources = [
                policy[lib.METADATA_FIELD][lib.METADATA_UID_FIELD]
                for policy in policies
            ]
        else:
            policies = [
                policy
                for policy in policies
                if policy[lib.METADATA_FIELD][lib.METADATA_UID_FIELD]
                in sources_set
            ]
    else:
        dev_uid = None
        policies = [
            policy
            for policy in policies
            if policy[lib.METADATA_FIELD][lib.METADATA_UID_FIELD]
            in sources_set
        ]
    pipeline = _af.Deviations.generate_pipeline(dev_uid, filters=filters)
    if output in [lib.OUTPUT_DEFAULT, lib.OUTPUT_WIDE]:
        summary = spyctl_policies.policies_summary_output(
            policies,
            (st, et),
            get_deviations_count=True,
            suppress_msg=True,
            dev_name_or_uid=dev_uid,
            dev_filters=filters,
            include_irrelevant=include_irrelevant,
        )
        cli.show(summary, lib.OUTPUT_RAW)
    else:
        for deviation in spyctl_dev.get_deviations_stream(
            ctx,
            sources,
            (st, et),
            pipeline,
            LIMIT_MEM,
            disable_pbar_on_first=not lib.is_redirected(),
            unique=unique,
            raw_data=raw_data,
            include_irrelevant=include_irrelevant,
            policies=policies,
        ):
            cli.show(deviation, output, ndjson=NDJSON)


def handle_get_machines(name_or_id, st, et, output: str, **filters: Dict):
    ctx = cfg.get_current_context()
    sources, filters = _af.Machines.build_sources_and_filters(**filters)
    pipeline = _af.Machines.generate_pipeline(name_or_id, filters=filters)
    if output in [lib.OUTPUT_DEFAULT, lib.OUTPUT_WIDE]:
        summary = spyctl_machines.machines_summary_output(
            ctx, sources, (st, et), pipeline, LIMIT_MEM
        )
        cli.show(summary, lib.OUTPUT_RAW)
    else:
        for machine in api.get_machines(
            *ctx.get_api_data(),
            sources,
            (st, et),
            pipeline,
            LIMIT_MEM,
            not lib.is_redirected(),
        ):
            cli.show(machine, output, ndjson=NDJSON)


def handle_get_namespaces(name_or_uid, st, et, output, **filters):
    ctx = cfg.get_current_context()
    sources, filters = _af.Namespaces.build_sources_and_filters(**filters)
    pipeline = _af.Namespaces.generate_pipeline(name_or_uid, filters=filters)
    if output in [lib.OUTPUT_DEFAULT, lib.OUTPUT_WIDE]:
        summary = spyctl_names.namespace_summary_output(
            name_or_uid, ctx, sources, (st, et), pipeline
        )
        cli.show(summary, lib.OUTPUT_RAW)
    else:
        for namespace in api.get_namespaces(
            *ctx.get_api_data(),
            sources,
            (st, et),
            pipeline,
            not lib.is_redirected(),
        ):
            cli.show(namespace, output, ndjson=NDJSON)


def handle_get_nodes(name_or_id, st, et, output: str, **filters: Dict):
    ctx = cfg.get_current_context()
    sources, filters = _af.Nodes.build_sources_and_filters(**filters)
    pipeline = _af.Nodes.generate_pipeline(
        name_or_id,
    )
    if output in [lib.OUTPUT_DEFAULT, lib.OUTPUT_WIDE]:
        summary = spyctl_nodes.nodes_output_summary(
            ctx, sources, (st, et), pipeline, LIMIT_MEM
        )
        cli.show(summary, lib.OUTPUT_RAW)
    else:
        for node in api.get_nodes(
            *ctx.get_api_data(),
            sources,
            (st, et),
            pipeline,
            LIMIT_MEM,
            not lib.is_redirected(),
        ):
            cli.show(node, output, ndjson=NDJSON)


def handle_get_opsflags(name_or_id, st, et, output, **filters):
    ctx = cfg.get_current_context()
    sources, filters = _af.OpsFlags.build_sources_and_filters(**filters)
    pipeline = _af.OpsFlags.generate_pipeline(name_or_id, filters=filters)
    if output in [lib.OUTPUT_DEFAULT, lib.OUTPUT_WIDE]:
        summary = spyctl_flags.flags_output_summary(
            ctx,
            lib.EVENT_OPSFLAG_PREFIX,
            sources,
            (st, et),
            pipeline,
            LIMIT_MEM,
        )
        cli.show(summary, lib.OUTPUT_RAW)
    else:
        for flag in api.get_opsflags(
            *ctx.get_api_data(),
            sources,
            (st, et),
            pipeline,
            LIMIT_MEM,
            not lib.is_redirected(),
        ):
            cli.show(flag, output, ndjson=NDJSON)


def handle_get_pods(name_or_id, st, et, output, **filters):
    ctx = cfg.get_current_context()
    sources, filters = _af.Pods.build_sources_and_filters(**filters)
    pipeline = _af.Pods.generate_pipeline(name_or_id, filters=filters)
    if output in [lib.OUTPUT_DEFAULT, lib.OUTPUT_WIDE]:
        summary = spyctl_pods.pods_output_summary(
            ctx, sources, (st, et), pipeline, LIMIT_MEM
        )
        cli.show(summary, lib.OUTPUT_RAW)
    else:
        for pod in api.get_pods(
            *ctx.get_api_data(),
            sources,
            (st, et),
            pipeline,
            LIMIT_MEM,
            not lib.is_redirected(),
        ):
            cli.show(pod, output, ndjson=NDJSON)


def handle_get_daemonsets(name_or_id, st, et, output, **filters):
    ctx = cfg.get_current_context()
    sources, filters = _af.Daemonsets.build_sources_and_filters(**filters)
    pipeline = _af.Daemonsets.generate_pipeline(name_or_id, filters=filters)
    if output in [lib.OUTPUT_DEFAULT, lib.OUTPUT_WIDE]:
        summary = spyctl_daemonset.daemonsets_output_summary(
            ctx, sources, (st, et), pipeline, LIMIT_MEM
        )
        cli.show(summary, lib.OUTPUT_RAW)
    else:
        for daemonset in api.get_daemonsets(
            *ctx.get_api_data(),
            sources,
            (st, et),
            pipeline,
            LIMIT_MEM,
            not lib.is_redirected(),
        ):
            cli.show(daemonset, output, ndjson=NDJSON)


def handle_get_processes(name_or_id, st, et, output, **filters):
    ctx = cfg.get_current_context()
    sources, filters = _af.Processes.build_sources_and_filters(**filters)
    pipeline = _af.Processes.generate_pipeline(name_or_id, filters=filters)
    if output in [lib.OUTPUT_DEFAULT, lib.OUTPUT_WIDE]:
        summary = spyctl_procs.processes_stream_output_summary(
            ctx, sources, (st, et), pipeline, LIMIT_MEM
        )
        cli.show(summary, lib.OUTPUT_RAW)
    else:
        for process in api.get_processes(
            *ctx.get_api_data(),
            sources,
            (st, et),
            pipeline,
            LIMIT_MEM,
            not lib.is_redirected(),
        ):
            cli.show(process, output, ndjson=NDJSON)


def handle_get_replicasets(name_or_id, st, et, output, **filters):
    ctx = cfg.get_current_context()
    sources, filters = _af.ReplicaSet.build_sources_and_filters(**filters)
    pipeline = _af.ReplicaSet.generate_pipeline(name_or_id, filters=filters)
    if output in [lib.OUTPUT_DEFAULT, lib.OUTPUT_WIDE]:
        summary = spyctl_replicaset.replicaset_output_summary(
            ctx, sources, (st, et), pipeline, LIMIT_MEM
        )
        cli.show(summary, lib.OUTPUT_RAW)
    else:
        for replicaset in api.get_replicaset(
            *ctx.get_api_data(),
            sources,
            (st, et),
            pipeline,
            LIMIT_MEM,
            not lib.is_redirected(),
        ):
            cli.show(replicaset, output, ndjson=NDJSON)


def handle_get_roles(name_or_id, st, et, output, **filters):
    ctx = cfg.get_current_context()
    sources, filters = _af.Role.build_sources_and_filters(**filters)
    pipeline = _af.Role.generate_pipeline(name_or_id, filters=filters)
    if output in [lib.OUTPUT_DEFAULT, lib.OUTPUT_WIDE]:
        summary = spyctl_roles.role_output_summary(
            ctx, sources, (st, et), pipeline, LIMIT_MEM
        )
        cli.show(summary, lib.OUTPUT_RAW)
    else:
        for role in api.get_role(
            *ctx.get_api_data(),
            sources,
            (st, et),
            pipeline,
            LIMIT_MEM,
            not lib.is_redirected(),
        ):
            cli.show(role, output, ndjson=NDJSON)


def handle_get_clusterroles(name_or_id, st, et, output, **filters):
    ctx = cfg.get_current_context()
    sources, filters = _af.ClusterRole.build_sources_and_filters(**filters)
    pipeline = _af.ClusterRole.generate_pipeline(name_or_id, filters=filters)
    if output in [lib.OUTPUT_DEFAULT, lib.OUTPUT_WIDE]:
        summary = spyctl_clusterroles.clusterrole_output_summary(
            ctx, sources, (st, et), pipeline, LIMIT_MEM
        )
        cli.show(summary, lib.OUTPUT_RAW)
    else:
        for clusterrole in api.get_clusterrole(
            *ctx.get_api_data(),
            sources,
            (st, et),
            pipeline,
            LIMIT_MEM,
            not lib.is_redirected(),
        ):
            cli.show(clusterrole, output, ndjson=NDJSON)


def handle_get_rolebinding(name_or_id, st, et, output, **filters):
    ctx = cfg.get_current_context()
    sources, filters = _af.RoleBinding.build_sources_and_filters(**filters)
    pipeline = _af.RoleBinding.generate_pipeline(name_or_id, filters=filters)
    if output in [lib.OUTPUT_DEFAULT, lib.OUTPUT_WIDE]:
        summary = spyctl_rolebinding.rolebinding_output_summary(
            ctx, sources, (st, et), pipeline, LIMIT_MEM
        )
        cli.show(summary, lib.OUTPUT_RAW)
    else:
        for rolebinding in api.get_rolebinding(
            *ctx.get_api_data(),
            sources,
            (st, et),
            pipeline,
            LIMIT_MEM,
            not lib.is_redirected(),
        ):
            cli.show(rolebinding, output, ndjson=NDJSON)


def handle_get_clusterrolebinding(name_or_id, st, et, output, **filters):
    ctx = cfg.get_current_context()
    sources, filters = _af.ClusterRoleBinding.build_sources_and_filters(
        **filters
    )
    pipeline = _af.ClusterRoleBinding.generate_pipeline(
        name_or_id, filters=filters
    )
    if output in [lib.OUTPUT_DEFAULT, lib.OUTPUT_WIDE]:
        summary = spyctl_crb.clusterrolebinding_output_summary(
            ctx, sources, (st, et), pipeline, LIMIT_MEM
        )
        cli.show(summary, lib.OUTPUT_RAW)
    else:
        for crb in api.get_clusterrolebinding(
            *ctx.get_api_data(),
            sources,
            (st, et),
            pipeline,
            LIMIT_MEM,
            not lib.is_redirected(),
        ):
            cli.show(crb, output, ndjson=NDJSON)


def handle_get_redflags(name_or_id, st, et, output, **filters):
    ctx = cfg.get_current_context()
    sources, filters = _af.RedFlags.build_sources_and_filters(**filters)
    pipeline = _af.RedFlags.generate_pipeline(name_or_id, filters=filters)
    if output in [lib.OUTPUT_DEFAULT, lib.OUTPUT_WIDE]:
        summary = spyctl_flags.flags_output_summary(
            ctx,
            lib.EVENT_REDFLAG_PREFIX,
            sources,
            (st, et),
            pipeline,
            LIMIT_MEM,
        )
        cli.show(summary, lib.OUTPUT_RAW)
    else:
        for flag in api.get_redflags(
            *ctx.get_api_data(),
            sources,
            (st, et),
            pipeline,
            LIMIT_MEM,
            not lib.is_redirected(),
        ):
            cli.show(flag, output, ndjson=NDJSON)


def handle_get_spydertraces(name_or_id, st, et, output, **filters):
    ctx = cfg.get_current_context()
    sources, filters = _af.Spydertraces.build_sources_and_filters(**filters)
    pipeline = _af.Spydertraces.generate_pipeline(name_or_id, filters=filters)
    if output == lib.OUTPUT_DEFAULT:
        summary = spyctl_spytrace.spydertraces_stream_summary_output(
            ctx, sources, (st, et), pipeline, LIMIT_MEM
        )
        cli.show(summary, lib.OUTPUT_RAW)
    elif output == lib.OUTPUT_WIDE:
        summary = spyctl_spytrace.spydertraces_stream_output_wide(
            ctx, sources, (st, et), pipeline, LIMIT_MEM
        )
        cli.show(summary, lib.OUTPUT_RAW)
    else:
        for spydertrace in api.get_spydertraces(
            *ctx.get_api_data(),
            sources,
            (st, et),
            pipeline,
            LIMIT_MEM,
            not lib.is_redirected(),
        ):
            cli.show(spydertrace, output, ndjson=NDJSON)


# ----------------------------------------------------------------- #
#                          Other Resources                          #
# ----------------------------------------------------------------- #


def handle_get_notif_config_templates(name_or_id: str, output, **filters):
    tmpl_type = filters.pop(lib.TYPE_FIELD, None)
    templates: List[spyctl_notif.NotificationConfigTemplate] = []
    if not name_or_id:
        templates.extend(spyctl_notif.NOTIF_CONFIG_TEMPLATES)
    else:
        for tmpl in spyctl_notif.NOTIF_CONFIG_TEMPLATES:
            if fnmatch.fnmatch(
                tmpl.display_name, name_or_id
            ) or tmpl.id == name_or_id.strip("*"):
                templates.append(tmpl)
    if tmpl_type:
        templates = [
            tmpl
            for tmpl in templates
            if tmpl.type == lib.NOTIF_TMPL_MAP.get(tmpl_type)
        ]
    if output in [lib.OUTPUT_DEFAULT, lib.OUTPUT_WIDE]:
        summary = spyctl_notif.notif_config_tmpl_summary_output(templates)
        cli.show(summary, lib.OUTPUT_RAW)
    else:
        for tmpl in templates:
            cli.show(tmpl.as_dict(), output)


# ----------------------------------------------------------------- #
#                Policy Workflow SQL-Based Resources                #
# ----------------------------------------------------------------- #


def handle_get_policies(name_or_id, output, files, st, et, **filters):
    has_matching = filters.pop("has_matching", False)
    file_output = filters.pop("output_to_file", False)
    get_deviations_count = filters.pop("get_deviations", False)
    raw_data = filters.pop("raw_data", False)
    from_archive = filters.pop("from_archive", False)
    version = filters.pop("version", None)
    if version:
        from_archive = True
    ctx = cfg.get_current_context()
    if files:
        policies = []
        for file in files:
            resource_data = lib.load_resource_file(file)
            kind = resource_data.get(lib.KIND_FIELD)
            if kind != lib.POL_KIND:
                cli.try_log(
                    f"Input file {file.name} is not a policy.. skipping",
                    is_warning=True,
                )
                continue
            policies.append(resource_data)
        policies = filt.filter_policies(policies, **filters)
        if name_or_id:
            policies = filt.filter_obj(
                policies,
                [
                    [lib.METADATA_FIELD, lib.NAME_FIELD],
                    [lib.METADATA_FIELD, lib.METADATA_UID_FIELD],
                ],
                name_or_id,
            )
    else:
        params = {
            "name_or_uid_contains": (
                name_or_id.strip("*") if name_or_id else None
            ),
            "from_archive": from_archive,
        }
        policies = api.get_policies(
            *ctx.get_api_data(), raw_data=raw_data, params=params
        )
    if version:
        policies = [
            pol
            for pol in policies
            if pol[lib.METADATA_FIELD][lib.VERSION_FIELD] == version
        ]
    if file_output:
        for policy in policies:
            out_fn = lib.find_resource_filename(policy, "policy_output")
            if output != lib.OUTPUT_JSON:
                output = lib.OUTPUT_YAML
            out_fn = lib.unique_fn(out_fn, output)
            cli.show(
                policy, output, dest=lib.OUTPUT_DEST_FILE, output_fn=out_fn
            )
    elif has_matching:
        policies, no_match_pols = __calculate_has_matching_fprints(
            policies, st, et
        )
        summary = spyctl_policies.policies_summary_output(
            policies, has_matching, no_match_pols
        )
        cli.show(summary, lib.OUTPUT_RAW)
    else:
        if output in [lib.OUTPUT_DEFAULT, lib.OUTPUT_WIDE]:
            summary = spyctl_policies.policies_summary_output(
                policies, (st, et), get_deviations_count
            )
            cli.show(summary, lib.OUTPUT_RAW)
        else:
            for policy in policies:
                cli.show(policy, output, ndjson=NDJSON)


def handle_get_suppression_policies(name_or_id, st, et, output, **filters):
    ctx = cfg.get_current_context()
    policies = api.get_policies(
        *ctx.get_api_data(),
        params={lib.METADATA_TYPE_FIELD: lib.POL_TYPE_TRACE},
    )
    policies = filt.filter_policies(policies, **filters)
    if name_or_id:
        policies = filt.filter_obj(
            policies,
            [
                [lib.METADATA_FIELD, lib.NAME_FIELD],
                [lib.METADATA_FIELD, lib.METADATA_UID_FIELD],
            ],
            name_or_id,
        )
    if output != lib.OUTPUT_DEFAULT:
        policies = s_pol.s_policies_output(policies)
    else:
        policies = s_pol.s_policies_summary_output(policies)
        output = lib.OUTPUT_RAW
    cli.show(policies, output)


def handle_get_rulesets(name_or_id: str, rs_type: str, output: str, **filters):
    ctx = cfg.get_current_context()
    from_archive = filters.pop("from_archive", False)
    version = filters.pop("version", None)
    if version:
        from_archive = True
    params = {
        "type": rs_type,
        "from_archive": from_archive,
    }
    if name_or_id:
        params["name_or_uid_contains"] = name_or_id.strip("*")
    rulesets = api.get_rulesets(*ctx.get_api_data(), params)
    if version:
        rulesets = [
            rs
            for rs in rulesets
            if rs[lib.METADATA_FIELD][lib.VERSION_FIELD] == version
        ]
    if output in [lib.OUTPUT_DEFAULT, lib.OUTPUT_WIDE]:
        summary = spyctl_ruleset.rulesets_summary_output(rulesets)
        cli.show(summary, lib.OUTPUT_RAW)
    else:
        for ruleset in rulesets:
            cli.show(ruleset, output, ndjson=NDJSON)


# ----------------------------------------------------------------- #
#               Policy Workflow Source-Based Resources              #
# ----------------------------------------------------------------- #


def handle_get_fingerprints(
    name_or_id, st, et, output, files: List[IO], latest, **filters
):
    ctx = cfg.get_current_context()
    # Pop any extra options
    raw = filters.pop("raw_data", False)
    group_by = filters.pop("group_by", [])
    sort_by = filters.pop("sort_by", [])
    fprint_type = filters.pop(lib.TYPE_FIELD)
    sources, filters = _af.Fingerprints.build_sources_and_filters(
        use_property_fields=True, **filters
    )
    # Hacky -- need to fix this in the API code
    if "image" in filters:
        value = filters.pop("image")
        filters["image_name"] = value
    name_or_id_expr = None
    if name_or_id:
        name_or_id_expr = _af.Fingerprints.generate_name_or_uid_expr(
            name_or_id
        )
    # Output in desired format
    if output == lib.OUTPUT_DEFAULT:
        summary = spyctl_fprints.fprint_output_summary(
            ctx,
            fprint_type,
            sources,
            filters,
            st,
            et,
            name_or_id_expr,
            group_by=group_by,
            sort_by=sort_by,
        )
        cli.show(summary, lib.OUTPUT_RAW)
    elif output == lib.OUTPUT_WIDE:
        summary = spyctl_fprints.fprint_output_summary(
            ctx,
            fprint_type,
            sources,
            filters,
            st,
            et,
            name_or_id_expr,
            group_by=group_by,
            sort_by=sort_by,
            wide=True,
        )
        cli.show(summary, lib.OUTPUT_RAW)
    else:
        if raw:
            fprints = api.get_guardian_fingerprints(
                *ctx.get_api_data(),
                sources,
                (st, et),
                fprint_type,
                unique=True,
                limit_mem=True,
                expr=name_or_id_expr,
                **filters,
            )
            for fprint in fprints:
                cli.show(fprint, output, ndjson=NDJSON)
        else:
            fprints = list(
                api.get_guardian_fingerprints(
                    *ctx.get_api_data(),
                    sources,
                    (st, et),
                    fprint_type,
                    unique=True,
                    limit_mem=True,
                    expr=name_or_id_expr,
                    **filters,
                )
            )
            fprint_groups = spyctl_fprints.make_fingerprint_groups(fprints)
            tmp_grps = []
            for grps in fprint_groups:
                tmp_grps.extend(grps)
            fprint_groups = spyctl_fprints.fprint_groups_output(tmp_grps)
            cli.show(fprint_groups, output, ndjson=NDJSON)


# ----------------------------------------------------------------- #
#                         Alternative Outputs                       #
# ----------------------------------------------------------------- #


def handle_agent_metrics_json(agents: List[Dict], st, et):
    ctx = cfg.get_current_context()
    cli.try_log("Retrieving metrics records.")
    sources = [agent["muid"] for agent in agents]
    pipeline = _af.AgentMetrics.generate_pipeline()
    for metrics_record in api.get_agent_metrics(
        *ctx.get_api_data(),
        sources,
        (st, et),
        pipeline,
        not lib.is_redirected(),
    ):
        cli.show(metrics_record, lib.OUTPUT_JSON, ndjson=NDJSON)


def handle_agent_usage_csv(agents: List[Dict], st, et, metrics_csv_file: IO):
    ctx = cfg.get_current_context()
    cli.try_log("Retrieving metrics records.")
    agent_map = spy_agents.metrics_ref_map(agents)
    sources = [agent["muid"] for agent in agents]
    pipeline = _af.AgentMetrics.generate_pipeline()
    metrics_csv_file.write(spy_agents.metrics_header())
    for metrics_record in api.get_agent_metrics(
        *ctx.get_api_data(), sources, (st, et), pipeline
    ):
        metrics_csv_file.write(
            spy_agents.usage_line(
                metrics_record, agent_map.get(metrics_record["ref"])
            )
        )


def handle_agent_usage_json(agents: List[Dict], st, et):
    ctx = cfg.get_current_context()
    cli.try_log("Retrieving metrics records.")
    agent_map = spy_agents.metrics_ref_map(agents)
    sources = [agent["muid"] for agent in agents]
    pipeline = _af.AgentMetrics.generate_pipeline()
    for metrics_record in api.get_agent_metrics(
        *ctx.get_api_data(),
        sources,
        (st, et),
        pipeline,
        not lib.is_redirected(),
    ):
        cli.show(
            spy_agents.usage_dict(
                metrics_record, agent_map.get(metrics_record["ref"])
            ),
            lib.OUTPUT_JSON,
            ndjson=NDJSON,
        )


# ----------------------------------------------------------------- #
#                          Helper Functions                         #
# ----------------------------------------------------------------- #


def __calculate_has_matching_fprints(
    policies: List[Dict], st, et
) -> Tuple[List[Dict], List[Dict]]:
    has_matching = []
    no_matching = []
    ctx = cfg.get_current_context()
    sources, filters = _af.Fingerprints.build_sources_and_filters()
    pipeline = _af.Fingerprints.generate_pipeline(filters=filters)
    fingerprints = list(
        api.get_fingerprints(
            *ctx.get_api_data(),
            sources,
            (st, et),
            pipeline=pipeline,
            limit_mem=LIMIT_MEM,
        )
    )
    for policy in policies:
        filters = lib.selectors_to_filters(policy)
        if filt.filter_fingerprints(
            fingerprints,
            use_context_filters=False,
            suppress_warning=True,
            **filters,
        ):
            has_matching.append(policy)
        else:
            no_matching.append(policy)
    return has_matching, no_matching


def __calc_policy_coverage(
    fingerprints: List[Dict], policies: List[Dict] = None
) -> Tuple[List[Dict], float]:
    """Calculates policy coverage from a list of fingerprints

    Args:
        fingerprints (List[Dict]): List of fingerprints to calculate the
            coverage of
        policies (List[Dict], optional): List of policies to calculate
            coverage with. Defaults to None. If None, will download applied
            policies from the Spyderbat Backend.

    Returns:
        Tuple[List[Dict], float]: (List of uncovered fingerprints, coverage
            percentage)
    """
    ctx = cfg.get_current_context()
    if policies is None:
        policies = api.get_policies(*ctx.get_api_data())
    orig_fprint_groups = spyctl_fprints.make_fingerprint_groups(fingerprints)
    total = 0
    for groups in orig_fprint_groups:
        total += len(groups)
    if total == 0:
        cli.err_exit("No fingerprints to calculate coverage of.")
    uncovered_fprints = fingerprints
    for policy in policies:
        filters = lib.selectors_to_filters(policy)
        uncovered_fprints = filt.filter_fingerprints(
            uncovered_fprints,
            use_context_filters=False,
            suppress_warning=True,
            not_matching=True,
            **filters,
        )
    uncovered_fprint_groups = spyctl_fprints.make_fingerprint_groups(
        uncovered_fprints
    )
    uncovered_tot = 0
    for groups in uncovered_fprint_groups:
        uncovered_tot += len(groups)
    coverage = 1 - (uncovered_tot / total)
    return uncovered_fprint_groups, coverage


def __get_fingerprints_matching_files_scope(
    name_or_id, files, latest, st, et, **filters
) -> List[Dict]:
    ctx = cfg.get_current_context()
    if latest and len(files) > 1:
        cli.try_log(
            "Unable to use --latest option for multiple input files",
            is_warning=True,
        )
    elif latest:
        resrc_data = lib.load_resource_file(files[0])
        filters = lib.selectors_to_filters(resrc_data)
        st = __get_latest_timestamp(resrc_data)
        et = time.time()
    fprint_type = filters.get(lib.TYPE_FIELD)
    sources, filters = _af.Fingerprints.build_sources_and_filters(**filters)
    pipeline = _af.Fingerprints.generate_pipeline(
        name_or_id, fprint_type, filters=filters
    )
    orig_fprints = list(
        api.get_fingerprints(
            *ctx.get_api_data(),
            sources,
            (st, et),
            fprint_type=filters.get(lib.TYPE_FIELD),
            pipeline=pipeline,
            limit_mem=LIMIT_MEM,
        )
    )
    rv = []
    for file in files:
        resrc_data = lib.load_resource_file(file)
        filters = lib.selectors_to_filters(resrc_data)
        if len(filters) == 0:
            cli.err_exit(
                f"Unable generate filters for {file.name}. Does it have a"
                " spec field with selectors?"
            )
        rv.extend(
            filt.filter_fingerprints(
                orig_fprints,
                use_context_filters=False,
                suppress_warning=True,
                **filters,
            )
        )
    if not rv:
        cli.try_log("No fingerprints matched input files.")
    return rv


def __get_fingerprints_matching_policies_scope(
    name_or_id, pol_names_or_uids, latest, st, et, **filters
) -> List[Dict]:
    if pol_names_or_uids:
        policies = __get_policies_from_option(pol_names_or_uids)
    else:
        policies = None
    ctx = cfg.get_current_context()
    if latest and len(policies) > 1:
        cli.try_log(
            "Unable to use --latest option for multiple policies",
            is_warning=True,
        )
    elif latest:
        filters = lib.selectors_to_filters(policies[0])
        st = __get_latest_timestamp(policies[0])
        et = time.time()
    fprint_type = filters.get(lib.TYPE_FIELD)
    sources, filters = _af.Fingerprints.build_sources_and_filters(**filters)
    pipeline = _af.Fingerprints.generate_pipeline(
        name_or_id, fprint_type, filters=filters
    )
    orig_fprints = list(
        api.get_fingerprints(
            *ctx.get_api_data(),
            sources,
            (st, et),
            fprint_type=filters.get(lib.TYPE_FIELD),
            pipeline=pipeline,
            limit_mem=LIMIT_MEM,
        )
    )
    rv = []
    for policy in policies:
        filters = lib.selectors_to_filters(policy)
        rv.extend(
            filt.filter_fingerprints(
                orig_fprints,
                use_context_filters=False,
                suppress_warning=True,
                **filters,
            )
        )
    if not rv:
        cli.try_log("No fingerprints matched policies scope.")
    return rv


def __get_latest_timestamp(obj: Dict):
    latest_timestamp = obj.get(lib.METADATA_FIELD, {}).get(
        lib.LATEST_TIMESTAMP_FIELD
    )
    if not latest_timestamp:
        cli.err_exit(
            f"Resource has no {lib.LATEST_TIMESTAMP_FIELD} field in"
            f" its {lib.METADATA_FIELD}"
        )
    return latest_timestamp


def __get_policies_from_option(pol_names_or_uids: List[str]) -> List[Dict]:
    ctx = cfg.get_current_context()
    policies = api.get_policies(*ctx.get_api_data())
    if not policies:
        cli.err_exit("No policies to use as filters.")
    rv = []
    if ALL in pol_names_or_uids:
        rv = policies
    else:
        filtered_pols = {}
        for pol_name_or_uid in pol_names_or_uids:
            pols = filt.filter_obj(
                policies,
                [
                    [lib.METADATA_FIELD, lib.NAME_FIELD],
                    [lib.METADATA_FIELD, lib.METADATA_UID_FIELD],
                ],
                pol_name_or_uid,
            )
            if len(pols) == 0:
                cli.try_log(
                    "Unable to locate policy with name or UID"
                    f" {pol_name_or_uid}",
                    is_warning=True,
                )
                continue
            for policy in pols:
                pol_uid = policy[lib.METADATA_FIELD][lib.METADATA_UID_FIELD]
                filtered_pols[pol_uid] = policy
        rv = list(filtered_pols.values())
    if not policies:
        cli.err_exit("No policies to use as filters.")
    return rv


def __output_time_log(resource, st, et):
    resrc_plural = lib.get_plural_name_from_alias(resource)
    if resrc_plural == lib.DEVIATIONS_RESOURCE.name_plural:
        resrc_plural = f"policy {resrc_plural}"
    if resrc_plural and resrc_plural not in not_time_based:
        cli.try_log(
            f"Getting {resrc_plural} from {lib.epoch_to_zulu(st)} to"
            f" {lib.epoch_to_zulu(et)}"
        )
    elif resrc_plural:
        cli.try_log(f"Getting {resrc_plural}")


def __st_at_least_2hrs(st: float):
    two_hours_secs = 60 * 60 * 2
    now = time.time()
    if now - st < two_hours_secs:
        return now - two_hours_secs
    return st
