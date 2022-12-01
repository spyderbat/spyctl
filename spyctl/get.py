import spyctl.user_config as u_conf
import spyctl.api as api
import spyctl.args as a
import spyctl.policies as p
import spyctl.cli as cli
from spyctl.fingerprints import (
    FPRINT_TYPE_CONT,
    FPRINT_TYPE_SVC,
    Fingerprint,
    fingerprint_summary,
)


def handle_get_clusters(args):
    names, uids = api.get_clusters(*u_conf.read_config(), cli.api_err_exit)
    clusters = []
    for name, uid in sorted(zip(names, uids)):
        clusters.append({"name": name, "uid": uid})
    cli.show(clusters, args)


def handle_get_namespaces(args):
    namespaces = {}
    for cluster in cli.clusters_input(args):
        ns = api.get_clust_namespaces(
            *u_conf.read_config(),
            cluster["uid"],
            cli.time_input(args),
            cli.api_err_exit,
        )
        namespaces[cluster["name"]] = ns
    cli.show(namespaces, args)


def handle_get_machines(args):
    if args.clusters:
        machines = {}
        for cluster in cli.clusters_input(args):
            names, muids = api.get_clust_muids(
                *u_conf.read_config(),
                cluster["uid"],
                cli.time_input(args),
                cli.api_err_exit,
            )
            machines[cluster["name"]] = []
            for name, muid in sorted(zip(names, muids)):
                machines[cluster["name"]].append({"name": name, "muid": muid})
        cli.show(machines, args)
    else:
        machines = []
        muids, names = api.get_muids(
            *u_conf.read_config(), cli.time_input(args), cli.api_err_exit
        )
        for name, muid in sorted(zip(names, muids)):
            machines.append({"name": name, "muid": muid})
        cli.show(machines, args)


def handle_get_pods(args):
    clusters = []
    machines = None
    namespaces = None
    if args.clusters:
        clusters = cli.clusters_input(args)
    else:
        names, uids = api.get_clusters(*u_conf.read_config(), cli.api_err_exit)
        for name, uid in sorted(zip(names, uids)):
            clusters.append({"name": name, "uid": uid})
    if args.machines:
        machines = cli.machines_input(args)
        machines = [m["muid"] for m in machines]
    if args.namespaces:
        namespaces = cli.namespaces_input(args)
    pods = {}
    for cluster in clusters:
        cluster_key = f"{cluster['name']} - {cluster['uid']}"
        pods[cluster_key] = {}
        pod_dict = api.get_clust_pods(
            *u_conf.read_config(),
            cluster["uid"],
            cli.time_input(args),
            cli.api_err_exit,
        )
        for ns in pod_dict:
            if namespaces is not None:
                if ns not in namespaces:
                    continue
            new_pods = []
            for name, uid, muid in sorted(zip(*pod_dict[ns])):
                if machines is not None:
                    if muid not in machines:
                        continue
                new_pods.append({"name": name, "uid": uid, "muid": muid})
            if len(new_pods) > 0:
                pods[cluster_key][ns] = new_pods
    cli.show(pods, args)


def handle_get_fingerprints(args):
    if args.type == FPRINT_TYPE_SVC and args.pods:
        cli.try_log(
            "Warning: pods specified for service fingerprints, will get all"
            " service fingerprints from the machines corresponding to the"
            " specified pods"
        )
    muids = set()
    pods = None
    specific_search = False
    if args.clusters:
        specific_search = True
        for cluster in cli.clusters_input(args):
            _, clus_muids = api.get_clust_muids(
                *u_conf.read_config(),
                cluster["uid"],
                cli.time_input(args),
                cli.api_err_exit,
            )
            muids.update(clus_muids)
    if args.machines:
        specific_search = True
        for machine in cli.machines_input(args):
            muids.add(machine["muid"])
    if args.pods:
        specific_search = True
        pods = []
        for pod in cli.pods_input(args):
            pods.append(pod["name"])
            if pod["muid"] != "unknown":
                muids.add(pod["muid"])
    if not specific_search:
        # We did not specify a source of muids so lets grab them all
        ret_muids, _ = api.get_muids(
            *u_conf.read_config(), cli.time_input(args), cli.api_err_exit
        )
        muids.update(ret_muids)
    fingerprints = []
    found_machs = set()
    for muid in muids:
        tmp_fprints = api.get_fingerprints(
            *u_conf.read_config(), muid, cli.time_input(args), cli.api_err_exit
        )
        if len(tmp_fprints) == 0:
            pass
            # cli.try_log(f"found no {args.type} fingerprints for", muid)
        else:
            found_machs.add(muid)
        fingerprints += [
            Fingerprint(f)
            for f in tmp_fprints
            if args.type in f["metadata"]["type"]
        ]
    cli.try_log(
        f"found {args.type} fingerprints on {len(found_machs)}/{len(muids)}"
        " machines"
    )
    fingerprints = [f.get_output() for f in fingerprints]
    if pods is not None and args.type == FPRINT_TYPE_CONT:
        found_pods = set()

        def in_pods(fprint):
            # TODO: Add pod name to metadata field
            container = fprint["spec"]["containerSelector"]["containerName"]
            for pod in pods:
                if pod in container:
                    found_pods.add(pod)
                    return True
            return False

        fingerprints = list(filter(in_pods, fingerprints))
        for pod in sorted(set(pods) - found_pods):
            cli.try_log("no fingerprints found for pod", pod)
        cli.try_log(
            f"Found fingerprints in {len(found_pods)}/{len(pods)} pods"
        )
    alternative_outputs = {a.OUTPUT_SUMMARY: fingerprint_summary}
    cli.show(fingerprints, args, alternative_outputs)


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
