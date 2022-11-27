from spyctl.cli import *
from spyctl.fingerprints import (FPRINT_TYPE_CONT, FPRINT_TYPE_SVC,
                                 Fingerprint, fingerprint_summary)


def handle_get_clusters(args):
    names, uids = get_clusters(*read_config(), api_err_exit)
    clusters = []
    for name, uid in sorted(zip(names, uids)):
        clusters.append({'name': name, 'uid': uid})
    show(clusters, args)

def handle_get_namespaces(args):
    namespaces = {}
    for cluster in clusters_input(args):
        ns = get_clust_namespaces(*read_config(), cluster['uid'], time_input(args), api_err_exit)
        namespaces[cluster['name']] = ns
    show(namespaces, args)

def handle_get_machines(args):
    if args.clusters:
        machines = {}
        for cluster in clusters_input(args):
            names, muids = get_clust_muids(*read_config(), cluster['uid'], time_input(args), api_err_exit)
            machines[cluster['name']] = []
            for name, muid in sorted(zip(names, muids)):
                machines[cluster['name']].append({"name": name, "muid": muid})
        show(machines, args)
    else:
        machines = []
        muids, names = get_muids(*read_config(), time_input(args), api_err_exit)
        for name, muid in sorted(zip(names, muids)):
            machines.append({"name": name, "muid": muid})
        show(machines, args)


def handle_get_pods(args):
    clusters = []
    machines = None
    namespaces = None
    if args.clusters:
        clusters = clusters_input(args)
    else:
        names, uids = get_clusters(*read_config(), api_err_exit)
        for name, uid in sorted(zip(names, uids)):
            clusters.append({'name': name, 'uid': uid})
    if args.machines:
        machines = machines_input(args) 
        machines = [m['muid'] for m in machines]
    if args.namespaces:
        namespaces = namespaces_input(args)
    pods = {}
    for cluster in clusters:
        cluster_key = f"{cluster['name']} - {cluster['uid']}"
        pods[cluster_key] = {}
        pod_dict = get_clust_pods(
            *read_config(), cluster['uid'], time_input(args), api_err_exit)
        for ns in pod_dict:
            if namespaces is not None:
                if ns not in namespaces:
                    continue
            new_pods = []
            for name, uid, muid in sorted(zip(*pod_dict[ns])):
                if machines is not None:
                    if muid not in machines:
                        continue
                new_pods.append({
                    'name': name,
                    'uid': uid,
                    'muid': muid
                })
            if len(new_pods) > 0:
                pods[cluster_key][ns] = new_pods
    show(pods, args)


def handle_get_fingerprints(args):
    if args.type == FPRINT_TYPE_SVC and args.pods:
        try_log(
            "Warning: pods specified for service fingerprints, will get all"
            " service fingerprints from the machines corresponding to the"
            " specified pods")
    muids = set()
    pods = None
    specific_search = False
    if args.clusters:
        specific_search = True
        for cluster in clusters_input(args):
            _, clus_muids = get_clust_muids(
                *read_config(), cluster['uid'], time_input(args), api_err_exit)
            muids.update(clus_muids)
    if args.machines:
        specific_search = True
        for machine in machines_input(args):
            muids.add(machine['muid'])
    if args.pods:
        specific_search = True
        pods = []
        for pod in pods_input(args):
            pods.append(pod['name'])
            if pod['muid'] != "unknown":
                muids.add(pod['muid'])
    if not specific_search:
        # We did not specify a source of muids so lets grab them all
        ret_muids, _ = get_muids(
            *read_config(), time_input(args), api_err_exit)
        muids.update(ret_muids)
    fingerprints = []
    found_machs = set()
    for muid in muids:
        tmp_fprints = get_fingerprints(
            *read_config(), muid, time_input(args), api_err_exit)
        if len(tmp_fprints) == 0:
            try_log(f"found no {args.type} fingerprints for", muid)
        else:
            found_machs.add(muid)
        fingerprints += [
            Fingerprint(f) for f in tmp_fprints
            if args.type in f['metadata']['type']]
    try_log(
        f"found {args.type} fingerprints on {len(found_machs)}/{len(muids)}"
        " machines")
    fingerprints = [f.get_output() for f in fingerprints]
    if pods is not None and args.type == FPRINT_TYPE_CONT:
        found_pods = set()

        def in_pods(fprint):
            # TODO: Add pod name to metadata field
            container = fprint['spec']['containerSelector']['containerName']
            for pod in pods:
                if pod in container:
                    found_pods.add(pod)
                    return True
            return False
        fingerprints = list(filter(in_pods, fingerprints))
        for pod in sorted(set(pods) - found_pods):
            try_log("no fingerprints found for pod", pod)
        try_log(f"Found fingerprints in {len(found_pods)}/{len(pods)} pods")
    alternative_outputs = {
        OUTPUT_SUMMARY: fingerprint_summary
    }
    show(fingerprints, args, alternative_outputs)


def handle_get_policies(args):
    pass
