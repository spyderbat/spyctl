import time
from copy import deepcopy
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional

import click
import urwid as u
import yaml
from simple_term_menu import TerminalMenu
from tabulate import tabulate

import spyctl.api as api
import spyctl.cli as cli
import spyctl.config.configs as cfg
import spyctl.schemas_v2 as schemas
import spyctl.spyctl_lib as lib

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
        self.old_name = name
        self.type = None
        self.dst_data = None
        if tgt_data:
            self.new = False
            self.changed = False
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
            self.changed = True
            self.data = {
                lib.NOTIF_CREATE_TIME: now,
                lib.NOTIF_LAST_UPDATED: now,
                lib.ID_FIELD: "notif_tgt:" + lib.make_uuid(),
                lib.DST_DESCRIPTION: self.name,
            }

    def update_name(self, new_name):
        if new_name != self.name:
            self.changed = True
            self.name = new_name
            self.data[lib.DST_DESCRIPTION] = self.name

    def update_destination(self, dst_type, dst_data):
        if self.type != dst_type or self.dst_data != dst_data:
            self.changed = True
            self.type = dst_type
            self.dst_data = dst_data

    def set_last_updated(self, time: float):
        self.data[lib.NOTIF_LAST_UPDATED] = time

    @property
    def tgt_type_name(self) -> Optional[str]:
        if self.type:
            return lib.DST_TYPE_TO_NAME[self.type]

    @property
    def tgt_data(self) -> Dict:
        return {
            self.name: {self.type: self.dst_data, lib.DATA_FIELD: self.data}
        }

    @property
    def editable_tgt_data(self) -> Dict:
        rv_dict = {self.name: {self.type: self.dst_data}}
        return rv_dict

    @property
    def dst_yaml(self):
        return yaml.dump(self.tgt_data)


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
    row_data.sort(key=lambda row: row[0].lower())
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
    shortcut_map = {
        "create": 0,
        "edit": 1,
        "delete": 2,
    }
    if shortcut is not None:
        shortcut = shortcut_map[shortcut]
    app = InteractiveTargets(notif_policy, shortcut)
    app.start()


def _interactive_targets(notif_policy: Dict, shortcut=None, name_or_id=None):
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


def put_and_get_notif_pol(nt: NotificationTarget, delete_name=None):
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


class InteractiveTargets:
    return_footer = " Q to return"

    MAIN_MENU_ITEMS = [
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

    def __init__(self, notif_pol: Dict, shortcut=None) -> None:
        self.notif_pol = notif_pol
        self.loop = u.MainLoop(
            u.Filler(u.Text("")),
            cli.URWID_PALLET,
            unhandled_input=self.unhandled_input,
        )
        self.menu_stack = []
        self.show_main_menu(shortcut=shortcut)

    @property
    def targets(self) -> Dict:
        return self.notif_pol.get(lib.TARGETS_FIELD, {})

    @property
    def routes(self) -> List:
        return self.notif_pol.get(lib.ROUTES_FIELD, [])

    @property
    def curr_menu_data(self):
        return self.menu_stack[-1][1]

    def unhandled_input(self, key):
        if key in ("q", "enter") and len(self.menu_stack) > 1:
            self.pop_menu()
        elif key in ("q",):
            self.quit()

    def quit(self):
        raise u.ExitMainLoop()

    def start(self):
        self.loop.run()

    def push_update(self, nt: NotificationTarget, delete_name=None):
        self.loop.stop()
        try:
            self.notif_pol = put_and_get_notif_pol(nt, delete_name)
            self.loop.start()
        except Exception as e:
            self.loop.start()
            raise e

    # ----------------------------------------------------------
    # Menu Stack Management
    # ----------------------------------------------------------
    def sub_menu(self, menu: u.Frame, menu_data=None):
        self.menu_stack.append((menu, menu_data))
        self.loop.widget = menu

    def pop_menu(self):
        self.menu_stack.pop()
        self.loop.widget = self.menu_stack[-1][0]

    # ----------------------------------------------------------
    # Menu menu
    # ----------------------------------------------------------
    def show_main_menu(
        self, previous_sel: int = 0, shortcut: int = None, route_id: str = None
    ):
        title = "Notification Targets Main Menu"
        frame = cli.selection_menu_v2(
            title,
            self.MAIN_MENU_ITEMS,
            previous_sel,
            " Q to exit",
            self.handle_main_menu_selection,
        )
        self.loop.widget = frame
        self.menu_stack = [(frame, 0)]
        if shortcut is not None:
            self.handle_main_menu_selection(shortcut)

    def handle_main_menu_selection(self, sel: int, id=None):
        if sel == 0:
            self.start_creation_prompts()
        elif sel == 1:
            self.show_target_sel_menu(self.handle_edit_target)
        elif sel == 2:
            self.show_target_sel_menu(self.handle_delete_target)
        elif sel == 3:
            self.show_pager(targets_summary_output(self.targets))
        elif sel == 4 or sel is None:
            self.quit()

    # ----------------------------------------------------------
    # Target Management Menu
    # ----------------------------------------------------------
    def show_target_mgmt_menu(
        self, nt: NotificationTarget, selected=0, menu_data=None
    ):
        title = "Notification Configuration Menu"
        frame = cli.selection_menu_v2(
            title,
            self.__build_target_mgmt_menu_items(nt),
            selected,
            self.return_footer,
            lambda sel: self.handle_target_mgmt_selection(nt, sel),
        )
        if not menu_data:
            menu_data = nt.name
        nt.old_name = menu_data
        self.sub_menu(frame, menu_data)

    def handle_target_mgmt_selection(self, nt: NotificationTarget, sel: int):
        old_name = self.curr_menu_data

        def update_nt(new_nt: NotificationTarget):
            self.pop_menu()
            self.show_target_mgmt_menu(new_nt, sel, old_name)

        def update_nt_from_edits(new_data: Dict):
            self.pop_menu()
            tgt_name, tgt_data = next(iter(new_data.items()))
            tgt_data[lib.DATA_FIELD] = nt.data
            new_nt = NotificationTarget(tgt_name, tgt_data)
            new_nt.changed = True
            self.show_target_mgmt_menu(new_nt, sel, old_name)

        def show_get_dst_data(dst_type: str):
            self.get_dst_data_prompts(nt, dst_type, lambda: update_nt(nt))

        def edit_target_yaml():
            self.edit_yaml(
                nt.editable_tgt_data, invalid_edit, update_nt_from_edits
            )

        def invalid_edit(error: str):
            self.show_pager(error, edit_target_yaml)

        def should_quit_menu(should_quit: bool):
            self.pop_menu()
            if should_quit:
                self.pop_menu()
                self.show_pager("No changes made.")

        def should_apply_target(should_apply: bool):
            self.pop_menu()
            if should_apply:
                try:
                    nt.set_last_updated(time.time())
                    self.push_update(nt, old_name)
                    self.pop_menu()
                    self.show_pager(f"Successfully added Target '{nt.name}'")
                except Exception as e:
                    self.show_pager(str(e))

        def stay(**_):
            self.pop_menu()

        if sel == 0:
            self.show_edit_name_prompt(nt, lambda: update_nt(nt))
        elif sel == 1:
            self.show_select_dst_type(nt, show_get_dst_data)
        elif sel == 2:
            edit_target_yaml()
        elif sel == 3:
            self.show_pager(nt.dst_yaml)
        elif sel == 4:
            if nt.changed:
                query = "Are you sure you want to discard all changes?"
                frame = cli.urwid_query_yes_no(
                    query, should_quit_menu, stay, "no"
                )
                self.sub_menu(frame)
            else:
                self.pop_menu()
                self.show_pager("No changes made.")
        elif sel == 5:
            if nt.changed:
                query = "Are you sure you want to apply changes?"
                frame = cli.urwid_query_yes_no(
                    query, should_apply_target, stay, "yes"
                )
                self.sub_menu(frame)
            else:
                self.pop_menu()
                self.show_pager("No changes made.")

    # ----------------------------------------------------------
    # Select Target Menu
    # ----------------------------------------------------------
    def show_target_sel_menu(self, handler: callable):
        menu_items = self.__build_target_sel_menu_items()
        title = "Select A Notification Target"
        frame = cli.extended_selection_menu(
            title,
            menu_items,
            self.return_footer,
            handler,
        )
        self.sub_menu(frame)

    def handle_edit_target(self, tgt_name):
        self.pop_menu()
        if tgt_name in self.targets:
            nt = NotificationTarget(tgt_name, self.targets[tgt_name])
            self.show_target_mgmt_menu(nt)

    def handle_delete_target(self, tgt_name):
        def confirm_delete(should_delete=False):
            self.pop_menu()
            if should_delete:
                try:
                    self.push_update(None, tgt_name)
                    self.pop_menu()
                    self.show_pager(f"Deleted target '{tgt_name}'.")
                except Exception as e:
                    self.show_pager(str(e))
            else:
                self.pop_menu()
                self.show_pager("No target deleted.")

        def cancel(**_):
            self.pop_menu()
            self.show_pager("No target deleted.")

        if tgt_name in self.targets:
            query = f"Are you sure you want to delete target '{tgt_name}'"
            frame = cli.urwid_query_yes_no(
                query, confirm_delete, cancel, default="no"
            )
            self.sub_menu(frame)
        else:
            self.pop_menu()
            self.show_pager("No target deleted.")

    # ----------------------------------------------------------
    # Target Creation Prompts
    # ----------------------------------------------------------
    def start_creation_prompts(
        self, nt: NotificationTarget = None, next_func: Callable = None
    ):
        def show_get_dst_data(dst_type: str):
            self.get_dst_data_prompts(nt, dst_type, show_name_prompt)

        def show_name_prompt():
            if next_func:
                self.show_edit_name_prompt(nt, lambda: next_func(nt))
            else:
                self.show_edit_name_prompt(
                    nt, lambda: self.show_target_mgmt_menu(nt)
                )

        if not nt:
            nt = NotificationTarget("")
        else:
            nt = deepcopy(nt)
        self.show_select_dst_type(nt, show_get_dst_data)

    # ----------------------------------------------------------
    # Select Dst Type (Creation Prompt)
    # ----------------------------------------------------------
    def show_select_dst_type(
        self, nt: NotificationTarget, next_menu: Callable
    ):
        title = "Select a Destination Type for your Notifications"
        frame = cli.selection_menu_v2(
            title,
            self.__build_dst_type_menu_items(nt),
            0,
            self.return_footer,
            lambda dst_type: self.handle_dst_type_selection(
                dst_type, next_menu
            ),
        )
        self.sub_menu(frame)

    def handle_dst_type_selection(self, dst_type: str, next_menu: Callable):
        self.pop_menu()
        next_menu(dst_type)

    # ----------------------------------------------------------
    # Get Dst Data Menus (Creation Prompt)
    # ----------------------------------------------------------
    def get_dst_data_prompts(
        self, nt: NotificationTarget, dst_type: str, next_menu: Callable = None
    ):
        def show_get_emails():
            self.show_get_emails_prompt(nt, next_menu)

        def show_get_slack_url():
            self.show_get_slack_url_prompt(nt, next_menu)

        def show_get_webhook_url():
            self.show_get_webhook_url(nt, show_get_tls_val)

        def show_get_tls_val():
            self.show_get_webhook_tls_validation(nt, next_menu)

        def show_get_sns_topic():
            self.show_get_sns_topic_arn(nt, show_get_cross_acct_role)

        def show_get_cross_acct_role():
            self.show_get_cross_acct_role(nt, next_menu)

        if dst_type == lib.DST_TYPE_EMAIL:
            show_get_emails()
        elif dst_type == lib.DST_TYPE_SLACK:
            show_get_slack_url()
        elif dst_type == lib.DST_TYPE_WEBHOOK:
            show_get_webhook_url()
        elif dst_type == lib.DST_TYPE_SNS:
            show_get_sns_topic()

    # Dst Data Emails
    def show_get_emails_prompt(
        self, nt: NotificationTarget, next_menu: Callable = None
    ):
        def validate_emails(emails: str):
            lines = emails.splitlines()
            if len(lines) == 0:
                return "No emails provided"
            error = []
            for line in lines:
                line = line.strip()
                if not lib.is_valid_email(line):
                    error.append(f"'{line}' is not a valid email.")
            if error:
                return " ".join(error)

        if nt.type == lib.DST_TYPE_EMAIL:
            curr_emails = "\n".join(nt.dst_data)
        else:
            curr_emails = ""
        frame = cli.urwid_multi_line_prompt(
            "Provide email addresses to send notifications to, 1 email per line:",
            lambda emails: self.handle_emails_input(
                nt, False, emails, next_menu
            ),
            lambda emails: self.handle_emails_input(
                nt, True, emails, next_menu
            ),
            curr_emails,
            validator=validate_emails,
        )
        self.sub_menu(frame)

    def handle_emails_input(
        self,
        nt: NotificationTarget,
        canceled: bool,
        emails: str,
        next_menu: Callable = None,
    ):
        self.pop_menu()
        if canceled:
            return
        emails = emails.splitlines()
        emails = [email.strip() for email in emails]
        nt.update_destination(lib.DST_TYPE_EMAIL, emails)
        if next_menu:
            next_menu()

    # Dst Data Slack
    def show_get_slack_url_prompt(
        self, nt: NotificationTarget, next_menu: Callable = None
    ):
        def validate_slack_hook(url: str):
            if not lib.is_valid_slack_url(url.strip()):
                return (
                    'URL must start with "https://hooks.slack.com/services/"'
                )

        if nt.type == lib.DST_TYPE_SLACK:
            curr_url = nt.dst_data["url"]
        else:
            curr_url = ""
        frame = cli.urwid_prompt(
            "url",
            "Provide a Slack Hook URL (e.g. https://hooks.slack.com/services/xxxxxxxxxxx/xxxxxxxxxxx/xxxxxxxxxxxxxxxxxxxxxxxx)",
            lambda url: self.handle_slack_input(nt, False, url, next_menu),
            lambda url: self.handle_slack_input(nt, True, url, next_menu),
            curr_url,
            validator=validate_slack_hook,
        )
        self.sub_menu(frame)

    def handle_slack_input(
        self,
        nr: NotificationTarget,
        canceled: bool,
        url: str,
        next_menu: Callable,
    ):
        self.pop_menu()
        if canceled:
            return
        nr.update_destination(lib.DST_TYPE_SLACK, {"url": url.strip()})
        if next_menu:
            next_menu()

    # Dst Data Webhook
    def show_get_webhook_url(
        self, nt: NotificationTarget, next_menu: Callable = None
    ):
        def validate_url(url: str):
            if not lib.is_valid_url(url.strip()):
                return f"'{url.strip()}' is not a valid URL."

        if nt.type == lib.DST_TYPE_WEBHOOK:
            curr_url = nt.dst_data["url"]
        else:
            curr_url = ""
        frame = cli.urwid_prompt(
            "url",
            "Provide a webhook URL (e.g. https://my.webhook.example/location/of/webhook",
            lambda url: self.handle_webhook_url_input(
                nt, False, url, next_menu
            ),
            lambda url: self.handle_webhook_url_input(
                nt, True, url, next_menu
            ),
            curr_url,
            validator=validate_url,
        )
        self.sub_menu(frame)

    def handle_webhook_url_input(
        self, nt: NotificationTarget, canceled: bool, url: str, next_menu
    ):
        self.pop_menu()
        if canceled:
            return
        if nt.type == lib.DST_TYPE_WEBHOOK:
            dst_data = deepcopy(nt.dst_data)
            dst_data["url"] = url.strip()
            nt.update_destination(lib.DST_TYPE_WEBHOOK, dst_data)
        else:
            nt.update_destination(lib.DST_TYPE_WEBHOOK, {"url": url.strip()})
        if next_menu:
            next_menu()

    def show_get_webhook_tls_validation(
        self, nt: NotificationTarget, next_menu: Callable = None
    ):
        if nt.type == lib.DST_TYPE_WEBHOOK:
            default = not nt.dst_data.get("no_tls_validation", True)
        else:
            default = False
        default = "yes" if default else "no"
        frame = cli.urwid_query_yes_no(
            "Would you like to perform TLS Validation on this webhook?",
            lambda resp: self.handle_tls_val_query(nt, resp, False, next_menu),
            lambda resp: self.handle_tls_val_query(nt, resp, True, next_menu),
            default,
        )
        self.sub_menu(frame)

    def handle_tls_val_query(
        self,
        nt: NotificationTarget,
        resp: bool,
        cancel,
        next_menu: Callable = None,
    ):
        self.pop_menu()
        if cancel:
            return
        dst_data = deepcopy(nt.dst_data)
        dst_data["no_tls_validation"] = not resp
        nt.update_destination(lib.DST_TYPE_WEBHOOK, dst_data)
        if next_menu:
            next_menu()

    # Dst Data SNS
    def show_get_sns_topic_arn(
        self, nt: NotificationTarget, next_menu: Callable = None
    ):
        if nt.type == lib.DST_TYPE_SNS:
            curr_topic = nt.dst_data["sns_topic_arn"]
        else:
            curr_topic = ""
        description = "Provide an AWS SNS Topic ARN (e.g. arn:aws:sns:region:account-id:topic-name)"
        frame = cli.urwid_prompt(
            "Topic ARN",
            description,
            lambda topic_arn: self.handle_sns_topic_input(
                nt, topic_arn, False, next_menu
            ),
            lambda topic_arn: self.handle_sns_topic_input(
                nt, topic_arn, False, next_menu
            ),
            curr_topic,
        )
        self.sub_menu(frame)

    def handle_sns_topic_input(
        self,
        nt: NotificationTarget,
        topic_arn: str,
        cancel: bool,
        next_menu: Callable = None,
    ):
        self.pop_menu()
        if cancel:
            return
        if nt.type == lib.DST_TYPE_SNS:
            dst_data = deepcopy(nt.dst_data)
            dst_data["sns_topic_arn"] = topic_arn
            nt.update_destination(lib.DST_TYPE_SNS, dst_data)
        else:
            nt.update_destination(
                lib.DST_TYPE_SNS, {"sns_topic_arn": topic_arn}
            )
        if next_menu:
            next_menu()

    def show_get_cross_acct_role(
        self, nt: NotificationTarget, next_menu: Callable
    ):
        if nt.type == lib.DST_TYPE_SNS:
            curr_role = nt.dst_data.get("cross_account_iam_role", None)
        else:
            curr_role = ""
        description = "Provide an AWS IAM Role ARN with cross-account permissions (e.g. arn:aws:iam::account-id:role/role-name)"
        frame = cli.urwid_prompt(
            "Role ARN",
            description,
            lambda role_arn: self.handle_iam_role_input(
                nt, role_arn, False, next_menu
            ),
            lambda role_arn: self.handle_iam_role_input(
                nt, role_arn, True, next_menu
            ),
            curr_role,
        )
        self.sub_menu(frame)

    def handle_iam_role_input(
        self,
        nt: NotificationTarget,
        role_arn: str,
        cancel: bool,
        next_menu: Callable = None,
    ):
        self.pop_menu()
        if cancel:
            return
        dst_data = deepcopy(nt.dst_data)
        dst_data["cross_account_iam_role"] = role_arn
        nt.update_destination(lib.DST_TYPE_SNS, dst_data)
        if next_menu:
            next_menu()

    # ----------------------------------------------------------
    # Set Target Name (Creation Prompt)
    # ----------------------------------------------------------
    def show_edit_name_prompt(
        self, nt: NotificationTarget, next_menu: Callable = None
    ):
        def validate_name(tmp_name: str) -> str:
            if tmp_name in self.targets and tmp_name != nt.old_name:
                return "Target names must be unique."
            if not lib.is_valid_tgt_name(tmp_name):
                return lib.TGT_NAME_ERROR_MSG

        self.sub_menu(
            cli.urwid_prompt(
                "Name",
                "Provide a name for the Notification Config.",
                lambda name: self.handle_name_input(
                    nt, False, name, next_menu
                ),
                lambda name: self.handle_name_input(nt, True, name, next_menu),
                nt.name,
                validator=validate_name,
            )
        )

    def handle_name_input(
        self,
        nt: NotificationTarget,
        canceled: bool,
        name: str,
        next_menu: Callable = None,
    ):
        self.pop_menu()
        if canceled:
            return
        nt.update_name(name)
        if next_menu:
            next_menu()

    # ----------------------------------------------------------
    # Simple Pager-like Menu
    # ----------------------------------------------------------
    def show_pager(self, data: str, on_close_handler: Callable = None):
        pager = cli.urwid_pager(
            data,
            self.return_footer,
            lambda: self.on_pager_close(on_close_handler),
        )
        self.sub_menu(pager)

    def on_pager_close(self, on_close_handler: Callable = None):
        self.pop_menu()
        if on_close_handler:
            on_close_handler()

    # ----------------------------------------------------------
    # Edit Yaml in Default Text Editor
    # ----------------------------------------------------------
    def edit_yaml(
        self, data: Dict, invalid_func: Callable, next_func: Callable
    ):
        self.loop.stop()
        yaml_str = yaml.dump(data)
        edits = click.edit(yaml_str, extension=".yaml")
        self.loop.start()
        if edits:
            try:
                edits: Dict = yaml.load(edits, lib.UniqueKeyLoader)
                if not isinstance(edits, dict):
                    raise TypeError("Target data should be a dictionary.")
            except Exception as e:
                error = f"Unable to load yaml. {e}"
                invalid_func(error)
                return
            tgt_data = next(iter(edits.values()))
            error = schemas.valid_notification_target(
                tgt_data, interactive=True
            )
            if isinstance(error, str):
                invalid_func(error)
                return
            next_func(edits)
            return
        else:
            next_func(data)

    # ----------------------------------------------------------
    # Misc
    # ----------------------------------------------------------
    def __build_dst_type_menu_items(
        self, nt: NotificationTarget
    ) -> List[cli.menu_item]:
        menu_items = []
        if nt.type:
            curr_str = lib.DST_TYPE_TO_NAME[nt.type]
            menu_items.append(
                cli.menu_item(
                    f"Current (curr: {curr_str})",
                    "Use the current Destination type.",
                    nt.type,
                )
            )
        menu_items.extend(
            [
                cli.menu_item(
                    lib.DST_TYPE_TO_NAME[d_type],
                    lib.DST_TYPE_TO_DESC[d_type],
                    d_type,
                )
                for d_type in lib.DST_TYPES
            ]
        )
        return menu_items

    def __build_target_sel_menu_items(self):
        menu_items = [cli.menu_item("Back", "", None)]
        for name, tgt_data in self.targets.items():
            dst_type = next(iter(tgt_data))
            menu_items.append(
                cli.menu_item(
                    f"{name} ({lib.DST_TYPE_TO_NAME[dst_type]})", "", name
                )
            )
        return menu_items

    def __build_target_mgmt_menu_items(self, nt: NotificationTarget):
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
                "Cancel", "Return to Main Menu without making changes.", 4
            ),
            cli.menu_item("Apply", "Apply changes.", 5),
        ]
        return menu_items
