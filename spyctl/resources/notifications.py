from copy import deepcopy
from typing import Dict, List, Optional
import time

import click
import yaml
from simple_term_menu import TerminalMenu
from tabulate import tabulate

import spyctl.api as api
import spyctl.cli as cli
import spyctl.config.configs as cfg
import spyctl.resources.notification_targets as nt
import spyctl.schemas_v2 as schemas
import spyctl.spyctl_lib as lib
from pathlib import Path

NOTIFICATIONS_HEADERS = [
    "NAME",
    "TYPE",
    "DESTINATIONS",
    "AGE",
]

DEFAULT_ANALYTICS_NOTIFICATION = {
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
        lib.NOTIF_INTERVAL_FIELD: 0,
        lib.NOTIF_TITLE_FIELD: None,
        lib.NOTIF_MESSAGE_FIELD: None,
        lib.NOTIF_NOTIFY_FIELD: [],
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
      schema: event_opsflag:agent_offline
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
        - target:
            admin_email:
            title: "Admin Notification: Agent Offline"
        - target:
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
        self.targets = []
        self.destination = None
        for dest in spec[lib.NOTIF_NOTIFY_FIELD]:
            if "target" in dest:
                self.targets.append(dest["target"])
            elif not self.destination:
                self.destination = dest
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
            elif key == "destination" and value != self.destination:
                self.changed = True
                self.destination = value
            elif key == "notify":
                self.changed = True
                self.settings[lib.SPEC_FIELD][lib.NOTIF_NOTIFY_FIELD] = value
                self.targets = []
                self.destination = None
                for dest in value:
                    if "target" in dest:
                        self.targets.append(list(dest["target"].keys())[0])
                    elif not self.destination:
                        self.destination = dest

    def add_destination(self, dst: Dict):
        self.changed = True
        dst_type, dst_settings = next(iter(dst.items()))
        if dst_type == "target":
            tgt_name, tgt_settings = next(iter(dst_settings.items()))
            match = False
            for i, name in list(enumerate(self.targets)):
                if tgt_name == name:
                    match = True
                    self.targets[i] = {tgt_name: tgt_settings}
                    break
            if not match:
                self.targets.append({tgt_name: tgt_settings})
        else:
            self.destination = dst
        self.settings[lib.SPEC_FIELD][lib.NOTIF_NOTIFY_FIELD] = [*self.targets]
        if self.destination:
            self.settings[lib.SPEC_FIELD][lib.NOTIF_NOTIFY_FIELD].append(
                self.destination
            )

    def update_target(self, index: int, target: Dict):
        if self.targets[index] != target:
            self.changed = True
            self.targets[index] = target

    def delete_target(self, index: int):
        self.changed = True
        self.targets.pop(index)

    def set_condition(self, condition: str):
        if (
            condition
            == self.settings[lib.SPEC_FIELD][lib.NOTIF_CONDITION_FIELD]
        ):
            return
        self.changed = True
        self.settings[lib.SPEC_FIELD][lib.NOTIF_CONDITION_FIELD] = condition

    def get_settings(self) -> Dict:
        rv = self.settings
        notify = [{"target": target} for target in self.targets]
        if self.destination:
            notify.append(self.destination)
        self.settings[lib.SPEC_FIELD][lib.NOTIF_NOTIFY_FIELD] = notify
        return rv

    @property
    def dst_count(self) -> int:
        settings = self.get_settings()
        return len(settings[lib.SPEC_FIELD].get(lib.NOTIF_NOTIFY_FIELD, []))

    @property
    def route(self) -> Dict:
        rv = {}
        if self.targets:
            rv[lib.TARGETS_FIELD] = [
                next(iter(target)) for target in self.targets
            ]
        if self.destination:
            rv["destination"] = self.destination
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


class NotificationConfig:
    def __init__(self, config: Dict) -> None:
        self.display_name = config["display_name"]
        self.description = config["description"]
        self.pre_conf_fields = config["config"]

    def update_rt(self, rt: NotificationRoute):
        for key in rt.settings[lib.SPEC_FIELD]:
            if key in self.pre_conf_fields:
                rt.update(**{key: self.pre_conf_fields[key]})


NOTIF_CONFIGS_LOC = Path("spyctl/resources/notification_configs.json")


def __load_notif_configs() -> List[NotificationConfig]:
    rv = []
    configs: List[Dict] = lib.load_file(NOTIF_CONFIGS_LOC)
    for config in configs:
        rv.append(NotificationConfig(config))
    return rv


NOTIF_CONFIGS: List[NotificationConfig] = __load_notif_configs()


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
        ).dst_count
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
                len(route[lib.TARGETS_FIELD]),
                age,
            ]
        )
    return table_rows


def interactive_notifications(
    notif_policy: Dict, shortcut=None, route_id=None
):
    routes: List[Dict] = notif_policy.get(lib.ROUTES_FIELD)
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
            nr = __interactive_create_notification(targets, routes)
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
                        routes,
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
            routes: List[Dict] = notif_policy.get(lib.ROUTES_FIELD)
            targets = notif_policy.get(lib.TARGETS_FIELD, {})


def x_interactive_notifications(
    notif_policy: Dict, shortcut=None, route_id=None
):
    notif_policy_copy = deepcopy(notif_policy)
    routes: List[Dict] = notif_policy_copy.get(lib.ROUTES_FIELD)
    targets = notif_policy_copy.get(lib.TARGETS_FIELD, {})
    main_menu = __build_main_menu()
    update_policy = False
    delete_id = None
    new_route_id = None
    new_route = None
    while True:
        id_index = __build_id_index(routes)
        main_sel = None
        if not shortcut:
            main_sel = main_menu.show()
        if main_sel == 0 or shortcut == "create":
            new_notif = __interactive_create_notification(
                targets, None, None, None
            )
            if new_notif:
                update_policy = True
                new_route_id = new_notif.id
                new_route = new_notif.route
        elif main_sel == 1 or shortcut == "edit":
            if route_id and route_id in id_index:
                sel_id = route_id
            else:
                sel_id = __i_notif_pick_menu(routes)
            if sel_id:
                index = id_index[sel_id]
                route = routes[index]
                if lib.NOTIF_SETTINGS_FIELD not in route.get(
                    lib.DATA_FIELD, {}
                ):
                    continue
                updated_notif = __i_notif_menu(
                    targets,
                    NotificationRoute(
                        route[lib.DATA_FIELD][lib.NOTIF_SETTINGS_FIELD]
                    ),
                )
                if updated_notif:
                    update_policy = True
                    new_route_id = updated_notif.id
                    new_route = updated_notif.route
        elif main_sel == 2 or shortcut == "delete":
            if route_id and route_id in id_index:
                sel_id = route_id
            else:
                sel_id = __i_notif_pick_menu(routes)
            if sel_id and cli.query_yes_no(
                f"Delete notification '{sel_id}'? This cannot be undone."
            ):
                update_policy = True
                delete_id = sel_id
        elif main_sel == 3:
            click.echo_via_pager(
                notifications_summary_output(routes, lib.NOTIF_TYPE_ALL)
            )
        elif main_sel == 4 or main_sel is None:
            return
        shortcut = None
        route_id = None
        if update_policy:
            update_policy = False
            notif_policy_copy = __put_and_get_notif_pol(
                new_route, new_route_id, delete_id
            )
            routes = notif_policy_copy.get(lib.ROUTES_FIELD, [])
            delete_id = None
            new_route = None
            new_route_id = None


def __interactive_create_notification(
    targets: Dict, routes: List[Dict], nr: NotificationRoute = None
) -> Optional[NotificationRoute]:
    pass


def x__interactive_create_notification(
    targets: Dict,
    notification: Dict = None,
    schema=None,
    condition=None,
):
    if notification is None:
        notification = deepcopy(DEFAULT_ANALYTICS_NOTIFICATION)
    route = NotificationRoute(notification)
    try:
        # Ask for destinations
        while True:
            if not route.dst_count:
                query = "Add a destination for the notification?"
            else:
                query = "Add another notification destination?"
            if not cli.query_yes_no(query):
                if not route.dst_count:
                    if cli.query_yes_no(
                        "Are you sure you want to discard this new notification?",
                        default="no",
                    ):
                        raise click.Abort
                    else:
                        continue
                break
            dst_type = __i_dst_pick_menu(route)
            if dst_type == "target":
                target_name = __i_tgt_pick_menu(targets)
                if not target_name:
                    continue
                route.add_destination({"target": {target_name: None}})
            elif dst_type:
                dst_data = nt.get_dst_data(dst_type)
                if not dst_data:
                    continue
                route.add_destination({dst_type: dst_data})
        # Ask for a Name
        name = __name_prompt()
        route.update(name=name)
        # Ask for a schema
        if not schema:
            schema = __schema_prompt()
        route.update(schema=schema)
        # Ask for a condition
        if not condition:
            condition = __condition_prompt()
        route.update(condition=condition)
        # Ask for a title
        title = __title_prompt()
        route.update(title=title)
        # Ask for a message
        message = __message_prompt()
        route.update(message=message)
        # Ask for an interval
        interval = __interval_prompt()
        route.update(interval=interval)
    except click.Abort:
        return None
    return __i_notif_menu(targets, route, True)


def __i_notif_menu(targets: Dict, route: NotificationRoute, new_notif=False):
    cursor_index = 0
    while True:
        menu = __build_notif_menu(cursor_index, route.route)
        sel = menu.show()
        if sel == 0:
            cursor_index = 0
            try:
                new_name = __name_prompt(route.name)
                route.update(name=new_name)
            except click.Abort:
                continue
        elif sel == 1:
            cursor_index = 1
            try:
                schema = __schema_prompt(route.schema)
                route.update(schema=schema)
            except click.Abort:
                continue
        elif sel == 2:
            cursor_index = 2
            try:
                condition = __condition_prompt(route.condition)
                route.update(condition=condition)
            except click.Abort:
                continue
        elif sel == 3:
            cursor_index = 3
            try:
                interval = __interval_prompt(route.interval)
                route.update(interval=interval)
            except click.Abort:
                continue
        elif sel == 4:
            cursor_index = 4
            try:
                title = __title_prompt()
                route.update(title=title)
            except click.Abort:
                continue
        elif sel == 5:
            cursor_index = 5
            try:
                message = __message_prompt(route.message)
                route.update(message=message)
            except click.Abort:
                continue
        elif sel == 6:
            cursor_index = 6
            dst_type = __i_dst_pick_menu()
            if not dst_type:
                continue
            if dst_type == "target":
                target_name = __i_tgt_pick_menu(targets)
                if not target_name:
                    continue
                route.add_destination({"target": {target_name: None}})
            else:
                dst_data = nt.get_dst_data(dst_type)
                if not dst_data:
                    continue
                route.add_destination({dst_type: dst_data})
        elif sel == 7:
            cursor_index = 7
            menu_items, helper_data = __notify_dst_pick_menu_items(route)
            notify_menu = __build_notify_dst_pick_menu(menu_items)
            notif_sel = notify_menu.show()
            if not notif_sel:
                continue
            else:
                data = helper_data[notif_sel - 1]
                ind, dst = next(iter(data.items()))
                if isinstance(ind, int):
                    target_name = __i_tgt_pick_menu(targets)
                    if not target_name:
                        continue
                    route.update_target(ind, {target_name: None})
                else:
                    dst_type, old_data = next(iter(dst.items()))
                    dst_data = nt.get_dst_data(dst_type, old_data)
                    route.update(destination={dst_type: dst_data})
        elif sel == 8:
            cursor_index = 8
            menu_items, helper_data = __notify_dst_pick_menu_items(route)
            notify_menu = __build_notify_dst_pick_menu(menu_items)
            notif_sel = notify_menu.show()
            if not notif_sel:
                continue
            else:
                data = helper_data[notif_sel - 1]
                ind, dst = next(iter(data.items()))
                if isinstance(ind, int):
                    route.delete_target(ind)
                else:
                    route.update(destination=None)
        elif sel == 9:
            cursor_index = 9
            if route.enabled:
                if cli.query_yes_no(
                    "Are you sure you want to disable this notification?"
                ):
                    route.update(enabled=False)
            else:
                if cli.query_yes_no(
                    "Are you sure you want to enable this notification?"
                ):
                    route.update(enabled=True)
        elif sel == 10:
            cursor_index = 10
            click.echo_via_pager(yaml.dump(route.get_settings()))
        elif sel == 11:
            cursor_index = 11
            if new_notif:
                query = (
                    "Are you sure you want to discard this new notification?"
                )
            elif route.changed:
                query = (
                    "Are you sure you want to discard updates to notification"
                    f" '{route.name} - {route.id}'"
                )
            else:
                return None
            if cli.query_yes_no(query):
                return None
            continue
        elif sel == 12:
            cursor_index = 12
            if new_notif:
                query = "Are you sure you want to apply this new notification?"
            elif route.changed:
                query = (
                    "Are you sure you want to update notification"
                    f" '{route.name} - {route.id}'"
                )
            else:
                cli.try_log("No changes to apply.")
            if cli.query_yes_no(query):
                return route
            continue


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


def __i_notif_config_menu():
    options = [c.display_name for c in NOTIF_CONFIGS]


def __i_tgt_pick_menu(targets: Dict) -> Optional[str]:
    target_names = sorted(list(targets))
    tgt_pick_menu = __build_tgt_pick_menu(target_names)
    tgt_pick_sel = tgt_pick_menu.show()
    if tgt_pick_sel == 0 or tgt_pick_sel is None:
        return None
    else:
        return target_names[tgt_pick_sel - 1]


def __i_dst_pick_menu(route: NotificationRoute) -> Optional[str]:
    title = "  Select a Notification Destination."
    if route.destination:
        title += (
            "\n  Adding another non-target destination will overwrite the\n"
            "  existing one. Only 1 non-target destination is allowed."
        )
    menu_items = ["Pre-configured Target", *lib.DST_NAMES]
    menu = __build_generic_menu(title, menu_items)
    sel = menu.show()
    if sel == 0:
        return "target"
    elif sel is None:
        return None
    else:
        return lib.get_dst_type(lib.DST_NAMES[sel - 1])


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


def __build_main_menu():
    main_menu_title = (
        "  Notifications Main Menu.\n  Press Q or Esc to exit. \n"
    )
    main_menu_items = [
        "Create Notification",
        "Edit Notification",
        "Delete Notification",
        "View Notifications",
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


def __build_notif_menu(cursor_index, notification: Dict):
    analytic_notif_setting = notification[lib.NOTIF_DATA_FIELD][
        lib.NOTIF_SETTINGS_FIELD
    ]
    menu_title = "  Notification Menu.\n  Press Q or Esc to exit. \n"
    meta = analytic_notif_setting[lib.METADATA_FIELD]
    spec = analytic_notif_setting[lib.SPEC_FIELD]
    name = meta[lib.METADATA_NAME_FIELD]
    schema = spec[lib.NOTIF_DEFAULT_SCHEMA]
    condition = __shorten_str(spec[lib.NOTIF_CONDITION_FIELD])
    interval = spec.get(lib.NOTIF_INTERVAL_FIELD)
    title = __shorten_str(spec.get(lib.NOTIF_TITLE_FIELD))
    message = __shorten_str(spec.get(lib.NOTIF_MESSAGE_FIELD))
    notify = spec[lib.NOTIF_NOTIFY_FIELD]
    enabled = spec.get(lib.ENABLED_FIELD, True)
    enable_str = "Disable" if enabled else "Enable"

    menu_items = [
        f"Set name{f' (curr: {name})' if name else ''}",
        f"Set schema{f' (curr: {schema})' if schema else ''}",
        f"Set condition{f' (curr: {condition})' if condition else ''}",
        f"Set interval{f' (curr: {interval})' if interval is not None else ''}",
        f"Set title{f' (curr: {title})' if title else ''}",
        f"Set message{f' (curr: {message})' if message else ''}",
        f"Add Notify Destination{f' (curr: {len(notify)})' if notify else ''}",
        f"Edit Notify Destination{f' (curr: {len(notify)})' if notify else ''}",
        f"Delete Notify Destination{f' (curr: {len(notify)})' if notify else ''}",
        f"{enable_str} Notification",
        "View notification",
        "Cancel",
        "Apply",
    ]
    menu_cursor = "> "
    menu_cursor_style = ("fg_red", "bold")
    menu_style = ("bg_red", "fg_yellow")
    main_menu = TerminalMenu(
        menu_entries=menu_items,
        title=menu_title,
        menu_cursor=menu_cursor,
        menu_cursor_style=menu_cursor_style,
        menu_highlight_style=menu_style,
        cycle_cursor=True,
        clear_screen=True,
        cursor_index=cursor_index,
    )
    return main_menu


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


def __build_dst_type_menu(dst_types: List):
    dst_pick_menu_title = ()

    menu_cursor = "> "
    menu_cursor_style = ("fg_red", "bold")
    menu_style = ("bg_red", "fg_yellow")
    rv = TerminalMenu(
        menu_entries=dst_pick_menu_items,
        title=dst_pick_menu_title,
        menu_cursor=menu_cursor,
        menu_cursor_style=menu_cursor_style,
        menu_highlight_style=menu_style,
        cycle_cursor=True,
        clear_screen=True,
    )
    return rv


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


def __notify_dst_pick_menu_items(route: NotificationRoute):
    rv: List[List, Dict] = [["Back"], []]
    items = rv[0]
    helper_data = rv[1]
    for i, tgt in enumerate(route.targets):
        items.append(next(iter(tgt)))
        helper_data.append({i: tgt})
    if route.destination:
        dst_type = next(iter(route.destination))
        items.append(dst_type)
        helper_data.append({lib.ROUTE_DESTINATION: route.destination})
    return rv


def __build_notify_dst_pick_menu(menu_items):
    menu_title = "  Pick a Destination.\n  Press Q or Esc to exit. \n"
    menu_cursor = "> "
    menu_cursor_style = ("fg_red", "bold")
    menu_style = ("bg_red", "fg_yellow")
    rv = TerminalMenu(
        menu_entries=menu_items,
        title=menu_title,
        menu_cursor=menu_cursor,
        menu_cursor_style=menu_cursor_style,
        menu_highlight_style=menu_style,
        cycle_cursor=True,
        clear_screen=True,
    )
    return rv


def __build_generic_menu(title, menu_items, can_cancel=True):
    menu_cursor = "> "
    menu_cursor_style = ("fg_red", "bold")
    menu_style = ("bg_red", "fg_yellow")
    if can_cancel:
        title += "\n  Press Q or Esc to exit. \n"
    rv = TerminalMenu(
        menu_entries=menu_items,
        title=title,
        menu_cursor=menu_cursor,
        menu_cursor_style=menu_cursor_style,
        menu_highlight_style=menu_style,
        cycle_cursor=True,
        clear_screen=True,
    )
    return rv


def __shorten_str(input, shorten_length: int = 10) -> str:
    if input is None:
        return None
    input = str(input)
    rv = input[:shorten_length]
    if len(input) > shorten_length:
        rv += "..."
    return rv


def __build_id_index(routes: List[Dict]) -> Dict:
    rv = {}
    for i, route in enumerate(routes):
        id = route.get(lib.DATA_FIELD, {}).get(lib.ID_FIELD)
        if not id:
            continue
        rv[id] = i
    return rv


def __name_prompt(default=None) -> str:
    name = click.prompt(
        "Provide a name for this notification",
        default=default,
        type=lib.valid_notification_name,
    )
    return name


def __schema_prompt() -> str:
    sel = None
    schema_types = ["event_opsflag"]
    while sel is None:
        menu = __build_generic_menu(
            "Select a schema type for the notification.\n"
            "This is the type of record that will be evaluated to trigger the"
            " notification.",
            schema_types,
            can_cancel=False,
        )
        sel = menu.show()
    return schema_types[sel]


def __condition_prompt(default=None) -> str:
    while True:
        condition = click.prompt("Provide a condition", default=default)
        try:
            # TODO add condition validation
            pass
        except ValueError as e:
            cli.try_log(*e.args, is_warning=True)
            continue
        break
    return condition


def __interval_prompt(default=None) -> int:
    interval = click.prompt(
        "Provide the interval.\n"
        "The interval is the minimum time in seconds between subsequent\n"
        "notifications. Notifications matching the condition will be\n"
        "aggregated in the interim.",
        default=0,
        type=int,
    )
    return interval


def __title_prompt() -> Optional[str]:
    title = click.prompt(
        "Provide a title for the notification record.\n"
        "This is equivalent to the subject line in an email.",
    )
    title = None if title == "__default__" else title
    return title


def __message_prompt(default=None) -> Optional[str]:
    MARKER = (
        "# Provide a message for the body of the notification.\n"
        "# If not provided, a message will be generated for you.\n"
        "# Everything above this line is ignored.\n"
    )
    prompt = MARKER + default if default else MARKER
    try:
        while True:
            resp = click.edit(prompt)
            if resp and MARKER not in resp:
                continue
            if not resp:
                return None
            message = resp.split(MARKER, 1)[-1].strip(" \n")
            if not message:
                return None
            return message
    except KeyboardInterrupt:
        raise click.Abort
