#!/usr/bin/env python3

import argparse
import gzip
import json
import os
import subprocess
import sys
import time
from base64 import urlsafe_b64encode as b64url
from typing import Dict, List, Tuple
from uuid import uuid4

import requests
import yaml
import zulu
from simple_term_menu import TerminalMenu

# Tool Features
DOWNLOAD_LSVC_PROF = "[1] Download Linux Service profile(s)"
DOWNLOAD_CONT_PROF = "[2] Download Container profile(s)"
UPLOAD_PROF = "[3] Upload a profile"
EXIT_PROGRAM = "[e] Exit"
BACK = "Back |"

SELECTED_ORG = None
SELECTED_MACHINES = []
SELECTED_MUIDS = []

DEPLOYMENTS = {
    'integration': {
       "ORG_UID": os.environ.get("I_ORG_UID"),
       "API_KEY": os.environ.get("I_API_KEY"),
       "API_URL": "https://api.kangaroobat.net",
    },
    'prod': {
       "ORG_UID": os.environ.get("P_ORG_UID"),
       "API_KEY": os.environ.get("P_API_KEY"),
       "API_URL": "https://api.prod.spyderbat.com",
    },
    'staging': {
       "ORG_UID": os.environ.get("S_ORG_UID"),
       "API_KEY": os.environ.get("S_API_KEY"),
       "API_URL": "https://api.staging.tigerbat.com",
    }
}

# In minutes
TIME_WINDOWS = ["90", "10", "30", "45", "60", "120", "Other"]

main_options = [
        DOWNLOAD_LSVC_PROF,
        DOWNLOAD_CONT_PROF,
        UPLOAD_PROF,
        EXIT_PROGRAM
    ]
main_menu = TerminalMenu(
    main_options,
    title="Main Menu\n\nSelect an option:",
    clear_screen=True)
deployments_menu = TerminalMenu(
    menu_entries=DEPLOYMENTS.keys(),
    title="Select a deployment:")
not_implemented_menu = TerminalMenu(
    ['[1] Back'], title="Feature coming soon...")


def main():
    while True:
        menu_entry_index = main_menu.show()
        if menu_entry_index is None:
            exit(0)
        option = main_options[menu_entry_index]
        if option == DOWNLOAD_LSVC_PROF:
            handle_download_lsvc()
        elif option == DOWNLOAD_CONT_PROF:
            handle_download_cont()
        elif option == UPLOAD_PROF:
            handle_upload()
        else:
            exit(0)


def handle_download_lsvc():
    api_info = get_deployment()
    if api_info is None:
        return
    else:
        api_key, api_url = api_info
    show_download_menu(api_key, api_url)


def prepare_profiles(profiles):
    # Get the latest version of each ID
    latest = {}
    for prof in profiles:
        latest[prof['id']] = prof
    # Unique the profiles based on checksum
    checksums = {}
    for prof in latest.values():
        checksum = prof['checksum']
        prof_yaml = yaml.dump(dict(spec=prof['spec']), sort_keys=False)
        if checksum not in checksums:
            checksums[checksum] = {
                'prof': prof,
                'suppressed': 0,
                'str_val':
                    f"{prof['service_name']} --" +
                    f" proc_nodes: {prof['proc_prof_len']}," +
                    f" ingress_nodes: {prof['ingress_len']}," +
                    f" egress_nodes: {prof['egress_len']} |" +
                    f" {prof_yaml}"
            }
        else:
            checksums[checksum]['suppressed'] += 1
            checksums[checksum]['str_val'] = \
                f"{prof['service_name']} " + \
                f" ({checksums[checksum]['suppressed']} suppressed) --" + \
                f" proc_nodes: {prof['proc_prof_len']}," + \
                f" ingress_nodes: {prof['ingress_len']}," + \
                f" egress_nodes: {prof['egress_len']} |" + \
                f" {prof_yaml}"
    rv = list(checksums.values())
    rv.sort(key=lambda d: d['str_val'])
    return list(rv)


def handle_download_cont():
    not_implemented_menu.show()


def handle_upload():
    not_implemented_menu.show()


def handle_error(error_code, msg=None):
    title = f"{error_code} Error while fetching data"
    if msg is not None:
        title += ". " + msg
    error_menu = TerminalMenu(
        ["[1] Back"], title=title)
    error_menu.show()


def handle_invalid(error_msg):
    error_menu = TerminalMenu(
        ["[1] Back"], title=error_msg)
    error_menu.show()


def show_download_menu(api_key, api_url):
    global SELECTED_ORG
    global SELECTED_MACHINES
    global SELECTED_MUIDS
    loaded_profiles = []
    selected_profiles = []
    while True:
        set_org = "[1] Set organization"
        if SELECTED_ORG is not None:
            set_org += f" -- current: {SELECTED_ORG} |"
        else:
            set_org += " |"
        set_machs = "[2] Set machine(s)"
        if len(SELECTED_MACHINES) == 1 and len(SELECTED_MUIDS) == 1:
            set_machs += f" -- current: {SELECTED_MACHINES[0]}" + \
                f" - {SELECTED_MUIDS[0]} |"
        elif len(SELECTED_MACHINES) > 1:
            muid_strs = [
                f"{mach} -- {muid}" for mach, muid in
                zip(SELECTED_MACHINES, SELECTED_MUIDS)]
            yaml_dict = yaml.dump(
                {'Selected machines': muid_strs[1:]})
            set_machs += f" -- current: {SELECTED_MACHINES[0]} -" + \
                f" {SELECTED_MUIDS[0]}, ... | " + \
                f'{yaml_dict}'
        else:
            set_machs += " |"
        load_profiles = "[3] Load profiles"
        if len(loaded_profiles) == 1:
            prof_strs = [
                my_list[0] for my_list in [
                    d['str_val'].split(' | ') for d in loaded_profiles]]
            load_profiles += f' -- current: {prof_strs[0]} |'
        elif len(loaded_profiles) > 1:
            prof_strs = [
                my_list[0] for my_list in [
                    d['str_val'].split(' | ') for d in loaded_profiles]]
            yaml_dict = yaml.dump({'Loaded Profiles': prof_strs[1:]})
            load_profiles += f' -- current: {prof_strs[0]}, ... | {yaml_dict}'
        else:
            load_profiles += " |"
        select_profiles = "[4] Select profiles"
        if len(selected_profiles) == 1:
            prof_strs = [
                my_list[0] for my_list in [
                    d['str_val'].split(' | ') for d in selected_profiles]]
            select_profiles += f' -- current: {prof_strs[0]} |'
        elif len(selected_profiles) > 1:
            prof_strs = [
                my_list[0] for my_list in [
                    d['str_val'].split(' | ') for d in selected_profiles]]
            yaml_dict = yaml.dump({'Selected Profiles': prof_strs[1:]})
            select_profiles += f' -- current: {prof_strs[0]}, ... | {yaml_dict}'
        else:
            select_profiles += " |"
        options = [
            set_org,
            set_machs,
            load_profiles,
            select_profiles,
            "[5] Diff profiles |",
            "[6] Save profiles |",
            "[7]" + BACK
        ]
        download_menu = TerminalMenu(
            options,
            title="Linux Service Profile Download Menu:\n" +
                  "Select an option:",
            preview_size=0.5,
            clear_screen=True,
            preview_command="echo '{}'",)
        index = download_menu.show()
        if index is None or options[index].endswith(BACK):
            return
        elif index == 0:
            # Set org
            org_info = get_orgs(api_url, api_key)
            if org_info is None:
                return
            org_uids, org_names = org_info
            index = show_org_menu(org_names)
            if index is None:
                return
            if SELECTED_ORG != org_uids[index]:
                SELECTED_ORG = org_uids[index]
                SELECTED_MUIDS = []
                SELECTED_MACHINES = []
        elif index == 1:
            # Set machines
            if SELECTED_ORG is None:
                handle_invalid("No organization selected")
                continue
            muid_info = get_muids(api_url, api_key, SELECTED_ORG)
            if muid_info is None:
                continue
            muids, hostnames = muid_info
            mach_options = ["[1] Specific machine(s)", "[2] All machines"]
            mach_q_menu = TerminalMenu(
                mach_options,
                title="Where would you like to download profiles from?")
            index = mach_q_menu.show()
            if index is None:
                continue
            if index == 0:
                muid_selection_info = show_machine_menu(muids, hostnames)
                if muid_selection_info is None:
                    continue
                SELECTED_MUIDS, SELECTED_MACHINES = muid_selection_info
            else:
                SELECTED_MUIDS, SELECTED_MACHINES = muid_info
        elif index == 2:
            # Load profiles
            if SELECTED_ORG is None:
                handle_invalid("No organization selected")
                continue
            elif len(SELECTED_MUIDS) == 0 or len(SELECTED_MACHINES) == 0:
                handle_invalid("No machine(s) selected")
                continue
            time_info = select_time_window()
            if time_info is None:
                continue
            start_time, end_time = time_info
            loaded_profiles = []
            for muid in SELECTED_MUIDS:
                tmp_profs = get_service_profiles(
                    api_url, api_key, SELECTED_ORG, muid, start_time, end_time)
                if tmp_profs is not None:
                    loaded_profiles += tmp_profs
                else:
                    break
            loaded_profiles = prepare_profiles(loaded_profiles)
            if len(loaded_profiles) == 0:
                handle_invalid("No profiles found")
                continue
        elif index == 3:
            # Select profiles for saving
            if len(loaded_profiles) == 0:
                handle_invalid("No profiles loaded")
                continue
            tmp_selected = show_service_profiles_menu(loaded_profiles)
            if tmp_selected is None:
                continue
            selected_profiles = tmp_selected
        elif index == 4:
            if len(selected_profiles) < 2:
                handle_invalid("Not enough profiles selected to diff")
            elif len(selected_profiles) == 2:
                show_profile_diff(selected_profiles)
            else:
                disclaimer_menu = TerminalMenu(
                    [
                        "[1] OK",
                        "[2] Back"
                    ],
                    title="Only the first two selected profiles will be diff'ed"
                )
                index = disclaimer_menu.show()
                if index is None or index == 1:
                    continue
                show_profile_diff(selected_profiles)
        elif index == 5:
            if len(selected_profiles) == 0:
                handle_invalid("No profiles selected")
            save_service_profile_yaml(selected_profiles)


def show_service_profiles_menu(profiles):
    prof_strs = [d['str_val'] for d in profiles]
    profiles_menu = TerminalMenu(
        prof_strs,
        title="Select profile(s):",
        preview_command="echo '{}'",
        preview_size=0.5,
        multi_select=True,
        multi_select_select_on_accept=False)
    index_tup = profiles_menu.show()
    if index_tup is None:
        return None
    rv = []
    for index in index_tup:
        rv.append(profiles[index])
    return rv


def show_profile_diff(profiles):
    fn1 = "/tmp/prof_diff1"
    fn2 = "/tmp/prof_diff2"
    try:
        with open(fn1, 'w') as f:
            profile = profiles[0]['prof']
            output = get_profile_output(profile)
            yaml.dump(output, f, sort_keys=False,)
        with open(fn2, "w") as f:
            profile = profiles[1]['prof']
            output = get_profile_output(profile)
            yaml.dump(output, f, sort_keys=False,)
        diff_proc = subprocess.Popen(
            ['sdiff', fn1, fn2],
            stdout=subprocess.PIPE)
        less_proc = subprocess.Popen(
            ['less', '-F', '-R', '-S', '-X', '-K'],
            stdin=diff_proc.stdout, stdout=sys.stdout)
        less_proc.wait()
    except IOError:
        handle_invalid("Error saving tmp files")


def get_profile_output(profile_rec: Dict):
    rv = {
            "spec": profile_rec['spec'],
            "metadata": {
                "service_name": profile_rec['service_name'],
                "checksum": profile_rec['checksum'],
                "muid": profile_rec['muid']
            }
        }
    root_puid = profile_rec.get('root_puid')
    if root_puid is not None:
        rv['metadata']['root_puid'] = root_puid
    return rv


def show_org_menu(org_names) -> int:
    if len(org_names) == 1:
        return 0
    org_menu = TerminalMenu(org_names, title="Select an org:")
    index = org_menu.show()
    return index


def show_machine_menu(muids, hostnames):
    sorted_muids = [x for _, x in sorted(zip(hostnames, muids))]
    sorted_hostnames = sorted(hostnames)
    machine_options = [
        f"{hostname} -- {muid}"
        for muid, hostname in zip(sorted_muids, sorted_hostnames)]
    mach_menu = TerminalMenu(
        machine_options,
        title="Select a machine (vim-style searching with /):",
        multi_select=True,
        multi_select_select_on_accept=False,
        show_multi_select_hint=True)
    index_tup = mach_menu.show()
    if index_tup is None or len(index_tup) == 0:
        return None
    rv_hostnames = []
    rv_muids = []
    for index in index_tup:
        rv_hostnames.append(sorted_hostnames[index])
        rv_muids.append(sorted_muids[index])
    return rv_muids, rv_hostnames


def save_service_profile_yaml(profiles):
    save_type_menu = TerminalMenu(
        [
            "[1] Save individual file(s) (for editing & uploading)",
            "[2] Save in one file (for viewing)",
            "[3]" + BACK
        ],
        title="Select an option:"
    )
    index = save_type_menu.show()
    if index is None or index == 2:
        return
    if index == 0:
        options = ['[y] yes', '[n] no']
        for profile_dict in profiles:
            profile = profile_dict['prof']
            save_service_menu = TerminalMenu(
                options, title=f"Save profile for {profile['service_name']}?")
            index = save_service_menu.show()
            if index == 0:
                output = get_profile_output(profile)
                while True:
                    filename = input(
                        f"Output filename [{profile['service_name']}.yml]: ")
                    if filename is None or filename == '':
                        filename = f"{profile['service_name']}.yml"
                    try:
                        with open(filename, 'w') as f:
                            yaml.dump(output, f, sort_keys=False)
                        break
                    except IOError:
                        print("Error: unable to open file")
    elif index == 1:
        options = ['[y] yes', '[n] no']
        save_service_menu = TerminalMenu(
            options, title=f"Save all selected profiles in one file?")
        if index is None:
            return
        elif index == 1:
            while True:
                default = "multi-service-profiles.yml"
                filename = input(
                    f"Output filename {default}]: ")
                if filename is None or filename == '':
                    filename = default
                try:
                    with open(filename, 'w') as f:
                        for profile_dict in profiles:
                            f.write("---\n")
                            profile = profile_dict['prof']
                            output = get_profile_output(profile)
                            yaml.dump(output, f, sort_keys=False)
                    break
                except IOError:
                    print("Error: unable to open file")


def get_service_profiles(
        api_url, api_key, org_uid, muid, start_time, end_time):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"}
    url = f"{api_url}/api/v1/org/{org_uid}/data/?src={muid}&"\
        f"st={int(start_time)}&et={int(end_time)}&dt=profiles"
    resp_str = ""
    resp = requests.get(url, headers=headers, stream=True)
    if resp.status_code == 200:
        for block in resp.iter_content(chunk_size=65536):
            block = block.decode('ascii')
            resp_str += str(block)
        # import pdb; pdb.set_trace() #noqa: E702
        if resp_str:
            profiles = []
            profiles_json = resp_str.split("\n")
            for p_json in profiles_json:
                profile = json.loads(p_json)
                profiles.append(profile)
            return profiles
        else:
            return []
    else:
        handle_error(resp.status_code, f"Unable to get profiles from {muid}")
        return None


def get_deployment():
    deployments = list(DEPLOYMENTS.keys())
    if len(deployments) == 1:
        return (DEPLOYMENTS[deployments[0]]['API_KEY'],
                DEPLOYMENTS[deployments[0]]['API_URL'])
    else:
        index = deployments_menu.show()
        if index is None:
            return None
        deployment = deployments[index]
        return (DEPLOYMENTS[deployment]['API_KEY'],
                DEPLOYMENTS[deployment]['API_URL'])


def get_orgs(api_url, api_key) -> List[Tuple]:
    org_uids = []
    org_names = []
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"}
    url = f"{api_url}/api/v1/org/"
    resp_str = ""
    resp = requests.get(url, headers=headers, stream=True)
    if resp.status_code == 200:
        for block in resp.iter_content(chunk_size=65536):
            block = block.decode('ascii')
            resp_str += str(block)
        orgs_json = json.loads(resp_str)
        for org in orgs_json:
            org_uids.append(org['uid'])
            org_names.append(org['name'])
    else:
        handle_error(resp.status_code)
        return None
    return (org_uids, org_names)


def get_muids(api_url, api_key, org_uid) -> List:
    sources = {}
    muids = []
    hostnames = []
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"}
    url = f"{api_url}/api/v1/org/{org_uid}/source/"
    resp_str = ""
    resp = requests.get(url, headers=headers, stream=True)
    if resp.status_code == 200:
        for block in resp.iter_content(chunk_size=65536):
            block = block.decode('ascii')
            resp_str += str(block)
        source_json = json.loads(resp_str)
        for source in source_json:
            if not source['uid'].startswith("global"):
                muid = source['uid']
                last_data = zulu.parse(source['last_data'])
                sources[muid] = {
                    'muid': muid,
                    'name': source['name'],
                    'last_data': last_data
                }
    else:
        handle_error(resp.status_code)
        return None
    url2 = f"{api_url}/api/v1/org/{org_uid}/agent/"
    resp_str = ""
    resp = requests.get(url2, headers=headers, stream=True)
    if resp.status_code == 200:
        for block in resp.iter_content(chunk_size=65536):
            block = block.decode('ascii')
            resp_str += str(block)
        source_json = json.loads(resp_str)
        for source in source_json:
            if not source['uid'].startswith("global"):
                muid = source['runtime_details']['src_uid']
                hostname = source['description']
                if muid in sources:
                    if sources[muid]['name'] == "":
                        sources[muid]['name'] = hostname
    else:
        handle_error(resp.status_code)
        return None
    two_days_ago = zulu.now().shift(days=-2)
    for muid, data in list(sources.items()):
        if data['last_data'] < two_days_ago:
            del sources[muid]
        else:
            muids.append(muid)
            hostnames.append(data['name'])
    return muids, hostnames


def select_time_window():
    now = time.time()
    start_time_menu = TerminalMenu(
        TIME_WINDOWS,
        title="Select start time in minutes back from now:")
    index = start_time_menu.show()
    if index is None:
        return None
    selection = TIME_WINDOWS[index]
    if selection == "other":
        try:
            start_time = int(input("Start Time: "))
            end_time = int(input("End time: "))
        except Exception:
            handle_invalid("Invalid input")
            return None
    else:
        start_time = now - (60 * int(selection))
        end_time = now
    return start_time, end_time


if __name__ == "__main__":
    main()
