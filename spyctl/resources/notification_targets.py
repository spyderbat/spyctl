import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Iterable
import yaml

import click
from simple_term_menu import TerminalMenu
from tabulate import tabulate

import spyctl.cli as cli
import spyctl.spyctl_lib as lib
import spyctl.api as api
import spyctl.config.configs as cfg
import spyctl.schemas_v2 as schemas

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


class NotificationTarget:
    def __init__(self, name, tgt_data=None) -> None:
        self.name = name
        self.type = None
        self.dst_data = None
        if tgt_data:
            self.new = False
            self.data = tgt_data.get(lib.DATA_FIELD, {})
            self.data[lib.DST_DESCRIPTION] = self.name
            for dst_type in lib.DST_TYPES:
                if dst_type in tgt_data:
                    self.type = dst_type
                    self.dst_data = tgt_data[dst_type]

                    break
        else:
            now = time.time()
            self.new = True
            self.data = {
                lib.NOTIF_CREATE_TIME: now,
                lib.NOTIF_LAST_UPDATED: now,
                lib.ID_FIELD: "notif_tgt:" + lib.make_uuid(),
                lib.DST_DESCRIPTION: self.name,
            }

    def update_name(self, new_name) -> bool:
        if new_name != self.name:
            self.name = new_name
            now = time.time()
            self.data[lib.NOTIF_LAST_UPDATED] = now
            self.data[lib.DST_DESCRIPTION] = self.name
            return True
        return False

    def update_destination(self, dst_type, dst_data) -> bool:
        if self.type != dst_type or self.dst_data != dst_data:
            now = time.time()
            self.data[lib.NOTIF_LAST_UPDATED] = now
            self.type = dst_type
            self.dst_data = dst_data
            return True
        False

    def set_last_updated(self, time: float):
        self.data[lib.NOTIF_LAST_UPDATED] = time

    @property
    def tgt_data(self) -> Dict:
        return {
            self.name: {self.type: self.dst_data, lib.DATA_FIELD: self.data}
        }

    @property
    def dst_yaml(self):
        rv_dict = {self.name: {self.type: self.tgt_data}}
        return yaml.dump(rv_dict)


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


def interactive_targets(notif_policy: Dict, shortcut=None, name_or_id=None):
    targets: Dict = notif_policy.get(lib.TARGETS_FIELD, {})
    sel = None
    title = "Notification Targets Main Menu"
    menu_items = [
        cli.menu_item(
            "Create",
            "Create a new Target. This is a named destination for"
            " notifications.",
            0,
        ),
        cli.menu_item("Edit", "Edit an existing Target.", 1),
        cli.menu_item("Delete", "Delete an existing Target.", 2),
        cli.menu_item("View", "View a summary of existing Targets.", 3),
        cli.menu_item("Exit", "Leave this menu.", 4),
    ]
    while True:
        nt = None
        delete = None
        if not shortcut:
            sel = cli.selection_menu(title, menu_items, sel)
        if sel == 0 or shortcut == "create":
            nt = __i_create_target(targets)
            if not nt:
                cli.notice("No changes made.")
        elif sel == 1 or shortcut == "edit":
            if name_or_id and name_or_id in targets:
                tgt_name = name_or_id
            else:
                tgt_name = i_tgt_pick_menu(targets)
            if tgt_name:
                tgt_data = targets[tgt_name]
                nt = __i_tgt_menu(
                    targets, NotificationTarget(tgt_name, tgt_data)
                )
                if not nt:
                    cli.notice("No changes made.")
                else:
                    delete = tgt_name
        elif sel == 2 or shortcut == "delete":
            if name_or_id and name_or_id in targets:
                tgt_name = name_or_id
            else:
                tgt_name = i_tgt_pick_menu(targets)
            if not tgt_name or not cli.query_yes_no(
                f"Are you sure you want to delete target {tgt_name}?", "no"
            ):
                cli.notice("No targets deleted")
            else:
                delete = tgt_name
        elif sel == 3 or shortcut == "view":
            click.echo_via_pager(targets_summary_output(targets))
        elif sel == 4 or sel is None:
            return
        shortcut = None
        name_or_id = None
        if delete or nt:
            notif_policy = __put_and_get_notif_pol(nt, delete)
            targets = notif_policy.get(lib.TARGETS_FIELD, {})


def prompt_tgt_name(targets: Dict, old_name=None) -> Optional[str]:
    try:
        while True:
            tgt_name = cli.input_window(
                "Provide a name",
                "Name for the Target. Referenced during notification configuration.",
                existing_data=old_name,
                error_msg=lib.TGT_NAME_ERROR_MSG,
                validator=lib.is_valid_tgt_name,
            )
            if tgt_name in targets and tgt_name != old_name:
                cli.notice("Target names must be unique.")
                continue
            break
        return tgt_name
    except KeyboardInterrupt:
        return None


def prompt_select_dst_type() -> Optional[str]:
    try:
        prompt = "Select a Destination Type"
        menu_items = [
            cli.menu_item(
                lib.DST_TYPE_TO_NAME[d_type],
                lib.DST_TYPE_TO_DESC[d_type],
                d_type,
            )
            for d_type in lib.DST_TYPES
        ]
        menu_items.append(cli.menu_item("Cancel", "", None))
        return cli.selection_menu(prompt, menu_items)
    except KeyboardInterrupt:
        return None


def __i_create_target(targets, old_type=None, old_name=None, old_data=None):
    quit_prompt = (
        "Are you sure you want to discard this new Notification Target?"
    )
    # Get the type of destination for the Target
    quit = False
    while True:
        if quit and cli.query_yes_no(quit_prompt, "no"):
            return None
        quit = False
        dst_type = prompt_select_dst_type()
        if not dst_type:
            quit = True
            continue
        # Get the data for the target
        dst_data = get_dst_data(dst_type)
        if not dst_data:
            quit = True
            continue
        break
    # Get the name for the target
    quit = False
    while True:
        if quit and cli.query_yes_no(quit_prompt, "no"):
            return None
        quit = False
        tgt_name = prompt_tgt_name(targets, old_name)
        if not tgt_name:
            quit = True
            continue
        break
    nt = NotificationTarget(tgt_name)
    nt.update_destination(dst_type, dst_data)
    return __i_tgt_menu(targets, nt)


def __put_and_get_notif_pol(nt: NotificationTarget, delete_name=None):
    ctx = cfg.get_current_context()
    notif_pol = api.get_notification_policy(*ctx.get_api_data())
    targets: Dict = notif_pol.get(lib.TARGETS_FIELD, {})
    if delete_name:
        targets.pop(delete_name, None)
    if nt:
        targets.update(nt.tgt_data)
    notif_pol[lib.TARGETS_FIELD] = targets
    api.put_notification_policy(*ctx.get_api_data(), notif_pol)
    rv_pol = api.get_notification_policy(*ctx.get_api_data())
    return rv_pol


def __i_tgt_menu(targets: Dict, nt: NotificationTarget):
    if nt.new:
        apply_desc = "Save new Target for use with Notifications."
    else:
        apply_desc = "Save changes to current Target."
    title = "Target Menu"
    sel = 0
    changed = False
    if nt.new:
        changed = True
    while True:
        menu_items = [
            cli.menu_item(
                f"Set Name (curr: {nt.name})", "Update the Target's name.", 0
            ),
            cli.menu_item(
                f"Set Destination (curr: {lib.DST_TYPE_TO_NAME[nt.type]})",
                "Update existing destination or change the type entirely.",
                1,
            ),
            cli.menu_item("Edit", "Manually edit the Target YAML.", 2),
            cli.menu_item("View", "View the Target YAML.", 3),
            cli.menu_item(
                "Cancel", "Return to previous menu without making changes.", 4
            ),
            cli.menu_item("Apply", apply_desc, 5),
        ]
        sel = cli.selection_menu(title, menu_items, sel)
        if sel == 0:
            tgt_name = prompt_tgt_name(targets, nt.name)
            if tgt_name:
                changed = nt.update_name(tgt_name)
        elif sel == 1:
            dst_type = prompt_select_dst_type()
            if dst_type and dst_type == nt.type:
                dst_data = get_dst_data(dst_type, nt.dst_data)
                if not dst_data:
                    cli.notice("No changes made.")
                    continue
                changed = nt.update_destination(dst_type, dst_data)
        elif sel == 2:
            while True:
                edits = click.edit(yaml.dump(nt.tgt_data), extension=".yaml")
                if edits:
                    try:
                        edits = yaml.load(edits, lib.UniqueKeyLoader)
                    except Exception as e:
                        cli.notice(f"Unable to load yaml. {e}")
                        continue
                    tgt_name, tgt_data = next(iter(edits.items()))
                    if not schemas.valid_notification_target(tgt_data, True):
                        continue
                    tgt_data[lib.DATA_FIELD] = nt.data
                    nt = NotificationTarget(tgt_name, tgt_data)
                    nt.set_last_updated(time.time())
                    changed = True
                else:
                    cli.notice("No edits made.")
                break
        elif sel == 3:
            click.echo_via_pager(yaml.dump(nt.tgt_data))
        elif sel == 4 or sel is None:
            if not changed or cli.query_yes_no(
                "Are you sure you want to discard all changes?", "no"
            ):
                return
        elif sel == 5:
            if not changed:
                return None
            if cli.query_yes_no("Are you sure you want to apply changes?"):
                return nt


def get_dst_data(dst_type, old_data=None):
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
            if lib.is_valid_email(email):
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
        if lib.is_valid_url(raw_url):
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
        if lib.is_valid_url(raw_url):
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


def i_tgt_pick_menu(targets: Iterable) -> Optional[str]:
    target_names = sorted(list(targets))
    tgt_pick_menu = __build_tgt_pick_menu(target_names)
    tgt_pick_sel = tgt_pick_menu.show()
    if tgt_pick_sel == 0 or tgt_pick_sel is None:
        return None
    else:
        return target_names[tgt_pick_sel - 1]


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
