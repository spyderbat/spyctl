from typing import Dict

import spyctl.api as api
import spyctl.cli as cli
import spyctl.config.configs as cfg
import spyctl.filter_resource as filt
import spyctl.resources.clusters as spyctl_clusts
import spyctl.resources.fingerprints as spyctl_fprints
import spyctl.resources.machines as spyctl_machines
import spyctl.resources.namespaces as spyctl_names
import spyctl.resources.pods as spyctl_pods
import spyctl.resources.nodes as spyctl_nodes
import spyctl.resources.policies as spyctl_policies
import spyctl.spyctl_lib as lib


def handle_get(
    resource, name_or_id, st, et, file, latest, exact, output, **filters
):
    if latest and not file:
        cli.err_exit(
            "filename must be provided to use '--latest' flag. Spyctl uses the"
            " input file to generate proper filters and also uses its"
            f" {lib.LATEST_TIMESTAMP_FIELD} for the starting time of the"
            " search if applicable."
        )
    if file:
        resrc_data = lib.load_resource_file(file)
        if latest:
            latest_timestamp = resrc_data.get(lib.METADATA_FIELD, {}).get(
                lib.LATEST_TIMESTAMP_FIELD
            )
            if not latest_timestamp:
                cli.err_exit(
                    f"Resource has no {lib.LATEST_TIMESTAMP_FIELD} field in"
                    f" its {lib.METADATA_FIELD}"
                )
            st = lib.time_inp(latest_timestamp)
        filters = lib.selectors_to_filters(resrc_data)
        if len(filters) == 0:
            cli.err_exit(
                "Unable generate filters from input document. Does it have a"
                " spec field with selectors?"
            )
    if name_or_id and not exact:
        name_or_id += "*" if name_or_id[-1] != "*" else name_or_id
        name_or_id = "*" + name_or_id if name_or_id[0] != "*" else name_or_id
    if resource == lib.CLUSTERS_RESOURCE:
        handle_get_clusters(name_or_id, output, **filters)
    elif resource == lib.FINGERPRINTS_RESOURCE:
        handle_get_fingerprints(name_or_id, st, et, output, **filters)
    elif resource == lib.MACHINES_RESOURCE:
        handle_get_machines(name_or_id, output, **filters)
    elif resource == lib.NAMESPACES_RESOURCE:
        handle_get_namespaces(name_or_id, st, et, output, **filters)
    elif resource == lib.NODES_RESOURCE:
        handle_get_nodes(name_or_id, st, et, output, **filters)
    elif resource == lib.PODS_RESOURCE:
        handle_get_pods(name_or_id, st, et, output, **filters)
    elif resource == lib.POLICIES_RESOURCE:
        handle_get_policies(name_or_id, output, **filters)
    else:
        cli.err_exit(f"The 'get' command is not supported for {resource}")


def handle_get_clusters(name_or_id, output: str, **filters: Dict):
    ctx = cfg.get_current_context()
    clusters = api.get_clusters(*ctx.get_api_data())
    clusters = filt.filter_clusters(clusters, **filters)
    output_clusters = []
    for cluster in clusters:
        output_clusters.append(
            {
                "name": cluster["name"],
                "uid": cluster["uid"],
                "cluster_details": {
                    "first_seen": cluster["valid_from"],
                    "last_data": cluster["last_data"],
                    "cluster_id": cluster["cluster_details"]["cluster_uid"],
                },
            }
        )
    if name_or_id:
        output_clusters = filt.filter_obj(
            output_clusters, ["name", "uid"], name_or_id
        )
    if output != lib.OUTPUT_DEFAULT:
        output_clusters = spyctl_clusts.clusters_output(output_clusters)
    cli.show(
        output_clusters,
        output,
        {lib.OUTPUT_DEFAULT: spyctl_clusts.clusters_summary_output},
    )


def handle_get_namespaces(name, st, et, output, **filters):
    ctx = cfg.get_current_context()
    clusters = api.get_clusters(*ctx.get_api_data())
    clusters = filt.filter_clusters(clusters, **filters)
    namespaces = api.get_namespaces(*ctx.get_api_data(), clusters, (st, et))
    namespaces = filt.filter_namespaces(
        namespaces, clusters_data=clusters, **filters
    )
    if name:
        namespaces = filt.filter_obj(namespaces, ["namespaces"], name)
    if output != lib.OUTPUT_DEFAULT:
        namespaces = spyctl_names.namespaces_output(namespaces)
    cli.show(
        namespaces,
        output,
        {lib.OUTPUT_DEFAULT: spyctl_names.namespace_summary_output},
    )


def handle_get_machines(name_or_id, output: str, **filters: Dict):
    ctx = cfg.get_current_context()
    machines = api.get_machines(*ctx.get_api_data())
    machines = filt.filter_machines(machines, **filters)
    if name_or_id:
        machines = filt.filter_obj(machines, ["name", "uid"], name_or_id)
    if output != lib.OUTPUT_DEFAULT:
        machines = spyctl_machines.machines_output(machines)
    cli.show(
        machines,
        output,
        {lib.OUTPUT_DEFAULT: spyctl_machines.machines_summary_output},
    )


def handle_get_nodes(name_or_id, st, et, output: str, **filters: Dict):
    ctx = cfg.get_current_context()
    clusters = api.get_clusters(*ctx.get_api_data())
    clusters = filt.filter_clusters(clusters, **filters)
    nodes = api.get_nodes(*ctx.get_api_data(), clusters, (st, et))
    nodes = filt.filter_nodes(nodes, **filters)
    if name_or_id:
        nodes = filt.filter_obj(
            nodes,
            [f"{lib.METADATA_FIELD}.{lib.METADATA_NAME_FIELD}", "id"],
            name_or_id,
        )
    if output != lib.OUTPUT_DEFAULT:
        nodes = spyctl_nodes.nodes_output(nodes)
    cli.show(
        nodes,
        output,
        {lib.OUTPUT_DEFAULT: spyctl_nodes.nodes_output_summary},
    )


def handle_get_pods(name_or_id, st, et, output, **filters):
    ctx = cfg.get_current_context()
    clusters = api.get_clusters(*ctx.get_api_data())
    clusters = filt.filter_clusters(clusters, **filters)
    pods = api.get_pods(*ctx.get_api_data(), clusters, (st, et))
    pods = filt.filter_pods(pods)
    if name_or_id:
        pods = filt.filter_obj(pods, ["metadata.name", "id"], name_or_id)
    if output != lib.OUTPUT_DEFAULT:
        pods = spyctl_pods.pods_output(pods)
    cli.show(
        pods,
        output,
        {lib.OUTPUT_DEFAULT: spyctl_pods.pods_output_summary},
    )


def handle_get_fingerprints(name_or_id, st, et, output, **filters):
    ctx = cfg.get_current_context()
    machines = api.get_machines(*ctx.get_api_data())
    clusters = None
    if cfg.CLUSTER_FIELD in filters or cfg.CLUSTER_FIELD in ctx.get_filters():
        clusters = api.get_clusters(*ctx.get_api_data())
    machines = filt.filter_machines(machines, clusters, **filters)
    muids = [m["uid"] for m in machines]
    fingerprints = api.get_fingerprints(*ctx.get_api_data(), muids, (st, et))
    fingerprints = filt.filter_fingerprints(fingerprints, **filters)
    fprint_groups = spyctl_fprints.make_fingerprint_groups(fingerprints)
    if name_or_id:
        cont_fprint_grps, svc_fprint_grps = fprint_groups
        cont_fprint_grps = filt.filter_obj(
            cont_fprint_grps,
            [
                f"{lib.METADATA_FIELD}.{lib.IMAGE_FIELD}",
                f"{lib.METADATA_FIELD}.{lib.IMAGEID_FIELD}",
            ],
            name_or_id,
        )
        svc_fprint_grps = filt.filter_obj(
            svc_fprint_grps,
            [
                f"{lib.METADATA_FIELD}.{lib.CGROUP_FIELD}",
            ],
            name_or_id,
        )
        fprint_groups = (cont_fprint_grps, svc_fprint_grps)
    fprint_groups = filt.filter_fprint_groups(fprint_groups, **filters)
    if output != lib.OUTPUT_DEFAULT:
        tmp_grps = []
        for grps in fprint_groups:
            tmp_grps.extend(grps)
        fprint_groups = spyctl_fprints.fprint_groups_output(tmp_grps)
    cli.show(
        fprint_groups,
        output,
        {lib.OUTPUT_DEFAULT: spyctl_fprints.fprint_grp_output_summary},
    )


def handle_get_policies(name_or_id, output, **filters):
    ctx = cfg.get_current_context()
    policies = api.get_policies(*ctx.get_api_data())
    policies = filt.filter_policies(policies, **filters)
    if name_or_id:
        policies = filt.filter_obj(
            policies,
            [
                f"{lib.METADATA_FIELD}.{lib.NAME_FIELD}",
                f"{lib.METADATA_FIELD}.{lib.METADATA_UID_FIELD}",
            ],
            name_or_id,
        )
    if output != lib.OUTPUT_DEFAULT:
        policies = spyctl_policies.policies_output(policies)
    cli.show(
        policies,
        output,
        {lib.OUTPUT_DEFAULT: spyctl_policies.policies_summary_output},
    )
