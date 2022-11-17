from cli import *
from fingerprints import Fingerprint, FPRINT_TYPE_CONT, FPRINT_TYPE_SVC, fingerprint_summary


def clusters_input(args):
    inp = get_open_input(args.clusters)

    def get_uid(clust_obj):
        if 'uid' in clust_obj:
            return clust_obj['uid']
        else:
            err_exit("cluster object input was missing 'uid'")
    names_or_uids = handle_list(inp, get_uid)
    names, uids = get_clusters(*read_config(), api_err_exit)
    clusters = []
    for string in names_or_uids:
        found = False
        for name, uid in zip(names, uids):
            if string == uid or string == name:
                clusters.append({'name': name, 'uid': uid})
                found = True
                break
        if not found:
            err_exit(f"cluster '{string}' did not exist in specified organization")
    clusters.sort(key=lambda c: c['name'])
    return clusters


def machines_input(args):
    inp = get_open_input(args.machines)
    def get_muid(mach):
        if isinstance(mach, list):
            return [get_muid(m) for m in mach]
        elif 'muid' in mach:
            return mach['muid']
        else:
            err_exit("machine object was missing 'muid'")
    names_or_uids = handle_list(inp, get_muid)
    muids, names = get_muids(*read_config(), time_input(args), api_err_exit)
    machs = []
    for string in names_or_uids:
        found = False
        for name, muid in zip(names, muids):
            if string == muid or string == name:
                machs.append({'name': name, 'muid': muid})
                found = True
                break
        if not found:
            err_exit(f"machine '{string}' did not exist in specified organization")
    machs.sort(key=lambda m: m['name'])
    return machs


def pods_input(args):
    inp = get_open_input(args.pods)
    def get_uid(pod_obj):
        if isinstance(pod_obj, list):
            return [get_uid(p) for p in pod_obj]
        elif 'uid' in pod_obj:
            return pod_obj['uid']
        else:
            ret = []
            for sub in pod_obj.values():
                if not isinstance(sub, list):
                    err_exit("pod object was missing 'uid'")
                ret.extend(get_uid(sub))
            return ret
    names_or_uids = handle_list(inp, get_uid)
    _, clus_uids = get_clusters(*read_config(), api_err_exit)
    pods = []
    all_pods = ([], [], [])
    for clus_uid in clus_uids:
        pod_dict = get_clust_pods(*read_config(), clus_uid, time_input(args), api_err_exit)
        for list_tup in pod_dict.values():
            for i in range(len(all_pods)):
                all_pods[i].extend(list_tup[i])
    for string in names_or_uids:
        found = False
        for name, uid, muid in zip(*all_pods):
            if string == name or string == uid:
                pods.append({'name': name, 'uid': uid, 'muid': muid})
                found = True
                break
        if not found:
            try_log(f"pod '{string}' did not exist in specified organization")
            # err_exit(f"pod '{string}' did not exist in specified organization")
    pods.sort(key=lambda p: p['name'])
    return pods


def namespaces_input(args):
    inp = get_open_input(args.namespaces)
    def get_strings(namespace):
        if isinstance(namespace, list):
            return [get_strings(n) for n in namespace]
        else:
            return namespace
    return sorted(handle_list(inp, get_strings))


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
    for muid in muids:
        tmp_fprints = get_fingerprints(
            *read_config(), muid, time_input(args), api_err_exit)
        if len(tmp_fprints) == 0:
            try_log("found no fingerprints for", muid)
        fingerprints += [
            Fingerprint(f) for f in tmp_fprints
            if args.type in f['metadata']['type']]
    fingerprints = [f.get_output() for f in fingerprints]
    if pods is not None and args.type == FPRINT_TYPE_CONT:
        found_pods = set()

        def in_pods(fprint):
            container = fprint['spec']['containerSelector']['containerName']
            for pod in pods:
                if pod in container:
                    found_pods.add(pod)
                    return True
            return False
        fingerprints = list(filter(in_pods, fingerprints))
        for pod in sorted(set(pods) - found_pods):
            try_log("no fingerprints found for pod", pod)
    alternative_outputs = {
        OUTPUT_SUMMARY: fingerprint_summary
    }
    show(fingerprints, args, alternative_outputs)


def handle_get_policies(args):
    pass
