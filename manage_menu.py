from simple_term_menu import TerminalMenu

from fingerprints import *
from merge import merge_fingerprints
from diff import show_fingerprint_diff

class ManagementMenu():
    def __init__(self) -> None:
        self.selected_fingerprints = []
    
    def set_fingerprints(self, fingerprints):
        self.selected_fingerprints = fingerprints
    
    def handle_invalid(self, error_msg):
        TerminalMenu(
            ["[1] Back"], title=error_msg
        ).show()
    
    def show(self):
        if len(self.selected_fingerprints) == 0:
            self.handle_invalid("No fingerprents selected to manage")
            return
        while True:
            main_options = [
                "[1] Compare Fingerprints",
                "[2] Merge Fingerprints",
                "[3] Save Fingerpints",
                "[4] Template Policy From Fingerprints",
                "[5] Done"
            ]
            index = TerminalMenu(
                main_options,
                title="Fingerprint Management Menu\n\n" + \
                    "Select an option:",
                clear_screen=True,
                status_bar=preview_selection(self.selected_fingerprints),
                status_bar_style=None
            ).show()
            if index == 0:
                self.compare_fingerprints()
            elif index == 1:
                self.merge_fingerprints()
            elif index == 2:
                self.save_fingerprints()
            elif index == 3:
                self.template_policy()
            else:
                break
    
    def compare_fingerprints(self):
        if len(self.selected_fingerprints) < 2:
            self.handle_invalid("Not enough fingerprints selected to compare")
            return
        try:
            out_prints = [f.get_output() for f in self.selected_fingerprints]
            show_fingerprint_diff(out_prints)
        except IOError:
            self.handle_invalid("Error saving temporary file")
    
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
    
    def template_policy(self):
        self.handle_invalid("Feature coming soon...")
