#!/usr/bin/env python3

import yaml
from simple_term_menu import TerminalMenu

from api import *
from download_menu import DownloadMenu
from fingerprints import preview_selection
from manage_menu import ManagementMenu

# Tool Features
CHOOSE = "[1] Select Fingerprints"
MANAGE = "[2] Manage Fingerprints"
UPLOAD = "[3] Upload Policies"
EXIT = "[e] Exit"

main_options = [
    CHOOSE,
    MANAGE,
    UPLOAD,
    EXIT
]
main_menu = TerminalMenu(
    main_options,
    title="Main Menu\n\nSelect an option:",
    clear_screen=True
)

download_menu = DownloadMenu()
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
            clear_screen=True,
            status_bar=preview_selection(download_menu.selected_fingerprints),
            status_bar_style=None
        ).show()
        if menu_entry_index is None:
            exit(0)
        option = main_options[menu_entry_index]
        if option == CHOOSE:
            handle_choose()
        elif option == MANAGE:
            handle_manage()
        elif option == UPLOAD:
            handle_upload()
        else:
            exit(0)


def handle_choose():
    download_menu.show()


def handle_manage():
    manage_menu.set_fingerprints(download_menu.selected_fingerprints)
    manage_menu.show()


def handle_upload():
    not_implemented_menu.show()


def handle_local_load():
    files = input("Enter file paths, separated by commas: ").split(',')
    if len(files) == 0:
        return
    files = [file.strip() for file in files]
    fprints = []
    for file in files:
        try:
            with open(file, "r") as f:
                fprints.append(yaml.load(f, yaml.Loader))
        except OSError:
            print("Failed to read file", file)
    download_menu.set_local(fprints)
    download_menu.show()


if __name__ == "__main__":
    main()
