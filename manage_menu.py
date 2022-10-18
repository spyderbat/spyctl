from simple_term_menu import TerminalMenu

from fingerprints import *
from merge import merge_fingerprints
from diff import save_fingerprint_diff
from download_menu import DownloadMenu

class ManagementMenu():
    def __init__(self) -> None:
        self.download_menu = DownloadMenu()
    
    def handle_invalid(self, error_msg):
        TerminalMenu(
            ["[1] Back"], title=error_msg
        ).show()
    
    def show(self):
        while True:
            main_options = [
                "[1] Download Service Fingerprints",
                "[2] Download Container Fingerprints",
                "[3] Load Local Fingerprints",
                "[4] Deselect Fingerprints",
                "[5] Compare Fingerprints",
                "[6] Merge Fingerprints",
                "[7] Save Fingerpints",
                "[8] Template Policy From Fingerprints",
                "[9] Done"
            ]
            index = TerminalMenu(
                main_options,
                title="Fingerprint Management Menu\n\n" + \
                    "Select an option:",
                clear_screen=True,
                status_bar=preview_selection(self.fingerprints),
                status_bar_style=None
            ).show()
            if index == 0:
                self.download_menu.show("Service")
            elif index == 1:
                self.download_menu.show("Container")
            elif index == 2:
                self.download_menu.select_local()
            elif index == 3:
                self.download_menu.deselect_fingerprints()
            elif index == 4:
                self.compare_fingerprints()
            elif index == 5:
                self.merge_fingerprints()
            elif index == 6:
                self.save_fingerprints()
            elif index == 7:
                self.template_policy()
            else:
                break
    
    @property
    def fingerprints(self):
        return self.download_menu.selected_fingerprints
    
    @fingerprints.setter
    def fingerprints(self, val):
        self.download_menu.selected_fingerprints = val
    
    def compare_fingerprints(self):
        if len(self.fingerprints) < 2:
            self.handle_invalid("Not enough fingerprints selected to compare")
            return
        try:
            out_prints = [f.get_output() for f in self.fingerprints]
            save_fingerprint_diff(out_prints)
        except IOError:
            self.handle_invalid("Error saving temporary file")
    
    def merge_fingerprints(self):
        if len(self.fingerprints) == 0:
            self.handle_invalid("No fingerprints selected to merge")
            return
        out_prints = [f.get_output() for f in self.fingerprints]
        try:
            merged = merge_fingerprints(out_prints)
            if len(merged) == 0:
                return
            save_merged_fingerprint_yaml(merged)
        except ValueError as err:
            self.handle_invalid(*err.args)

    def save_fingerprints(self):
        if len(self.fingerprints) == 0:
            self.handle_invalid("No fingerprints selected to save")
            return
        save_fingerprint_yaml(self.fingerprints)
    
    def template_policy(self):
        self.handle_invalid("Feature coming soon...")
