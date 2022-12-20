import json
import time
from typing import Dict, List, Tuple

import yaml

import spyctl.api as api
import spyctl.cli as cli
import spyctl.config.configs as u_conf
import spyctl.config.configs as cfg
import spyctl.config.secrets as s
import spyctl.filter_resource as filt
import spyctl.resources.clusters as spyctl_clusts
import spyctl.resources.fingerprints as spyctl_fprints
import spyctl.resources.machines as spyctl_machines
import spyctl.resources.namespaces as spyctl_names
import spyctl.resources.pods as spyctl_pods
import spyctl.resources.policies as p
import spyctl.spyctl_lib as lib


def handle_get(resource, name_or_id, st, et, latest, output, **filters):
    if latest is not None:
        try:
            with open(latest) as f:
                resrc_data = yaml.load(f, yaml.Loader)
        except Exception:
            try:
                resrc_data = json.load(latest)
            except Exception:
                cli.err_exit("Unable to load resource file.")
        latest_timestamp = resrc_data.get(lib.METADATA_FIELD, {}).get(
            lib.LATEST_TIMESTAMP_FIELD
        )
        if latest_timestamp is not None:
            st = lib.time_inp(latest_timestamp)
        else:
            cli.try_log(
                f"No {lib.LATEST_TIMESTAMP_FIELD} found in provided resource"
                " metadata field."
            )
        filters = lib.selectors_to_filters(resrc_data)
    if resource == lib.CLUSTERS_RESOURCE:
        handle_get_clusters(output, **filters)
    if resource == lib.FINGERPRINTS_RESOURCE:
        handle_get_fingerprints(name_or_id, st, et, output, **filters)
    if resource == lib.MACHINES_RESOURCE:
        handle_get_machines(output, **filters)
    if resource == lib.NAMESPACES_RESOURCE:
        handle_get_namespaces(name_or_id, st, et, output, **filters)
    if resource == lib.PODS_RESOURCE:
        handle_get_pods(name_or_id, st, et, output, **filters)
    if resource == lib.SECRETS_RESOURCE:
        handle_get_secrets(output, name_or_id)


def handle_get_secrets(output, name=None):
    s.get_secrets(output, name)


def handle_get_clusters(output: str, **filters: Dict):
    ctx = cfg.get_current_context()
    clusters = api.get_clusters(*ctx.get_api_data(), cli.api_err_exit)
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
    if output != lib.OUTPUT_DEFAULT:
        output_clusters = spyctl_clusts.clusters_output(output_clusters)
    cli.show(
        output_clusters,
        output,
        {lib.OUTPUT_DEFAULT: spyctl_clusts.clusters_summary_output},
    )


def handle_get_namespaces(name, st, et, output, **filters):
    ctx = cfg.get_current_context()
    clusters = api.get_clusters(*ctx.get_api_data(), cli.api_err_exit)
    clusters = filt.filter_clusters(clusters, **filters)
    namespaces = api.get_namespaces(
        *ctx.get_api_data(), clusters, (st, et), cli.api_err_exit
    )
    namespaces = filt.filter_namespaces(
        namespaces, clusters_data=clusters, **filters
    )
    if output != lib.OUTPUT_DEFAULT:
        namespaces = spyctl_names.namespaces_output(namespaces)
    cli.show(
        namespaces,
        output,
        {lib.OUTPUT_DEFAULT: spyctl_names.namespace_summary_output},
    )


def handle_get_machines(output: str, **filters: Dict):
    ctx = cfg.get_current_context()
    machines = api.get_machines(*ctx.get_api_data(), cli.api_err_exit)
    machines = filt.filter_machines(machines, **filters)
    cli.show(machines, output)
    if output != lib.OUTPUT_DEFAULT:
        machines = spyctl_machines.machines_output(machines)
    cli.show(
        machines,
        output,
        {lib.OUTPUT_DEFAULT: spyctl_machines.machines_summary_output},
    )


def handle_get_pods(name_or_id, st, et, output, **filters):
    ctx = cfg.get_current_context()
    clusters = api.get_clusters(*ctx.get_api_data(), cli.api_err_exit)
    clusters = filt.filter_clusters(clusters, **filters)
    pods = api.get_pods(
        *ctx.get_api_data(), clusters, (st, et), cli.api_err_exit
    )
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
    machines = api.get_machines(*ctx.get_api_data(), cli.api_err_exit)
    clusters = None
    if cfg.CLUSTER_FIELD in filters or cfg.CLUSTER_FIELD in ctx.get_filters():
        clusters = api.get_clusters(*ctx.get_api_data(), cli.api_err_exit)
    machines = filt.filter_machines(machines, clusters, **filters)
    muids = [m["uid"] for m in machines]
    fingerprints = api.get_fingerprints(
        *ctx.get_api_data(), muids, (st, et), cli.api_err_exit
    )
    fingerprints = filt.filter_fingerprints(fingerprints, **filters)
    fprint_groups = spyctl_fprints.make_fingerprint_groups(fingerprints)
    if name_or_id:
        name_or_id += "*" if name_or_id[-1] != "*" else name_or_id
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


def get_policy_input(args) -> p.Policy:
    policies = cli.policy_input([args.policy_file])
    if len(policies) > 1:
        cli.err_exit(
            "multiple policies provided; only retrieving first policy"
            " at a time"
        )
    elif len(policies) == 0:
        return None
    return policies[0]


def handle_get_policies(args):
    uid = args.uid
    if uid is None:
        policy = get_policy_input(args)
        if policy is not None:
            uid = policy.get_uid()
    if uid is None:
        params = {api.GET_POL_TYPE: args.type}
        # Get list of all policies
        policies = api.get_policies(
            *u_conf.read_config(), cli.api_err_exit, params
        )
        policies = [p.Policy(pol) for pol in policies]
        cli.show(policies, args)
    else:
        # Get specific policy
        policy = api.get_policy(*u_conf.read_config(), uid, cli.api_err_exit)
        policy = p.Policy(policy)
        cli.show(policy, args)
