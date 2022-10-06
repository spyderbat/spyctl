#!/usr/bin/env python3

import argparse
from simple_term_menu import TerminalMenu

from api import *
from manage_menu import ManagementMenu

DESCRIPTION = "A tool to help manage Spyderbat fingerprints and policies"

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


def parse_args():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    run_action = parser.add_mutually_exclusive_group()
    run_action.add_argument('-m', '--merge', help="directly merge specified files")
    run_action.add_argument('-c', '--compare', help="directly compare specified files")
    parser.add_argument('-o', '--org_uid', help="organization UID to have selected")
    parser.add_argument('-a', '--api_info', help="API url, API key to use instead of environment variables")
    args = parser.parse_args()
    return args


def handle_args(args):
    if args.org_uid:
        manage_menu.download_menu.selected_org = args.org_uid
    if args.api_info:
        api_url, api_key = [s.strip() for s in args.api_info.split(',')]
        manage_menu.download_menu.api_url = api_url
        manage_menu.download_menu.api_key = api_key
    if files_str := args.merge or args.compare:
        files = [f.strip() for f in files_str.split(',')]
        if len(files) < 2:
            print("Not enough files")
            exit(1)
        for file in files:
            if not manage_menu.download_menu.load_file(file):
                print("Failed to load file", file)
                exit(1)
        manage_menu.fingerprints = manage_menu.download_menu.loaded_fingerprints
        if args.merge:
            manage_menu.merge_fingerprints()
        elif args.compare:
            manage_menu.compare_fingerprints()
        exit(0)


def main():
    args = parse_args()
    handle_args(args)
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
