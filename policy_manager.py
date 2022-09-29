#!/usr/bin/env python3

import yaml
from simple_term_menu import TerminalMenu

from api import *
from download_menu import DownloadMenu

# Tool Features
DOWNLOAD_LSVC_PROF = "[1] Download Linux Service fingerprint(s)"
DOWNLOAD_CONT_PROF = "[2] Download Container fingerprint(s)"
UPLOAD_PROF = "[3] Upload a policy"
LOCAL_MERGE = "[4] Merge local fingerprints"
EXIT_PROGRAM = "[e] Exit"

main_options = [
    DOWNLOAD_LSVC_PROF,
    DOWNLOAD_CONT_PROF,
    UPLOAD_PROF,
    LOCAL_MERGE,
    EXIT_PROGRAM
]
main_menu = TerminalMenu(
    main_options,
    title="Main Menu\n\nSelect an option:",
    clear_screen=True
)

download_menu = DownloadMenu()

not_implemented_menu = TerminalMenu(
    ['[1] Back'],
    title="Feature coming soon..."
)


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
        elif option == LOCAL_MERGE:
            handle_local_merge()
        else:
            exit(0)


def handle_download_lsvc():
    download_menu.show()


def handle_download_cont():
    not_implemented_menu.show()


def handle_upload():
    not_implemented_menu.show()


def handle_local_merge():
    from fingerprints import save_service_fingerprint_yaml
    from merge import merge_fingerprints
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
    merged_print = merge_fingerprints(fprints)
    save_service_fingerprint_yaml([merged_print])


if __name__ == "__main__":
    main()
