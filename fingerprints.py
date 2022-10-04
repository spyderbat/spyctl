import sys
import subprocess
import yaml

from merge import DiffDumper, MergeDumper

from simple_term_menu import TerminalMenu


def prepare_fingerprints(fingerprints):
    # Get the latest version of each ID
    latest = {}
    for fprint in fingerprints:
        latest[fprint['id']] = fprint
    # Unique the fingerprints based on checksum
    checksums = {}
    for fprint in latest.values():
        checksum = fprint['checksum']
        fprint_yaml = yaml.dump(dict(spec=fprint['spec']), sort_keys=False)
        if checksum not in checksums:
            checksums[checksum] = {
                'print': fprint,
                'suppressed': 0,
                'str_val':
                    f"{fprint['service_name']} --" +
                    f" proc_nodes: {fprint['proc_fprint_len']}," +
                    f" ingress_nodes: {fprint['ingress_len']}," +
                    f" egress_nodes: {fprint['egress_len']} |" +
                    f" {fprint_yaml}"
            }
        else:
            checksums[checksum]['suppressed'] += 1
            checksums[checksum]['str_val'] = \
                f"{fprint['service_name']}" + \
                f" ({checksums[checksum]['suppressed']} suppressed) --" + \
                f" proc_nodes: {fprint['proc_fprint_len']}," + \
                f" ingress_nodes: {fprint['ingress_len']}," + \
                f" egress_nodes: {fprint['egress_len']} |" + \
                f" {fprint_yaml}"
    rv = list(checksums.values())
    rv.sort(key=lambda d: d['str_val'])
    return list(rv)


def get_fingerprint_output(fingerprint_rec):
    rv = {
        "spec": fingerprint_rec['spec'],
        "metadata": {
            "service_name": fingerprint_rec['service_name'],
            "id": fingerprint_rec['id'],
            "checksum": fingerprint_rec['checksum'],
            "muid": fingerprint_rec['muid']
        }
    }
    root_puid = fingerprint_rec.get('root_puid')
    if root_puid is not None:
        rv['metadata']['root_puid'] = root_puid
    return rv


def load_fingerprint_from_output(fingerprint_out):
    meta = fingerprint_out['metadata']
    proc_fprint_len = 0
    node_queue = fingerprint_out['spec']['processPolicy'].copy()
    for node in node_queue:
        proc_fprint_len += 1
        if 'children' in node:
            node_queue += node['children']
    ingress_len = len(fingerprint_out['spec']['networkPolicy']['ingress'])
    egress_len = len(fingerprint_out['spec']['networkPolicy']['egress'])
    rv = {
        "spec": fingerprint_out['spec'],
        "service_name": meta['service_name'],
        "muid": meta['muid'],
        "checksum": meta['checksum'],
        "id": meta['id'],
        "proc_fprint_len": proc_fprint_len,
        "ingress_len": ingress_len,
        "egress_len": egress_len
    }
    root_puid = meta.get('root_puid')
    if root_puid is not None:
        rv['root_puid'] = root_puid
    return rv


def dialog(title):
    index = TerminalMenu(
        ['[y] yes', '[n] no'],
        title=title
    ).show()
    return index == 0


def prepeared_to_output(fingerprints):
    return [get_fingerprint_output(fprint['print']) for fprint in fingerprints]


def save_service_fingerprint_yaml(fingerprints):
    save_options = [
        "[1] Save individual file(s) (for editing & uploading)",
        "[2] Save in one file (for viewing)",
        "[3] Back"
    ]
    index = TerminalMenu(
        save_options,
        title="Select an option:"
    ).show() if len(fingerprints) > 1 else 0
    if index is None or index == 2:
        return
    if index == 0:
        for fingerprint in fingerprints:
            if dialog(f"Save fingerprint for {fingerprint['metadata']['service_name']}?"):
                while True:
                    filename = input(f"Output filename [{fingerprint['metadata']['service_name']}.yml]: ")
                    if filename is None or filename == '':
                        filename = f"{fingerprint['metadata']['service_name']}.yml"
                    try:
                        with open(filename, 'w') as f:
                            yaml.dump(fingerprint, f, sort_keys=False)
                        break
                    except IOError:
                        print("Error: unable to open file")
    elif index == 1:
        if dialog("Save all selected fingerprints in one file?"):
            while True:
                default = "multi-service-fingerprints.yml"
                filename = input(f"Output filename [{default}]: ")
                if filename is None or filename == '':
                    filename = default
                try:
                    with open(filename, 'w') as f:
                        first = True
                        for fingerprint in fingerprints:
                            if first:
                                first = False
                            else:
                                f.write("---\n")
                            yaml.dump(fingerprint, f, sort_keys=False)
                    break
                except IOError:
                    print("Error: unable to open file")


def save_merged_fingerprint_yaml(fingerprint):
    while True:
        default = f"{fingerprint['metadata']['service_name']}.yml"
        filename = input(f"Output filename [{default}]: ")
        if filename is None or filename == '':
            filename = default
        try:
            with open(filename, 'w') as f:
                yaml.dump(fingerprint, f, Dumper=MergeDumper, sort_keys=False)
            break
        except IOError:
            print("Error: unable to open file")
