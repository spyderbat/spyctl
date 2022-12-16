import time
from typing import Dict, List, Tuple

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
from spyctl.resources.fingerprints import (
    FPRINT_TYPE_CONT,
    FPRINT_TYPE_SVC,
    Fingerprint,
    fingerprint_summary,
)


def handle_get(resource, name_or_id, st, et, output, **filters):
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
    fprint_groups = filt.filter_fingerprints(fprint_groups, **filters)
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


# def handle_get_fingerprints(args):
#     if args.type == FPRINT_TYPE_SVC and args.pods:
#         cli.try_log(
#             "Warning: pods specified for service fingerprints, will get all"
#             " service fingerprints from the machines corresponding to the"
#             " specified pods"
#         )
#     muids = set()
#     pods = None
#     specific_search = False
#     if args.clusters:
#         specific_search = True
#         for cluster in cli.clusters_input(args):
#             _, clus_muids = api.get_clust_muids(
#                 *u_conf.read_config(),
#                 cluster["uid"],
#                 cli.time_input(args),
#                 cli.api_err_exit,
#             )
#             muids.update(clus_muids)
#     if args.machines:
#         specific_search = True
#         for machine in cli.machines_input(args):
#             muids.add(machine["muid"])
#     if args.pods:
#         specific_search = True
#         pods = []
#         for pod in cli.pods_input(args):
#             pods.append(pod["name"])
#             if pod["muid"] != "unknown":
#                 muids.add(pod["muid"])
#     if not specific_search:
#         # We did not specify a source of muids so lets grab them all
#         ret_muids, _ = api.get_muids(
#             *u_conf.read_config(), cli.time_input(args), cli.api_err_exit
#         )
#         muids.update(ret_muids)
#     fingerprints = []
#     found_machs = set()
#     for muid in muids:
#         tmp_fprints = api.get_fingerprints(
#             *u_conf.read_config(), muid, cli.time_input(args), cli.api_err_exit
#         )
#         if len(tmp_fprints) == 0:
#             pass
#             # cli.try_log(f"found no {args.type} fingerprints for", muid)
#         else:
#             found_machs.add(muid)
#         fingerprints += [
#             Fingerprint(f)
#             for f in tmp_fprints
#             if args.type in f["metadata"]["type"]
#         ]
#     cli.try_log(
#         f"found {args.type} fingerprints on {len(found_machs)}/{len(muids)}"
#         " machines"
#     )
#     fingerprints = [f.get_output() for f in fingerprints]
#     if pods is not None and args.type == FPRINT_TYPE_CONT:
#         found_pods = set()

#         def in_pods(fprint):
#             # TODO: Add pod name to metadata field
#             container = fprint["spec"]["containerSelector"]["containerName"]
#             for pod in pods:
#                 if pod in container:
#                     found_pods.add(pod)
#                     return True
#             return False

#         fingerprints = list(filter(in_pods, fingerprints))
#         for pod in sorted(set(pods) - found_pods):
#             cli.try_log("no fingerprints found for pod", pod)
#         cli.try_log(
#             f"Found fingerprints in {len(found_pods)}/{len(pods)} pods"
#         )
#     alternative_outputs = {"summary": fingerprint_summary}
#     cli.show(fingerprints, args, alternative_outputs)


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
