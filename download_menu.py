import os
import yaml
import time
import sys
import subprocess
from simple_term_menu import TerminalMenu

from api import *

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
TIME_WINDOWS = ["90", "10", "30", "45", "60", "120", "Other"]


def add_current(string, current=None, title="", fmt=lambda s: s):
    if current is None:
        return string + "|"
    if isinstance(current, list):
        if len(current) == 1:
            return string + f" -- current: {fmt(current[0])}|"
        elif len(current) > 1:
            strs = [fmt(elem) for elem in current]
            return string + f" -- current: {fmt(current[0])} ...|" + \
                yaml.dump({f'{title}': strs}, width=float("inf"))
        else:
            return string + "|"
    else:
        return string + f" -- current: {fmt(current)}|"


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
                f"{prof['service_name']}" + \
                f" ({checksums[checksum]['suppressed']} suppressed) --" + \
                f" proc_nodes: {prof['proc_prof_len']}," + \
                f" ingress_nodes: {prof['ingress_len']}," + \
                f" egress_nodes: {prof['egress_len']} |" + \
                f" {prof_yaml}"
    rv = list(checksums.values())
    rv.sort(key=lambda d: d['str_val'])
    return list(rv)


def get_profile_output(profile_rec):
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


def show_profile_diff(profiles):
    fn1 = "/tmp/prof_diff1"
    fn2 = "/tmp/prof_diff2"
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


def dialog(title):
    index = TerminalMenu(
        ['[y] yes', '[n] no'],
        title=title
    ).show()
    return index == 0


def save_service_profile_yaml(profiles):
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
        for profile_dict in profiles:
            profile = profile_dict['prof']
            if dialog(f"Save profile for {profile['service_name']}?"):
                output = get_profile_output(profile)
                while True:
                    filename = input(f"Output filename [{profile['service_name']}.yml]: ")
                    if filename is None or filename == '':
                        filename = f"{profile['service_name']}.yml"
                    try:
                        with open(filename, 'w') as f:
                            yaml.dump(output, f, sort_keys=False)
                        break
                    except IOError:
                        print("Error: unable to open file")
    elif index == 1:
        if dialog("Save all selected profiles in one file?"):
            while True:
                default = "multi-service-profiles.yml"
                filename = input(f"Output filename [{default}]: ")
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


class DownloadMenu():
    api_key = None
    api_url = None

    selected_org = None
    selected_machines = []
    selected_muids = []

    loaded_profiles = []
    selected_profiles = []
    
    deployments_menu = TerminalMenu(
        menu_entries=DEPLOYMENTS.keys(),
        title="Select a deployment:"
    )

    def get_api_info(self):
        deployments = list(DEPLOYMENTS.keys())
        if len(deployments) == 1:
            self.api_key = DEPLOYMENTS[deployments[0]]['API_KEY']
            self.api_url = DEPLOYMENTS[deployments[0]]['API_URL']
        else:
            index = self.deployments_menu.show()
            if index is not None:
                deployment = deployments[index]
                self.api_key = DEPLOYMENTS[deployment]['API_KEY']
                self.api_url = DEPLOYMENTS[deployment]['API_URL']
            else:
                raise ValueError("No deployment set")
    
    def handle_error(self, error_code, reason, msg=None):
        title = f"{error_code} ({reason}) Error while fetching data"
        if msg is not None:
            title += ". " + msg
        TerminalMenu(
            ["[1] Back"], title=title
        ).show()

    def handle_invalid(self, error_msg):
        TerminalMenu(
            ["[1] Back"], title=error_msg
        ).show()

    def show(self):
        try:
            self.get_api_info()
        except ValueError as err:
            self.handle_invalid(*err.args)
        while True:
            set_org = add_current(
                "[1] Set organization",
                current=self.selected_org
            )
            set_machs = add_current(
                "[2] Set machine(s)",
                current=list(zip(self.selected_machines, self.selected_muids)),
                title="Selected Machines",
                fmt=lambda pair: f"{pair[0]} - {pair[1]}"
            )
            load_profiles = add_current(
                "[3] Load profiles",
                current=self.loaded_profiles,
                title="Loaded Profiles",
                fmt=lambda prof: prof['str_val'].split(' | ')[0]
            )
            select_profiles = add_current(
                "[4] Select profiles",
                current=self.selected_profiles,
                title="Selected Profiles",
                fmt=lambda prof: prof['str_val'].split(' | ')[0]
            )
            options = [
                set_org,
                set_machs,
                load_profiles,
                select_profiles,
                "[5] Diff profiles|",
                "[6] Save profiles|",
                "[7] Back|"
            ]
            download_menu = TerminalMenu(
                options,
                title="Linux Service Profile Download Menu\n\n" +
                    "Select an option:",
                preview_size=0.5,
                clear_screen=True,
                preview_command="echo '{}'",
                preview_title=""
            )
            index = download_menu.show()
            if index is None or index == 6:
                break
            elif index == 0:
                self.select_org()
            elif index == 1:
                self.select_machine()
            elif index == 2:
                self.load_profiles()
            elif index == 3:
                self.select_profiles()
            elif index == 4:
                self.diff_profiles()
            elif index == 5:
                self.save_profiles()
    
    def select_org(self):
        org_info = get_orgs(self.api_url, self.api_key, self.handle_error)
        if org_info is None:
            return
        org_uids, org_names = org_info
        index = 0
        if len(org_names) > 1:
            org_menu = TerminalMenu(org_names, title="Select an org:")
            index = org_menu.show()
        if index is None:
            return
        if self.selected_org != org_uids[index]:
            self.selected_org = org_uids[index]
            self.selected_muids = []
            self.selected_machines = []
    
    def select_machine(self):
        if self.selected_org is None:
            self.handle_invalid("No organization selected")
            return
        muid_info = get_muids(self.api_url, self.api_key,
                              self.selected_org, self.handle_error)
        if muid_info is None:
            return
        muids, hostnames = muid_info
        mach_options = ["[1] Specific machine(s)", "[2] All machines"]
        index = TerminalMenu(
            mach_options,
            title="Where would you like to download profiles from?"
        ).show()
        if index is None:
            return
        if index == 0:
            muid_selection_info = self.select_machine_subset(muids, hostnames)
            if muid_selection_info is None:
                return
            self.selected_muids, self.selected_machines = muid_selection_info
        else:
            self.selected_muids, self.selected_machines = muid_info
    
    def select_machine_subset(self, muids, hostnames):
        sorted_muids = []
        sorted_hostnames = []
        for hostname, muid in sorted(zip(hostnames, muids)):
            sorted_muids.append(muid)
            sorted_hostnames.append(hostname)
        machine_options = [
            f"{hostname} -- {muid}"
            for muid, hostname in zip(sorted_muids, sorted_hostnames)
        ]
        index_tup = TerminalMenu(
            machine_options,
            title="Select a machine (vim-style searching with /):",
            multi_select=True,
            multi_select_select_on_accept=False,
            show_multi_select_hint=True
        ).show()
        if index_tup is None or len(index_tup) == 0:
            return None
        rv_hostnames = []
        rv_muids = []
        for index in index_tup:
            rv_hostnames.append(sorted_hostnames[index])
            rv_muids.append(sorted_muids[index])
        return rv_muids, rv_hostnames
    
    def load_profiles(self):
        if self.selected_org is None:
            self.handle_invalid("No organization selected")
            return
        elif len(self.selected_muids) == 0 or len(self.selected_machines) == 0:
            self.handle_invalid("No machine(s) selected")
            return
        time_info = self.select_time_window()
        if time_info is None:
            return
        start_time, end_time = time_info
        self.loaded_profiles = []
        for muid in self.selected_muids:
            tmp_profs = get_service_profiles(
                self.api_url, self.api_key, self.selected_org,
                muid, start_time, end_time, self.handle_error
            )
            if tmp_profs is not None:
                self.loaded_profiles += tmp_profs
            else:
                break
        self.loaded_profiles = prepare_profiles(self.loaded_profiles)
        if len(self.loaded_profiles) == 0:
            self.handle_invalid("No profiles found")
            return
    
    def select_time_window(self):
        now = time.time()
        index = TerminalMenu(
            TIME_WINDOWS,
            title="Select start time in minutes back from now:"
        ).show()
        if index is None:
            return None
        selection = TIME_WINDOWS[index]
        if selection == "other":
            try:
                start_time = int(input("Start Time: "))
                end_time = int(input("End time: "))
            except Exception:
                self.handle_invalid("Invalid input")
                return None
        else:
            start_time = now - (60 * int(selection))
            end_time = now
        return start_time, end_time
    
    def select_profiles(self):
        if len(self.loaded_profiles) == 0:
            self.handle_invalid("No profiles loaded")
            return
        prof_strs = [prof['str_val'] for prof in self.loaded_profiles]
        index_tup = TerminalMenu(
            prof_strs,
            title="Select profile(s):",
            preview_command="echo '{}'",
            preview_size=0.5,
            multi_select=True,
            multi_select_select_on_accept=False
        ).show()
        if index_tup is None or len(index_tup) == 0:
            return
        self.selected_profiles = []
        for index in index_tup:
            self.selected_profiles.append(self.loaded_profiles[index])
    
    def diff_profiles(self):
        if len(self.selected_profiles) < 2:
            self.handle_invalid("Not enough profiles selected to diff")
            return
        elif len(self.selected_profiles) > 2:
            disclaimer_menu = TerminalMenu(
                ["[1] OK", "[2] Back"],
                title="Only the first two selected profiles will be diff'ed"
            )
            index = disclaimer_menu.show()
            if index is None or index == 1:
                return
        try:
            show_profile_diff(self.selected_profiles)
        except IOError:
            self.handle_invalid("Error saving tmp fies")
    
    def save_profiles(self):
        if len(self.selected_profiles) == 0:
            self.handle_invalid("No profiles selected to save")
            return
        save_service_profile_yaml(self.selected_profiles)
