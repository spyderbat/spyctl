#!/usr/bin/env python3

import yaml
from simple_term_menu import TerminalMenu

from api import *
from download_menu import DownloadMenu

# Tool Features
DOWNLOAD_LSVC_PROF = "[1] Download Linux Service profile(s)"
DOWNLOAD_CONT_PROF = "[2] Download Container profile(s)"
UPLOAD_PROF = "[3] Upload a profile"
EXIT_PROGRAM = "[e] Exit"

main_options = [
    DOWNLOAD_LSVC_PROF,
    DOWNLOAD_CONT_PROF,
    UPLOAD_PROF,
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
        else:
            exit(0)


def handle_download_lsvc():
    download_menu.show()


def handle_download_cont():
    not_implemented_menu.show()


def handle_upload():
    not_implemented_menu.show()


if __name__ == "__main__":
    main()
