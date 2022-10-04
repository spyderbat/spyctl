import os
import yaml
import time
from simple_term_menu import TerminalMenu

from api import *
from fingerprints import *
from merge import merge_fingerprints
from diff import show_fingerprint_diff

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


def add_current(string, current=None, title="", fmt=lambda s: s) -> str:
    if current is None:
        return string + "|"
    if isinstance(current, list):
        if len(current) == 1:
            return string + f" - current: {fmt(current[0])}|"
        elif len(current) > 1:
            strs = [fmt(elem) for elem in current]
            return string + f" - current: {fmt(current[0])} ...|" + \
                yaml.dump({f'{title}': strs}, width=float("inf"))
        else:
            return string + "|"
    else:
        return string + f" - current: {fmt(current)}|"


class DownloadMenu():
    def __init__(self) -> None:
        self.api_key = None
        self.api_url = None

        self.selected_org = None
        self.selected_machines = []
        self.selected_muids = []

        self.loaded_fingerprints = []
        self.selected_fingerprints = []
        
        self.deployments_menu = TerminalMenu(
            menu_entries=DEPLOYMENTS.keys(),
            title="Select a deployment:"
        )

        self.local = False

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

    def set_local(self, local_fingerprints):
        self.selected_fingerprints = Fingerprint.prepare_many([
            Fingerprint(fprint) for fprint in local_fingerprints
        ])
        self.local = len(local_fingerprints) > 0

    def show(self):
        if not self.local:
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
                fmt=lambda pair: f"{pair[0]} -- {pair[1]}"
            )
            load_fingerprints = add_current(
                "[3] Load fingerprints",
                current=self.loaded_fingerprints,
                title="Loaded Fingerprints",
                fmt=lambda fprint: fprint.preview_str().split(' | ')[0]
            )
            select_fingerprints = add_current(
                "[4] Select fingerprints",
                current=self.selected_fingerprints,
                title="Selected Fingerprints",
                fmt=lambda fprint: fprint.preview_str().split(' | ')[0]
            )
            options = [
                set_org,
                set_machs,
                load_fingerprints,
                select_fingerprints,
                "[5] Compare fingerprints|",
                "[6] Merge fingerprints|",
                "[7] Save fingerprints|",
                "[8] Back|"
            ] if not self.local else [
                "[1] Compare fingerprints|",
                "[2] Merge fingerprints|",
                "[3] Back|"
            ]
            title = "Download" if not self.local else "Management"
            download_menu = TerminalMenu(
                options,
                title=f"Fingerprint {title} Menu\n\n" +
                    "Select an option:",
                preview_size=0.5,
                clear_screen=True,
                preview_command="echo '{}'",
                preview_title=""
            )
            index = download_menu.show()
            option = options[index] if index is not None else None
            if index is None or "Back" in option:
                break
            elif option == set_org:
                self.select_org()
            elif option == set_machs:
                self.select_machine()
            elif option == load_fingerprints:
                self.load_fingerprints()
            elif option == select_fingerprints:
                self.select_fingerprints()
            elif "Compare fingerprints" in option:
                self.diff_fingerprints()
            elif "Merge fingerprints" in option:
                self.merge_fingerprints()
            elif "Save fingerprints" in option:
                self.save_fingerprints()
    
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
            title="Where would you like to download fingerprints from?"
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
    
    def load_fingerprints(self):
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
        raw_fingerprints = []
        for muid in self.selected_muids:
            tmp_fprints = get_service_fingerprints(
                self.api_url, self.api_key, self.selected_org,
                muid, start_time, end_time, self.handle_error
            )
            if tmp_fprints is not None:
                raw_fingerprints += [Fingerprint(f) for f in tmp_fprints]
            else:
                break
        self.loaded_fingerprints = Fingerprint.prepare_many(raw_fingerprints)
    
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
    
    def select_fingerprints(self):
        if len(self.loaded_fingerprints) == 0:
            self.handle_invalid("No fingerprints loaded")
            return
        fprint_strs = [f.preview_str() for f in self.loaded_fingerprints]
        index_tup = TerminalMenu(
            fprint_strs,
            title="Select fingerprint(s):",
            preview_command="echo '{}'",
            preview_size=0.5,
            multi_select=True,
            multi_select_select_on_accept=False
        ).show()
        if index_tup is None or len(index_tup) == 0:
            return
        self.selected_fingerprints = []
        for index in index_tup:
            self.selected_fingerprints.append(self.loaded_fingerprints[index])
    
    def diff_fingerprints(self):
        if len(self.selected_fingerprints) < 2:
            self.handle_invalid("Not enough fingerprints selected to compare")
            return
        try:
            out_prints = [f.get_output() for f in self.selected_fingerprints]
            show_fingerprint_diff(out_prints)
        except IOError:
            self.handle_invalid("Error saving tmp file")
    
    def merge_fingerprints(self):
        if len(self.selected_fingerprints) == 0:
            self.handle_invalid("No fingerprints selected to merge")
            return
        out_prints = [f.get_output() for f in self.selected_fingerprints]
        save_merged_fingerprint_yaml(merge_fingerprints(out_prints))

    def save_fingerprints(self):
        if len(self.selected_fingerprints) == 0:
            self.handle_invalid("No fingerprints selected to save")
            return
        save_service_fingerprint_yaml(self.selected_fingerprints)
