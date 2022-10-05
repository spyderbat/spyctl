#!/usr/bin/env python3

import yaml
from simple_term_menu import TerminalMenu

from api import *
from fingerprints import preview_selection
from manage_menu import ManagementMenu

# Tool Features
MANAGE = "[1] Manage Fingerprints"
POLICIES = "[2] Upload Policies"
EXIT = "[e] Exit"

main_options = [
    MANAGE,
    POLICIES,
    EXIT
]
main_menu = TerminalMenu(
    main_options,
    title="Main Menu\n\nSelect an option:",
    clear_screen=True
)

manage_menu = ManagementMenu()

not_implemented_menu = TerminalMenu(
    ['[1] Back'],
    title="Feature coming soon..."
)


def main():
    while True:
        menu_entry_index = TerminalMenu(
            main_options,
            title="Main Menu\n\nSelect an option:",
            clear_screen=True
        ).show()
        if menu_entry_index is None:
            exit(0)
        option = main_options[menu_entry_index]
        if option == MANAGE:
            handle_manage()
        elif option == POLICIES:
            handle_policies()
        else:
            exit(0)


def handle_manage():
    manage_menu.show()


def handle_policies():
    not_implemented_menu.show()


if __name__ == "__main__":
    main()
