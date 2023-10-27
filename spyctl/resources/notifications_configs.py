from typing import Dict, List, Optional
import time
from copy import deepcopy

import click
import yaml
from simple_term_menu import TerminalMenu
from tabulate import tabulate

import spyctl.api as api
import spyctl.cli as cli
import spyctl.config.configs as cfg
import spyctl.resources.notification_targets as nt
import spyctl.resources.notification_config_templates as nct
import spyctl.schemas_v2 as schemas
import spyctl.spyctl_lib as lib

NOTIFICATIONS_HEADERS = [
    "NAME",
    "TYPE",
    "DESTINATION",
    "AGE",
]

DEFAULT_NOTIFICATION_CONFIG = {
    lib.API_FIELD: lib.API_VERSION,
    lib.KIND_FIELD: lib.NOTIFICATION_KIND,
    lib.METADATA_FIELD: {
        lib.METADATA_TYPE_FIELD: "object",
        lib.NAME_FIELD: None,
    },
    lib.SPEC_FIELD: {
        lib.ENABLED_FIELD: True,
        lib.NOTIF_DEFAULT_SCHEMA: None,
        lib.NOTIF_CONDITION_FIELD: None,
        lib.NOTIF_TITLE_FIELD: None,
        lib.NOTIF_MESSAGE_FIELD: None,
        lib.NOTIF_NOTIFY_FIELD: {},
    },
}


class NotificationRoute:
    """
    apiVersion: spyderbat/v1
    kind: SpyderbatNotification
    metadata:
      type: object
      name: Agent Health
    spec:
      enabled: true
      schemaType: event_opsflag:agent_offline
      condition: ephemeral = true
      interval: 86400  # aggregation window
      title: "Agent Offline"
      message: "Detected {{ref.id}} offline at {{time}}."
      notify:
        - email:
            address: admins@rmi.org
            template: agent_alert_email
            title: "Agent Offline"
        - slack:
            url: https://…
            template: agent_alert_slack
            icon: :red_circle:
        - targets:
            admin_email:
                title: "Admin Notification: Agent Offline"
            admin_slack:
                icon: :red_circle:
    """

    def __init__(self, notification_configuration: Dict) -> None:
        self.settings = notification_configuration
        meta = notification_configuration[lib.METADATA_FIELD]
        if lib.METADATA_UID_FIELD not in meta:
            self.id = "notif:" + lib.make_uuid()
            meta[lib.METADATA_UID_FIELD] = self.id
            self.new = True
        else:
            self.id = meta[lib.METADATA_UID_FIELD]
            self.new = False
        self.name = meta[lib.NAME_FIELD]
        self.create_time = meta.get(lib.NOTIF_CREATE_TIME, time.time())
        self.last_updated = time.time()
        meta[lib.NOTIF_CREATE_TIME] = self.create_time
        meta[lib.NOTIF_LAST_UPDATED] = self.last_updated
        spec = notification_configuration[lib.SPEC_FIELD]
        self.dst_type = None
        self.dst_data = None
        if spec[lib.NOTIF_NOTIFY_FIELD]:
            self.dst_type, self.dst_data = next(
                iter(spec[lib.NOTIF_NOTIFY_FIELD].items())
            )
        self.changed = False

    def update(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if key == "name" and value != self.name:
                self.changed = True
                self.name = value
                self.settings[lib.METADATA_FIELD][
                    lib.METADATA_NAME_FIELD
                ] = value
            elif (
                key == "condition"
                and value
                != self.settings[lib.SPEC_FIELD][lib.NOTIF_CONDITION_FIELD]
            ):
                self.changed = True
                self.settings[lib.SPEC_FIELD][
                    lib.NOTIF_CONDITION_FIELD
                ] = value
            elif (
                key == "interval"
                and value
                != self.settings[lib.SPEC_FIELD][lib.NOTIF_INTERVAL_FIELD]
            ):
                self.changed = True
                self.settings[lib.SPEC_FIELD][lib.NOTIF_INTERVAL_FIELD] = value
            elif (
                key == "enabled"
                and value != self.settings[lib.SPEC_FIELD][lib.ENABLED_FIELD]
            ):
                self.changed = True
                self.settings[lib.SPEC_FIELD][lib.ENABLED_FIELD] = value
            elif (
                key == "title"
                and value
                != self.settings[lib.SPEC_FIELD][lib.NOTIF_TITLE_FIELD]
            ):
                self.changed = True
                self.settings[lib.SPEC_FIELD][lib.NOTIF_TITLE_FIELD] = value
            elif (
                key == "message"
                and value
                != self.settings[lib.SPEC_FIELD][lib.NOTIF_MESSAGE_FIELD]
            ):
                self.changed = True
                self.settings[lib.SPEC_FIELD][lib.NOTIF_MESSAGE_FIELD] = value
            elif (
                key == "schema"
                and value
                != self.settings[lib.SPEC_FIELD][lib.NOTIF_DEFAULT_SCHEMA]
            ):
                self.changed = True
                self.settings[lib.SPEC_FIELD][lib.NOTIF_DEFAULT_SCHEMA] = value
            elif key == "notify" or key == "destination":
                dst_type, dst_data = next(iter(value.items()))
                if dst_type != self.dst_type or dst_data != self.dst_data:
                    self.changed = True
                    self.settings[lib.SPEC_FIELD][
                        lib.NOTIF_NOTIFY_FIELD
                    ] = value
                    self.dst_type = dst_type
                    self.dst_data = dst_data

    def set_last_updated(self, time: float):
        self.changed = True
        self.last_updated = time

    def get_settings(self) -> Dict:
        return self.settings

    def get_notify_data(self, dst_type):
        return self.settings[lib.SPEC_FIELD][lib.NOTIF_NOTIFY_FIELD].get(
            dst_type
        )

    @property
    def targets(self) -> List[str]:
        if self.dst_type != lib.NOTIF_DST_TGTS:
            return []
        rv = [tgt_name for tgt_name in self.dst_data]
        return rv

    @property
    def curr_dest(self) -> Optional[str]:
        return self.dst_type

    @property
    def dst_name(self) -> int:
        if self.dst_type == lib.NOTIF_DST_TGTS:
            return "Target(s)"
        else:
            return lib.DST_TYPE_TO_NAME[self.dst_type]

    @property
    def route(self) -> Dict:
        rv = {}
        if self.targets:
            rv[lib.TARGETS_FIELD] = self.targets
        else:
            rv["destination"] = {self.dst_type: self.dst_data}
        rv[lib.DATA_FIELD] = {
            lib.NOTIF_CREATE_TIME: self.create_time,
            lib.ID_FIELD: self.id,
            lib.NOTIF_LAST_UPDATED: self.last_updated,
            lib.NOTIF_SETTINGS_FIELD: self.get_settings(),
            lib.NOTIF_NAME_FIELD: self.name,
        }
        rv[lib.ROUTE_EXPR] = {"property": "data.route_id", "equals": self.id}
        return rv

    @property
    def schema(self) -> str:
        return self.get_settings()[lib.SPEC_FIELD][lib.NOTIF_DEFAULT_SCHEMA]

    @property
    def condition(self) -> str:
        return self.get_settings()[lib.SPEC_FIELD][lib.NOTIF_CONDITION_FIELD]

    @property
    def interval(self) -> int:
        return self.get_settings()[lib.SPEC_FIELD][lib.NOTIF_INTERVAL_FIELD]

    @property
    def title(self) -> Optional[str]:
        return self.get_settings()[lib.SPEC_FIELD].get(lib.NOTIF_TITLE_FIELD)

    @property
    def message(self) -> Optional[str]:
        return self.get_settings()[lib.SPEC_FIELD].get(lib.NOTIF_MESSAGE_FIELD)

    @property
    def enabled(self) -> bool:
        return self.get_settings()[lib.SPEC_FIELD].get(lib.ENABLED_FIELD, True)


class NotificationConfigTemplate:
    def __init__(self, config: Dict) -> None:
        self.display_name = config["display_name"]
        self.description = config["description"]
        self.config_values = config["config"]

    def update_rt(self, rt: NotificationRoute):
        for key in rt.settings[lib.SPEC_FIELD]:
            if key in self.pre_conf_fields:
                rt.update(**{key: self.pre_conf_fields[key]})


def __load_notif_configs() -> List[NotificationConfigTemplate]:
    rv = []
    for config in nct.TEMPLATES:
        rv.append(NotificationConfigTemplate(config))
    return rv


NOTIF_CONFIG_TEMPLATES: List[
    NotificationConfigTemplate
] = __load_notif_configs()


def notifications_summary_output(routes: Dict, notif_type: str):
    data = []
    if (
        notif_type == lib.NOTIF_TYPE_ALL
        or notif_type == lib.NOTIF_TYPE_DASHBOARD
    ):
        dashboard_search_notifications = __parse_dashboard_notifications(
            routes
        )
        if dashboard_search_notifications:
            data.extend(__get_dashboard_data(dashboard_search_notifications))
    if notif_type == lib.NOTIF_TYPE_ALL or notif_type == lib.NOTIF_TYPE_OBJECT:
        object_notifications = __parse_object_notifications(routes)
        if object_notifications:
            data.extend(__get_object_data(object_notifications))
    return tabulate(data, NOTIFICATIONS_HEADERS, "plain")


def __parse_object_notifications(routes: Dict):
    rv = []
    for route in routes:
        if __is_object_notification(route):
            rv.append(route)
    return rv


def __parse_dashboard_notifications(routes: Dict):
    rv = []
    if not isinstance(routes, list):
        return rv
    for route in routes:
        if __is_dashboard_notification(route):
            rv.append(route)
    return rv


def __is_object_notification(route: Dict) -> bool:
    if not isinstance(route, dict):
        return False
    data: Dict = route.get(lib.NOTIF_DATA_FIELD)
    if not isinstance(data, dict):
        return False
    settings = data.get(lib.NOTIF_SETTINGS_FIELD)
    if not isinstance(settings, dict):
        return False
    kind = settings.get(lib.KIND_FIELD)
    if kind == lib.NOTIFICATION_KIND:
        return True
    return False


def __is_dashboard_notification(route: Dict) -> bool:
    if not isinstance(route, dict):
        return False
    data: Dict = route.get(lib.NOTIF_DATA_FIELD)
    if not isinstance(data, dict):
        # This is the default notification type and data is
        # an optional field managed by the UI
        return True
    settings = data.get(lib.NOTIF_SETTINGS_FIELD)
    if not isinstance(settings, dict):
        # Same reason as above
        return True
    kind = settings.get(lib.KIND_FIELD)
    if kind == lib.NOTIFICATION_KIND:
        # In case we get explicit about dashboard search notifications
        notif_type = lib.get_metadata_type(settings)
        if notif_type == lib.NOTIF_TYPE_DASHBOARD:
            return True
        else:
            return False
    return True


def __get_object_data(routes: List[Dict]):
    table_rows = []
    for route in routes:
        data = route.get(lib.DATA_FIELD, {})
        if isinstance(data, dict):
            name = data.get(
                lib.NAME_FIELD, data.get(lib.ID_FIELD, lib.NOT_AVAILABLE)
            )
            create_time = data.get(lib.NOTIF_CREATE_TIME)
            if create_time:
                age = lib.calc_age(create_time)
            else:
                age = lib.NOT_AVAILABLE
        else:
            name = lib.NOT_AVAILABLE
            age = lib.NOT_AVAILABLE
        dst_count = NotificationRoute(
            route[lib.DATA_FIELD][lib.NOTIF_SETTINGS_FIELD]
        ).dst_name
        table_rows.append(
            [
                name,
                lib.NOTIF_TYPE_OBJECT,
                dst_count,
                age,
            ]
        )
    return table_rows


def __get_dashboard_data(routes: List[Dict]):
    table_rows = []
    for route in routes:
        data = route.get(lib.DATA_FIELD, {})
        if isinstance(data, dict):
            name = data.get(
                lib.NAME_FIELD, data.get(lib.ID_FIELD, lib.NOT_AVAILABLE)
            )
            create_time = data.get(lib.NOTIF_CREATE_TIME)
            if create_time:
                age = lib.calc_age(create_time)
            else:
                age = lib.NOT_AVAILABLE
        else:
            name = lib.NOT_AVAILABLE
            age = lib.NOT_AVAILABLE
        table_rows.append(
            [
                name,
                lib.NOTIF_TYPE_DASHBOARD,
                lib.DST_NAME_SNS,
                age,
            ]
        )
    return table_rows


def interactive_notifications(
    notif_policy: Dict, shortcut=None, route_id=None
):
    routes: List[Dict] = notif_policy.get(lib.ROUTES_FIELD, [])
    targets = notif_policy.get(lib.TARGETS_FIELD, {})
    sel = None
    title = "Notification Configurations Main Menu"
    menu_items = [
        cli.menu_item("Create", "Create a new Notification Configuration", 0),
        cli.menu_item(
            "Edit", "Edit an existing Notification Configuration", 1
        ),
        cli.menu_item(
            "Delete", "Delete an existing Notification Configuration", 2
        ),
        cli.menu_item(
            "View", "View a summary of existing Notification Configurations", 3
        ),
        cli.menu_item("Exit", "Leave this menu", 4),
    ]
    while True:
        nr = None
        delete = None
        id_index = __build_id_index(routes)
        if not shortcut:
            sel = cli.selection_menu(title, menu_items, sel)
        if sel == 0 or shortcut == "create":
            nr = __i_create_notification(targets)
            if not nr:
                cli.notice("No changes made.")
        elif sel == 1 or shortcut == "edit":
            if route_id and route_id in id_index:
                nr_id = route_id
            else:
                nr_id = __i_notif_pick_menu(routes)
            if nr_id:
                route = routes[id_index[nr_id]]
                if lib.NOTIF_SETTINGS_FIELD not in route.get(
                    lib.DATA_FIELD, {}
                ):
                    cli.notice("Legacy Notifications Editing not supported.")
                else:
                    nr = __i_notif_menu(
                        targets,
                        NotificationRoute(
                            route[lib.DATA_FIELD][lib.NOTIF_SETTINGS_FIELD]
                        ),
                    )
                    if not nr:
                        cli.notice("No changes made.")
                    else:
                        delete = nr_id
        elif sel == 2 or shortcut == "delete":
            if route_id and route_id in id_index:
                nr_id = route_id
            else:
                nr_id = __i_notif_pick_menu(routes)
            if nr_id:
                route = routes[id_index[nr_id]]
                if lib.NOTIF_SETTINGS_FIELD in route.get(lib.DATA_FIELD, {}):
                    name = NotificationRoute(
                        route[lib.DATA_FIELD][lib.NOTIF_SETTINGS_FIELD]
                    )
                    name = f"{name} - {nr_id}"
                else:
                    name = nr_id
                if cli.query_yes_no(
                    f"Delete notification '{name}'? This cannot be undone."
                ):
                    delete = nr_id
        elif sel == 3 or shortcut == "view":
            click.echo_via_pager(
                notifications_summary_output(routes, lib.NOTIF_TYPE_ALL)
            )
        elif sel == 4 or sel is None:
            return
        shortcut = None
        route_id = None
        if delete or nr:
            notif_policy = __put_and_get_notif_pol(nr, delete)
            routes: List[Dict] = notif_policy.get(lib.ROUTES_FIELD, [])
            targets = notif_policy.get(lib.TARGETS_FIELD, {})


def __i_create_notification(
    targets: Dict, nr: NotificationRoute = None
) -> Optional[NotificationRoute]:
    quit_prompt = (
        "Are you sure you want to discard this new Notification Configuration?"
    )
    if not nr:
        while True:
            new = True
            nr = NotificationRoute(deepcopy(DEFAULT_NOTIFICATION_CONFIG))
            config_vals = __prompt_pre_config_selection()
            if config_vals == "custom":
                break
            if config_vals:
                nr.update(**config_vals)
                break
            elif cli.query_yes_no(quit_prompt):
                return None
    else:
        new = False
    # Ask for destinations
    quit = False
    while True:
        if quit and cli.query_yes_no(quit_prompt, "no"):
            return None
        quit = False
        dst_type = __prompt_select_dst_type(nr)
        if not dst_type:
            quit = True
            continue
        if dst_type == lib.NOTIF_DST_TGTS:
            __i_edit_targets(targets, nr)
            if not nr.targets:
                continue
        else:
            dst_data = nt.get_dst_data(dst_type, nr.get_notify_data(dst_type))
            if not dst_data:
                continue
            nr.update(destination={dst_type: dst_data})
        if cli.query_yes_no(
            "Continue? Respond with 'no' to re-configure Notification destination."
        ):
            break
    # Get the name for the Notification Configuration
    quit = False
    while True:
        if quit and cli.query_yes_no(quit_prompt, "no"):
            return None
        quit = False
        name = __prompt_nr_name(nr)
        if not name:
            quit = True
            continue
        nr.update(name=name)
        break
    # Get the schema type
    quit = False
    while True:
        if new and nr.schema:
            break
        if quit and cli.query_yes_no(quit_prompt, "no"):
            return None
        quit = False
        schema_type = __prompt_schema_type(nr)
        if not schema_type:
            quit = True
            continue
        nr.update(schema=schema_type)
        break
    # Get the condition
    quit = False
    while True:
        if new and nr.condition:
            break
        if quit and cli.query_yes_no(quit_prompt, "no"):
            return None
        quit = False
        condition = __prompt_condition(nr)
        if not condition:
            quit = True
            continue
        nr.update(condition=condition)
        break
    # Get title
    quit = False
    while True:
        if quit and cli.query_yes_no(quit_prompt, "no"):
            return None
        quit = False
        title = __prompt_title(nr)
        if not title:
            quit = True
            continue
        nr.update(title=title)
        break
    # Get message
    while True:
        if quit and cli.query_yes_no(quit_prompt, "no"):
            return None
        quit = False
        message = __prompt_message(nr)
        if not message:
            quit = True
            continue
        nr.update(message=message)
        break
    if new:
        return __i_notif_menu(targets, nr)
    return


def __prompt_pre_config_selection() -> Optional[Dict]:
    title = "Select Notification Configuration Template or Custom"
    menu_items = [
        cli.menu_item(
            "Custom", "Build out a custom Notification Configuration", "custom"
        )
    ]
    for config in NOTIF_CONFIG_TEMPLATES:
        menu_items.append(
            cli.menu_item(
                config.display_name, config.description, config.config_values
            )
        )
    return cli.selection_menu(title, menu_items)


def __prompt_select_dst_type(nr: NotificationRoute):
    try:
        title = "Select a Destination for your Notifications"
        menu_items = []
        if nr.curr_dest:
            if nr.curr_dest == lib.NOTIF_DST_TGTS:
                curr_str = "Target(s)"
            else:
                curr_str = lib.DST_TYPE_TO_NAME[nr.curr_dest]
            menu_items.append(
                cli.menu_item(
                    f"Current (curr: {curr_str})",
                    "Use the current Destination type.",
                    nr.curr_dest,
                )
            )
        menu_items.append(
            cli.menu_item(
                "Target(s)",
                "Select one or more pre-configured destinations.",
                lib.NOTIF_DST_TGTS,
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
        return cli.selection_menu(title, menu_items)
    except KeyboardInterrupt:
        return None


def __prompt_nr_name(nr: NotificationRoute):
    try:
        while True:
            tgt_name = cli.input_window(
                "Name",
                "Provide a name for the Notification Configuration.",
                existing_data=nr.name,
                error_msg=lib.NOTIF_CONF_NAME_ERROR_MSG,
                validator=lib.is_valid_notification_name,
            )
            break
        return tgt_name
    except KeyboardInterrupt:
        return nr.name


def __prompt_schema_type(nr: NotificationRoute):
    title = "Select The Type of Record To Notify On"
    current = nr.schema
    menu_items = []
    if current:
        menu_items.append(
            cli.menu_item(
                "Current", f"The current schema type is {current}", current
            )
        )
    menu_items.extend(
        [
            cli.menu_item(
                "Operations Flags (event_opsflag)",
                "Events of interested related to operations.",
                "event_opsflag",
            ),
            cli.menu_item(
                "Red Flags (event_redflag)",
                "Event of interest related to security.",
                "event_redflag",
            ),
        ]
    )
    return cli.selection_menu(title, menu_items)


def __prompt_condition(nr: NotificationRoute):
    try:
        while True:
            condition = cli.input_window(
                "Condition",
                "Provide a condition for when this Configuration should emit Notifications.",
                existing_data=nr.condition,
            )
            break
        return condition
    except KeyboardInterrupt:
        return nr.condition


def __prompt_title(nr: NotificationRoute):
    try:
        while True:
            title = cli.input_window(
                "Title",
                "Provide a title for when notification are emitted. For email"
                " destinations this would be the subject line.",
                existing_data=nr.title,
            )
            if not title:
                return nr.title
            break
        return title
    except KeyboardInterrupt:
        return nr.title


def __prompt_message(nr: NotificationRoute) -> Optional[str]:
    MARKER = (
        "# Provide a message for the body of the notification.\n"
        "# If not provided, a message will be generated for you.\n"
        "# Everything above this line is ignored.\n"
    )
    prompt = MARKER + nr.message if nr.message else MARKER
    try:
        while True:
            resp = click.edit(prompt)
            if resp and MARKER not in resp:
                continue
            if not resp:
                return nr.message
            message = resp.split(MARKER, 1)[-1].strip(" \n")
            if not message:
                return nr.message
            return message
    except KeyboardInterrupt:
        return nr.message


def __i_edit_targets(targets: Dict, nr: NotificationRoute):
    title = "Configure Targets"
    sel = 0
    nr_targets = nr.targets.copy()
    while True:
        new_targets = set(nr_targets).difference(set(nr.targets))
        menu_items = [
            cli.menu_item(
                f"Add (curr: {len(new_targets)} new target(s))",
                "Add existing Target to this Notification Configuration",
                0,
            ),
            cli.menu_item(
                "Delete",
                "Delete Target from this Notification Configuration",
                1,
            ),
            cli.menu_item("View", "View pending Target list.", 2),
            cli.menu_item(
                "Cancel", "Return to previous menu without making changes.", 3
            ),
            cli.menu_item(
                "Done",
                f"Confirm adding {len(new_targets)} Target(s) to this Notification Configuration",
                4,
            ),
        ]
        sel = cli.selection_menu(title, menu_items, sel)
        if sel == 0:
            tgt_opts = set(targets) - set(nr_targets)
            tgt_name = nt.i_tgt_pick_menu(tgt_opts)
            if not tgt_name:
                cli.notice("No Target added.")
                continue
            nr_targets.append(tgt_name)
        elif sel == 1:
            tgt_name = nt.i_tgt_pick_menu(nr_targets)
            if not tgt_name:
                cli.notice("No Target deleted.")
            try:
                i = nr_targets.index(tgt_name)
                nr_targets.pop(i)
            except ValueError:
                pass
        elif sel == 2:
            click.echo_via_pager(yaml.dump(nr_targets))
        elif sel == 3:
            return
        elif sel == 4:
            if (
                new_targets or set(nr_targets) != set(nr.targets)
            ) and cli.query_yes_no(
                "Are you sure you want update Targets for this Notification"
                " Configuration?"
            ):
                nr.update(
                    destination={
                        lib.NOTIF_DST_TGTS: {name: None for name in nr_targets}
                    }
                )
            return


def __i_notif_menu(targets, nr: NotificationRoute):
    if nr.new:
        apply_desc = "Save new Notification Configuration."
    else:
        apply_desc = "Save changes to current Notification Configuration."
    title = "Notification Configuration Menu"
    sel = 0
    while True:
        menu_items = [
            cli.menu_item(
                f"Set Name (curr: {nr.name})",
                "Update the Notification Configuration's name.",
                0,
            ),
            cli.menu_item(
                f"Set Destination (curr: {nr.dst_name})",
                "Update existing destination or change the type entirely.",
                1,
            ),
            cli.menu_item(
                "Run Prompts",
                "Re-run through creation prompts to set values.",
                2,
            ),
            cli.menu_item("Edit", "Manually edit the Configuration YAML.", 3),
            cli.menu_item("View", "View the Configuration YAML.", 4),
            cli.menu_item(
                "Cancel", "Return to Main Menu without making changes.", 5
            ),
            cli.menu_item("Apply", apply_desc, 6),
        ]
        sel = cli.selection_menu(title, menu_items, sel)
        if sel == 0:
            name = __prompt_nr_name(nr)
            if not name:
                cli.notice("No changes made.")
                continue
            nr.update(name=name)
        elif sel == 1:
            dst_type = __prompt_select_dst_type(nr)
            if not dst_type:
                cli.notice("No changes made.")
                continue
            if dst_type == lib.NOTIF_DST_TGTS:
                __i_edit_targets(targets, nr)
                if not nr.targets:
                    continue
            else:
                dst_data = nt.get_dst_data(
                    dst_type, nr.get_notify_data(dst_type)
                )
                if not dst_data:
                    continue
                nr.update(destination={dst_type: dst_data})
        elif sel == 2:
            __i_create_notification(targets, nr)
        elif sel == 3:
            while True:
                edits = click.edit(yaml.dump(nr.settings), extension=".yaml")
                if edits:
                    try:
                        edits = yaml.load(edits, lib.UniqueKeyLoader)
                    except Exception as e:
                        cli.notice(f"Unable to load yaml. {e}")
                        continue
                    if not schemas.valid_object(
                        edits, allow_obj_list=False, interactive=True
                    ):
                        continue
                    nr = NotificationRoute(edits)
                    nr.set_last_updated(time.time())
                else:
                    cli.notice("No edits made.")
                break
        elif sel == 4:
            click.echo_via_pager(yaml.dump(nr.settings))
        elif sel == 5 or sel is None:
            if not nr.changed or cli.query_yes_no(
                "Are you sure you want to discard all changes?", "no"
            ):
                return
        elif sel == 6:
            if not nr.changed:
                return None
            if cli.query_yes_no("Are you sure you want to apply changes?"):
                return nr


def __i_notif_pick_menu(routes) -> str:
    options = []
    for route in routes:
        data = route.get(lib.DATA_FIELD)
        if not data:
            continue
        name = data.get(lib.NOTIF_NAME_FIELD)
        id = data.get(lib.ID_FIELD)
        if not id:
            continue
        if name:
            option = f"{name} - {id}"
        else:
            option = f"{id}"
        options.append(option)
    options.sort()
    menu = __build_notif_pick_menu(options)
    sel = menu.show()
    if sel == 0 or sel is None:
        return None
    else:
        return options[sel - 1].split(" - ")[-1]


def __put_and_get_notif_pol(
    nr: NotificationRoute = None, delete_id: str = None
):
    ctx = cfg.get_current_context()
    n_pol = api.get_notification_policy(*ctx.get_api_data())
    routes: List = n_pol.get(lib.ROUTES_FIELD, [])
    if delete_id:
        for i, route in list(enumerate(routes)):
            rt_id = route.get(lib.DATA_FIELD, {}).get(lib.ID_FIELD)
            if not rt_id:
                continue
            if rt_id == delete_id:
                routes.pop(i)
                break
    if nr:
        found = False
        for i, route in list(enumerate(routes)):
            rt_id = route.get(lib.DATA_FIELD, {}).get(lib.ID_FIELD)
            if not rt_id:
                continue
            if rt_id == nr.id:
                found = True
                routes[i] = nr.route
                break
        if not found:
            routes.append(nr.route)
    n_pol[lib.ROUTES_FIELD] = routes
    api.put_notification_policy(*ctx.get_api_data(), n_pol)
    n_pol = api.get_notification_policy(*ctx.get_api_data())
    return n_pol


def __build_notif_pick_menu(options: List):
    menu_cursor = "> "
    cursor_style = ("fg_red", "bold")
    menu_style = ("bg_red", "fg_yellow")
    menu_title = (
        "  Select A Target.\n  Press Q or Esc to back to main menu. \n"
    )
    menu_items = ["Back", *options]
    add_tgt_menu = TerminalMenu(
        menu_items,
        title=menu_title,
        menu_cursor=menu_cursor,
        menu_cursor_style=cursor_style,
        menu_highlight_style=menu_style,
        cycle_cursor=True,
        clear_screen=True,
    )
    return add_tgt_menu


def __build_id_index(routes: List[Dict]) -> Dict:
    rv = {}
    for i, route in enumerate(routes):
        id = route.get(lib.DATA_FIELD, {}).get(lib.ID_FIELD)
        if not id:
            continue
        rv[id] = i
    return rv
