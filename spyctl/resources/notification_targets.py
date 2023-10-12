import re
import time
from copy import deepcopy
from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib.parse import urlparse
import yaml

import click
from simple_term_menu import TerminalMenu
from tabulate import tabulate

import spyctl.cli as cli
import spyctl.spyctl_lib as lib
import spyctl.api as api
import spyctl.config.configs as cfg

TARGETS_HEADERS = ["NAME", "AGE", "TYPE", "DESTINATIONS"]


@dataclass
class Emails:
    emails: list

    @property
    def sum_dest(self):
        if self.emails:
            return "\n".join(self.emails)
        else:
            return lib.NOT_AVAILABLE


@dataclass
class Slack:
    url: str = None

    @property
    def sum_dest(self):
        if self.url:
            return self.url
        else:
            return lib.NOT_AVAILABLE

    @property
    def dest(self):
        return {"url": self.url}


@dataclass
class SNS:
    cross_account_iam_role: str = None
    sns_topic_arn: str = None

    @property
    def sum_dest(self):
        if self.sns_topic_arn:
            return self.sns_topic_arn
        else:
            return lib.NOT_AVAILABLE

    @property
    def dest(self):
        rv = {}
        if self.cross_account_iam_role:
            rv.update({"cross_account_iam_role": self.cross_account_iam_role})
        if self.sns_topic_arn:
            rv.update({"sns_topic_arn": self.sns_topic_arn})
        return rv


@dataclass
class Users:
    users: list

    @property
    def sum_dest(self):
        if self.emails:
            return "\n".join(self.emails)
        else:
            return lib.NOT_AVAILABLE


@dataclass
class Webhook:
    url: str = None
    no_tls_validation: bool = None

    @property
    def sum_dest(self):
        if self.url:
            return self.url
        else:
            return lib.NOT_AVAILABLE

    @property
    def dest(self):
        rv = {"url": self.url}
        if self.no_tls_validation:
            rv.update({"no_tls_validation": self.no_tls_validation})
        return rv


def targets_summary_output(targets: Dict):
    row_data = []
    for tgt_name, tgt_data in targets.items():
        types = []
        dest_count = 0
        for tgt_type in lib.DST_TYPES:
            if tgt_type in tgt_data:
                dest_count += len(tgt_data[tgt_type])
                types.append(tgt_type)
        if lib.DATA_FIELD not in tgt_data:
            age = lib.NOT_AVAILABLE
        else:
            data = tgt_data[lib.DATA_FIELD]
            if lib.NOTIF_CREATE_TIME in data:
                age = lib.calc_age(data[lib.NOTIF_CREATE_TIME])
            else:
                age = lib.NOT_AVAILABLE
        if len(types) == 1:
            type = types[0]
        elif len(types) > 1:
            type = f"{len(types)} types"
        else:
            type = lib.NOT_AVAILABLE
        row_data.append([tgt_name, age, type, dest_count])
    return tabulate(row_data, TARGETS_HEADERS, "plain")


def targets_wide_output(targets: Dict):
    row_data = []
    for tgt_name, tgt_data in targets.items():
        types = []
        dests = {}
        for tgt_type in lib.DST_TYPES:
            if tgt_type in tgt_data:
                if tgt_type == lib.DST_TYPE_EMAIL:
                    dests[tgt_type] = Emails(tgt_data[tgt_type])
                elif tgt_type == lib.DST_TYPE_SLACK:
                    dests[tgt_type] = Slack(**tgt_data[tgt_type])
                elif tgt_type == lib.DST_TYPE_SNS:
                    dests[tgt_type] = SNS(**tgt_data[tgt_type])
                elif tgt_type == lib.DST_TYPE_USERS:
                    dests[tgt_type] = Users(tgt_data[tgt_type])
                elif tgt_type == lib.DST_TYPE_WEBHOOK:
                    dests[tgt_type] = Webhook(**tgt_data[tgt_type])
                else:
                    cli.err_exit("Unsupported tgt type.")
                types.append(tgt_type)
        if lib.DATA_FIELD not in tgt_data:
            age = lib.NOT_AVAILABLE
        else:
            data = tgt_data[lib.DATA_FIELD]
            if lib.NOTIF_CREATE_TIME in data:
                age = lib.calc_age(data[lib.NOTIF_CREATE_TIME])
            else:
                age = lib.NOT_AVAILABLE
        if types:
            for i, tgt_type in enumerate(types):
                if i == 0:
                    row_data.append(
                        [tgt_name, age, tgt_type, dests[tgt_type].sum_dest]
                    )
                else:
                    row_data.append(
                        ["", "", tgt_type, dests[tgt_type].sum_dest]
                    )
        else:
            row_data.append(
                [tgt_name, age, lib.NOT_AVAILABLE, lib.NOT_AVAILABLE]
            )
    return tabulate(row_data, TARGETS_HEADERS, "plain")


def interactive_targets(notif_policy: Dict, shortcut=None):
    notif_policy_copy = deepcopy(notif_policy)
    targets: Dict = notif_policy_copy[lib.TARGETS_FIELD]
    main_menu = __build_main_menu()
    update_policy = False
    delete_name = None
    while True:
        main_sel = None
        if not shortcut:
            main_sel = main_menu.show()
        if main_sel == 0 or shortcut == "create":
            new_tgt = __i_tgt_menu(targets)
            if new_tgt:
                new_name, new_data = list(new_tgt.items())[0]
                if cli.query_yes_no("Preview new target?"):
                    click.echo_via_pager(yaml.dump(new_tgt))
                if cli.query_yes_no(f"Add new target '{new_name}'?"):
                    targets[new_name] = new_data
                    update_policy = True
        elif main_sel == 1 or shortcut == "edit":
            tgt_name = __i_tgt_pick_menu(targets)
            if tgt_name:
                tgt_data = targets[tgt_name]
                updated_tgt = __i_tgt_menu(targets, tgt_name, tgt_data)
                if updated_tgt:
                    new_name, new_data = list(updated_tgt.items())[0]
                    if cli.query_yes_no("Preview change?"):
                        click.echo_via_pager(yaml.dump(updated_tgt))
                    if new_name != tgt_name:
                        query = (
                            f"Update target '{tgt_name}' and rename to"
                            f" '{new_name}'?"
                        )
                    else:
                        query = f"Update target '{tgt_name}'?"
                    if cli.query_yes_no(query):
                        if new_name == tgt_name:
                            targets[new_name] = new_data
                        else:
                            del targets[tgt_name]
                            targets[new_name] = new_data
                            delete_name = tgt_name
                        update_policy = True
        elif main_sel == 2 or shortcut == "delete":
            tgt_name = __i_tgt_pick_menu(targets)
            if tgt_name and cli.query_yes_no(
                f"Delete target '{tgt_name}'? This cannot be undone."
            ):
                del targets[tgt_name]
                update_policy = True
                delete_name = tgt_name
        elif main_sel == 3:
            click.echo_via_pager(targets_summary_output(targets))
        elif main_sel == 4 or main_sel is None:
            return
        shortcut = None
        if update_policy:
            update_policy = False
            notif_policy_copy = __put_and_get_notif_pol(targets, delete_name)
            targets = notif_policy_copy[lib.TARGETS_FIELD]
            delete_name = None


def __put_and_get_notif_pol(targets: Dict, delete_name=None):
    ctx = cfg.get_current_context()
    new_pol = api.get_notification_policy(*ctx.get_api_data())
    new_pol[lib.TARGETS_FIELD].update(**targets)
    if delete_name:
        new_pol[lib.TARGETS_FIELD].pop(delete_name, None)
    api.put_notification_policy(*ctx.get_api_data(), new_pol)
    rv_pol = api.get_notification_policy(*ctx.get_api_data())
    return rv_pol


valid_symbols = ["-", "_"]


def __i_tgt_menu(
    targets: Dict,
    tgt_name: str = None,
    tgt_data: Dict = None,
) -> Optional[Dict]:
    tgt_menu = __build_tgt_menu(tgt_name)
    orig_tgt_name = tgt_name
    if not tgt_data:
        new = True
        rv_tgt_data = {}
    else:
        new = False
        rv_tgt_data = deepcopy(tgt_data)
    error_msg = None
    while True:
        tgt_menu_sel = tgt_menu.show()
        if tgt_menu_sel == 0:
            new_name = input(
                "Supply a unique target name containing letters, numbers and"
                f" valid symbols {valid_symbols}\nTarget Name: "
            )
            if new_name != orig_tgt_name and new_name in targets:
                error_msg = "Error: name already taken"
            elif new_name and __valid_name(new_name):
                tgt_name = new_name
            elif new_name:
                error_msg = "Error: invalid name"
        elif tgt_menu_sel == 1:
            dst_type = __i_dst_pick_menu()
            if dst_type:
                dst_data = __get_dst_data(dst_type)
                if dst_data:
                    if dst_type not in rv_tgt_data or (
                        dst_type in rv_tgt_data
                        and dst_data != rv_tgt_data[dst_type]
                        and cli.query_yes_no(
                            f"Overwrite '{dst_type}' destination(s) in current"
                            " target?"
                        )
                    ):
                        rv_tgt_data[dst_type] = dst_data
                elif dst_data is False:
                    error_msg = f"Error: no valid '{dst_type}' destinations."
                else:
                    rv_tgt_data.pop(dst_type, None)
        elif tgt_menu_sel == 2:
            dst_types = []
            for dst_type in lib.DST_TYPES:
                if dst_type in rv_tgt_data:
                    dst_types.append(dst_type)
            dst_type = __i_dst_pick_menu(dst_types)
            if dst_type:
                dst_data = __get_dst_data(dst_type, rv_tgt_data[dst_type])
                if dst_data is not None:
                    if dst_type not in rv_tgt_data or (
                        dst_type in rv_tgt_data
                        and dst_data != rv_tgt_data[dst_type]
                        and cli.query_yes_no(
                            f"Overwrite '{dst_type}' destination(s) in current"
                            " target?"
                        )
                    ):
                        rv_tgt_data[dst_type] = dst_data
                else:
                    rv_tgt_data.pop(dst_type, None)
        elif tgt_menu_sel == 3:
            dst_types = []
            for dst_type in lib.DST_TYPES:
                if dst_type in rv_tgt_data:
                    dst_types.append(dst_type)
            dst_type = __i_dst_pick_menu(dst_types)
            if dst_type and cli.query_yes_no(
                f"Delete all '{dst_type}' destination(s) from target?"
            ):
                del rv_tgt_data[dst_type]
        elif tgt_menu_sel == 4 or tgt_menu_sel is None:
            return None
        elif tgt_menu_sel == 5:
            if tgt_name and any(
                [dst_type in rv_tgt_data for dst_type in lib.DST_TYPES]
            ):
                now = time.time()
                if new:
                    data = {
                        lib.NOTIF_CREATE_TIME: now,
                        lib.NOTIF_LAST_UPDATED: now,
                    }
                else:
                    data = rv_tgt_data.get(lib.DATA_FIELD, {})
                    data[lib.NOTIF_LAST_UPDATED] = now
                data[lib.ID_FIELD] = tgt_name
                rv_tgt_data["description"] = tgt_name
                rv_tgt_data[lib.DATA_FIELD] = data
                return {tgt_name: rv_tgt_data}
            else:
                if not tgt_name:
                    error_msg = "Error: Cannot apply, invalid target name."
                else:
                    error_msg = (
                        "Error: Cannot apply, invalid or missing"
                        " destination(s)."
                    )
        tgt_menu = __build_tgt_menu(tgt_name, error_msg)
        error_msg = None


def __get_dst_data(dst_type, old_data=None):
    if dst_type == lib.DST_TYPE_EMAIL:
        MARKER = "# Add one email per line. Everything above is ignored.\n"
        if old_data:
            message = MARKER + "\n".join(old_data)
        else:
            message = MARKER
        resp = click.edit(message)
        if resp is None:
            if old_data:
                return old_data
            return None
        resp = resp.split(MARKER, 1)[-1]
        raw_emails = resp.split("\n")
        valid_emails = []
        for email in raw_emails:
            email = email.strip("\n ")
            if __is_valid_email(email):
                valid_emails.append(email)
        if valid_emails:
            return valid_emails
        elif old_data and cli.query_yes_no("No valid emails, keep old data?"):
            return old_data
        elif not old_data:
            return False
        return None
    if dst_type == lib.DST_TYPE_USERS:
        MARKER = "# Add one user per line. Everything above is ignored.\n"
        if old_data:
            message = MARKER + "\n".join(old_data)
        else:
            message = MARKER
        resp = click.edit(message)
        if resp is None:
            if old_data:
                return old_data
            return None
        resp = resp.split(MARKER, 1)[-1]
        raw_users = resp.split("\n")
        valid_users = []
        for user in raw_users:
            valid_users.append(user.strip("\n "))
        if valid_users:
            return valid_users
        if old_data and cli.query_yes_no("No valid users, keep old data?"):
            return old_data
        elif not old_data:
            return False
        return None
    if dst_type == lib.DST_TYPE_SLACK:
        MARKER = (
            "# Provide the URL for your desired Slack hook. Everything"
            " above this line is ignored.\n"
        )
        url_prompt = "URL: "
        if old_data:
            message = MARKER + url_prompt + old_data["url"]
        else:
            message = MARKER + url_prompt
        resp = click.edit(message)
        if resp is None:
            if old_data:
                return old_data
            return None
        resp = resp.split(MARKER, 1)[-1]
        raw_url = resp.split("\n")[0].split(":", 1)[-1].strip()
        if __is_valid_url(raw_url):
            return Slack(url=raw_url).dest
        if old_data and cli.query_yes_no(
            "No valid Slack hook url, keep old data?"
        ):
            return old_data
        elif not old_data:
            return False
        return None
    if dst_type == lib.DST_TYPE_WEBHOOK:
        MARKER = (
            "# Provide the URL for your desired webhook.\n# example:"
            " 'https://my.webhook.example'\n# You may also"
            " specify if you want the notification system to perform TLS"
            " validation before sending the message. Everything above this"
            " line is ignored.\n"
        )
        if old_data:
            url_prompt = f"URL: {old_data['url']}\n"
            no_tls_val = old_data.get("no_tls_validation", True)
            tls_val_prompt = f"TLS Validation (True/False): {not no_tls_val}"
        else:
            url_prompt = "URL: \n"
            tls_val_prompt = "TLS Validation (True/False): "
        message = MARKER + url_prompt + tls_val_prompt
        resp = click.edit(message)
        if resp is None:
            if old_data:
                return old_data
            return None
        resp = resp.split(MARKER, 1)[-1]
        lines = resp.split("\n")
        if len(lines) < 2:
            if old_data:
                return old_data
            return None
        raw_url = resp.split("\n")[0].split(":", 1)[-1].strip()
        raw_bool = resp.split("\n")[1].split(":", 1)[-1].strip()
        raw_bool = __parse_bool_str(raw_bool)
        if __is_valid_url(raw_url):
            return Webhook(raw_url, not raw_bool).dest
        if old_data and cli.query_yes_no(
            "No valid webhook url provided, keep old data?"
        ):
            return old_data
        elif not old_data:
            return False
        return None
    if dst_type == lib.DST_TYPE_SNS:
        MARKER = (
            "# Provide the AWS SNS topic ARN you with to send notifications"
            " to. You may also provide a cross-account AWS IAM role. The AWS"
            " IAM role is required if the destination SNS topic uses"
            " encryption at-rest or if the destination SNS topic access policy"
            " does not include Spyderbat. Everything above this line is"
            " ignored.\n"
        )
        if old_data:
            sns_topic_prompt = f"SNS Topic ARN: {old_data['sns_topic_arn']}\n"
            cross_acct_role = old_data.get("cross_account_iam_role")
            if cross_acct_role:
                cross_acct_role_prompt = (
                    f"Cross Account Role: {cross_acct_role}"
                )
            else:
                cross_acct_role_prompt = "Cross Account Role:"
        else:
            sns_topic_prompt = "SNS Topic ARN:\n"
            cross_acct_role_prompt = "Cross Account Role:"
        message = MARKER + sns_topic_prompt + cross_acct_role_prompt
        resp = click.edit(message)
        if resp is None:
            if old_data:
                return old_data
            return None
        resp = resp.split(MARKER, 1)[-1]
        lines = resp.split("\n")
        if len(lines) < 2:
            if old_data:
                return old_data
            return None
        raw_sns = resp.split("\n")[0].split(":", 1)[-1].strip()
        raw_role = resp.split("\n")[1].split(":", 1)[-1].strip()
        if raw_sns:
            raw_role = raw_role if raw_role else None
            return SNS(raw_role, raw_sns).dest
        if old_data and cli.query_yes_no(
            "No SNS Topic ARN provided, keep old data?"
        ):
            return old_data
        elif not old_data:
            return False
        return None


def __i_tgt_pick_menu(targets: Dict) -> Optional[str]:
    target_names = sorted(list(targets))
    tgt_pick_menu = __build_tgt_pick_menu(target_names)
    tgt_pick_sel = tgt_pick_menu.show()
    if tgt_pick_sel == 0 or tgt_pick_sel is None:
        return None
    else:
        return target_names[tgt_pick_sel - 1]


def __i_dst_pick_menu(dst_types: List = None) -> Optional[str]:
    if dst_types is None:
        dst_types = lib.DST_TYPES
    dst_type_menu = __build_dst_type_menu(dst_types)
    dst_type_sel = dst_type_menu.show()
    if dst_type_sel == 0 or dst_type_sel is None:
        return None
    else:
        return dst_types[dst_type_sel - 1]


def __i_rm_tgt_menu(targets: Dict):
    pass


def __build_main_menu() -> TerminalMenu:
    main_menu_title = (
        "  Notification Target Main Menu.\n  Press Q or Esc to exit. \n"
    )
    main_menu_items = [
        "Create Target",
        "Edit Target",
        "Remove Target",
        "View Targets",
        "Exit",
    ]
    main_menu_cursor = "> "
    main_menu_cursor_style = ("fg_red", "bold")
    main_menu_style = ("bg_red", "fg_yellow")
    main_menu = TerminalMenu(
        menu_entries=main_menu_items,
        title=main_menu_title,
        menu_cursor=main_menu_cursor,
        menu_cursor_style=main_menu_cursor_style,
        menu_highlight_style=main_menu_style,
        cycle_cursor=True,
        clear_screen=True,
    )
    return main_menu


def __build_tgt_menu(tgt_name=None, error_msg=None) -> TerminalMenu:
    menu_cursor = "> "
    cursor_style = ("fg_red", "bold")
    menu_style = ("bg_red", "fg_yellow")
    tgt_menu_title = (
        "  Add Target Menu.\n  Press Q or Esc to back to main menu. \n"
    )
    if error_msg:
        tgt_menu_title = tgt_menu_title + "\n  " + error_msg + "\n"
    if tgt_name:
        set_name = f"Set Name (curr: {tgt_name})"
    else:
        set_name = "Set Name"
    tgt_menu_items = [
        set_name,
        "Add Destination",
        "Edit Destination",
        "Remove Destination",
        "Cancel",
        "Apply Changes",
    ]
    tgt_menu = TerminalMenu(
        tgt_menu_items,
        title=tgt_menu_title,
        menu_cursor=menu_cursor,
        menu_cursor_style=cursor_style,
        menu_highlight_style=menu_style,
        cycle_cursor=True,
        clear_screen=True,
    )
    return tgt_menu


def __build_dst_type_menu(dst_types: List = None):
    menu_cursor = "> "
    cursor_style = ("fg_red", "bold")
    menu_style = ("bg_red", "fg_yellow")
    dst_type_menu_title = "  Select A Destination Type.\n  Press Q or Esc to back to main menu. \n"
    dst_type_menu_items = ["Back"]
    if dst_types is not None:
        dst_type_menu_items.extend(dst_types)
    else:
        dst_type_menu_items.extend(*lib.DST_TYPES)
    dst_type_menu = TerminalMenu(
        dst_type_menu_items,
        title=dst_type_menu_title,
        menu_cursor=menu_cursor,
        menu_cursor_style=cursor_style,
        menu_highlight_style=menu_style,
        cycle_cursor=True,
        clear_screen=True,
    )
    return dst_type_menu


def __build_tgt_pick_menu(target_names: List[str]):
    menu_cursor = "> "
    cursor_style = ("fg_red", "bold")
    menu_style = ("bg_red", "fg_yellow")
    add_tgt_menu_title = (
        "  Select A Target.\n  Press Q or Esc to back to main menu. \n"
    )
    add_tgt_menu_items = ["Back"]
    add_tgt_menu_items.extend(target_names)
    add_tgt_menu = TerminalMenu(
        add_tgt_menu_items,
        title=add_tgt_menu_title,
        menu_cursor=menu_cursor,
        menu_cursor_style=cursor_style,
        menu_highlight_style=menu_style,
        cycle_cursor=True,
        clear_screen=True,
    )
    return add_tgt_menu


def __add_dest_menu() -> TerminalMenu:
    menu_cursor = "> "
    cursor_style = ("fg_red", "bold")
    menu_style = ("bg_red", "fg_yellow")
    add_tgt_menu_title = (
        "  Add Target Menu.\n  Press Q or Esc to back to main menu. \n"
    )
    add_tgt_menu_items = ["Edit Config", "Save Settings", "Back to Main Menu"]
    add_tgt_menu = TerminalMenu(
        add_tgt_menu_items,
        title=add_tgt_menu_title,
        menu_cursor=menu_cursor,
        menu_cursor_style=cursor_style,
        menu_highlight_style=menu_style,
        cycle_cursor=True,
        clear_screen=True,
    )
    return add_tgt_menu


def __del_tgt_menu(targets: Dict) -> TerminalMenu:
    menu_cursor = "> "
    cursor_style = ("fg_red", "bold")
    menu_style = ("bg_red", "fg_yellow")
    del_tgt_menu_title = (
        "  Edit Menu.\n  Press Q or Esc to back to main menu. \n"
    )
    del_tgt_menu_items = ["Edit Config", "Save Settings", "Back to Main Menu"]
    del_tgt_menu = TerminalMenu(
        del_tgt_menu_items,
        title=del_tgt_menu_title,
        menu_cursor=menu_cursor,
        menu_cursor_style=cursor_style,
        menu_highlight_style=menu_style,
        cycle_cursor=True,
        clear_screen=True,
    )
    return del_tgt_menu


def __valid_name(input_string):
    # Define a regular expression pattern to match allowed characters
    pattern = r"^[a-zA-Z0-9\-_]+$"

    # Use the re.match function to check if the input_string matches the pattern
    if re.match(pattern, input_string):
        return True
    else:
        return False


def __is_valid_email(email):
    # Define a regular expression pattern for a valid email address
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"

    # Use the re.match function to check if the email matches the pattern
    if re.match(pattern, email):
        return True
    else:
        return False


def __is_valid_url(url):
    try:
        result = urlparse(url)
        return all(
            [result.scheme, result.netloc]
        )  # Check if both scheme and network location are present
    except ValueError:
        return False


def __parse_bool_str(input) -> bool:
    return input.lower() in [
        "true",
        "1",
        "t",
        "y",
        "yes",
        "yeah",
        "yup",
        "certainly",
        "uh-huh",
    ]
