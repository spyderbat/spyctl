import sys
import subprocess
import yaml

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
                    f" proc_nodes: {fprint['proc_prof_len']}," +
                    f" ingress_nodes: {fprint['ingress_len']}," +
                    f" egress_nodes: {fprint['egress_len']} |" +
                    f" {fprint_yaml}"
            }
        else:
            checksums[checksum]['suppressed'] += 1
            checksums[checksum]['str_val'] = \
                f"{fprint['service_name']}" + \
                f" ({checksums[checksum]['suppressed']} suppressed) --" + \
                f" proc_nodes: {fprint['proc_prof_len']}," + \
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
            "checksum": fingerprint_rec['checksum'],
            "muid": fingerprint_rec['muid']
        }
    }
    root_puid = fingerprint_rec.get('root_puid')
    if root_puid is not None:
        rv['metadata']['root_puid'] = root_puid
    return rv


def show_fingerprint_diff(fingerprints):
    fn1 = "/tmp/fprint_diff1"
    fn2 = "/tmp/fprint_diff2"
    with open(fn1, 'w') as f:
        fingerprint = fingerprints[0]['print']
        output = get_fingerprint_output(fingerprint)
        yaml.dump(output, f, sort_keys=False,)
    with open(fn2, "w") as f:
        fingerprint = fingerprints[1]['print']
        output = get_fingerprint_output(fingerprint)
        yaml.dump(output, f, sort_keys=False,)
    diff_proc = subprocess.Popen(
        ['sdiff', fn1, fn2],
        stdout=subprocess.PIPE)
    less_proc = subprocess.Popen(
        ['less', '-F', '-R', '-S', '-X', '-K'],
        stdin=diff_proc.stdout, stdout=sys.stdout)
    less_proc.wait()


def dialog(title):
    index = TerminalMenu(
        ['[y] yes', '[n] no'],
        title=title
    ).show()
    return index == 0


def save_service_fingerprint_yaml(fingerprints):
    save_options = [
        "[1] Save individual file(s) (for editing & uploading)",
        "[2] Save in one file (for viewing)",
        "[3] Back"
    ]
    index = TerminalMenu(
        save_options,
        title="Select an option:"
    ).show()
    if index is None or index == 2:
        return
    if index == 0:
        for fingerprint_dict in fingerprints:
            fingerprint = fingerprint_dict['print']
            if dialog(f"Save fingerprint for {fingerprint['service_name']}?"):
                output = get_fingerprint_output(fingerprint)
                while True:
                    filename = input(f"Output filename [{fingerprint['service_name']}.yml]: ")
                    if filename is None or filename == '':
                        filename = f"{fingerprint['service_name']}.yml"
                    try:
                        with open(filename, 'w') as f:
                            yaml.dump(output, f, sort_keys=False)
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
                        for fingerprint_dict in fingerprints:
                            f.write("---\n")
                            fingerprint = fingerprint_dict['print']
                            output = get_fingerprint_output(fingerprint)
                            yaml.dump(output, f, sort_keys=False)
                    break
                except IOError:
                    print("Error: unable to open file")
