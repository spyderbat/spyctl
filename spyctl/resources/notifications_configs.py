import time
from copy import deepcopy
from typing import Callable, Dict, List, Optional

import click
import urwid as u
import yaml
from tabulate import tabulate

import spyctl.api as api
import spyctl.cli as cli
import spyctl.config.configs as cfg
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
        - slack:
            url: https://…
        - targets:
            admin_email:
            admin_slack:
      additionalFields:
        slack_icon: ":large_green_circle:"
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
            if key == "additional_fields" and value != self.additional_fields:
                self.changed = True
                self.settings[lib.SPEC_FIELD][
                    lib.NOTIF_ADDITIONAL_FIELDS
                ] = value
            elif key == "name" and value != self.name:
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
    def additional_fields(self) -> Dict:
        return self.settings[lib.SPEC_FIELD].get(
            lib.NOTIF_ADDITIONAL_FIELDS, {}
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
    data.sort(key=lambda row: (row[1], row[0]))
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
    shortcut_map = {
        "create": 0,
        "edit": 1,
        "delete": 2,
    }
    if shortcut is not None:
        shortcut = shortcut_map[shortcut]
    app = InteractiveNotifications(notif_policy, shortcut)
    app.start()


def put_and_get_notif_pol(nr: NotificationRoute = None, delete_id: str = None):
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


class InteractiveNotifications:
    return_footer = " Q to return"

    MAIN_MENU_ITEMS = [
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

    def __init__(self, notif_pol: Dict, shortcut) -> None:
        self.notif_pol = notif_pol
        self.loop = u.MainLoop(
            u.Filler(u.Text("")),
            cli.URWID_PALLET,
            unhandled_input=self.unhandled_input,
        )
        self.menu_stack = []
        self.show_main_menu(shortcut=shortcut)

    @property
    def targets(self):
        return self.notif_pol.get(lib.TARGETS_FIELD, {})

    @property
    def routes(self):
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

    def push_update(self, nr: NotificationRoute, delete_id=None):
        self.loop.stop()
        self.notif_pol = put_and_get_notif_pol(nr, delete_id)
        self.loop.start()

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
        title = "Notification Configurations Main Menu"
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
            self.show_config_sel_menu(self.handle_edit_config)
        elif sel == 2:
            self.show_config_sel_menu(self.handle_delete_config)
        elif sel == 3:
            self.show_pager(
                notifications_summary_output(self.routes, lib.NOTIF_TYPE_ALL)
            )
        elif sel == 4 or sel is None:
            self.quit()

    # ----------------------------------------------------------
    # Notification Config Management Menu
    # ----------------------------------------------------------
    def show_config_mgmt_menu(self, nr: NotificationRoute, selected=0):
        title = "Notification Configuration Menu"
        frame = cli.selection_menu_v2(
            title,
            self.__build_notif_mgmt_menu_items(nr),
            selected,
            self.return_footer,
            lambda sel: self.handle_config_mgmt_selection(nr, sel),
        )
        self.sub_menu(frame)

    def handle_config_mgmt_selection(self, nr: NotificationRoute, sel: int):
        def update_nr(new_nr: NotificationRoute):
            self.pop_menu()
            new_nr.changed = nr.changed
            self.show_config_mgmt_menu(new_nr, sel)

        def update_settings(new_settings: Dict):
            self.pop_menu()
            new_nr = NotificationRoute(new_settings)
            new_nr.changed = nr.changed
            self.show_config_mgmt_menu(new_nr, sel)

        def edit_settings_yaml():
            self.edit_yaml(nr.get_settings(), invalid_edit, update_settings)

        def invalid_edit(error: str):
            self.show_pager(error, edit_settings_yaml)

        def show_get_dst_data(dst_type: str):
            if dst_type == lib.NOTIF_DST_TGTS:
                self.show_targets_mgmt_menu(nr, lambda: update_nr(nr))
            else:
                self.get_dst_data_prompts(nr, dst_type, lambda: update_nr(nr))

        def should_quit_menu(should_quit: bool):
            self.pop_menu()
            if should_quit:
                self.pop_menu()
                self.show_pager("No changes made.")

        def should_apply_config(should_apply: bool):
            self.pop_menu()
            if should_apply:
                self.pop_menu()
                del_id = nr.id if not nr.new else None
                self.push_update(nr, del_id)

        def stay(**_):
            self.pop_menu()

        if sel == 0:
            self.show_edit_name_prompt(nr, lambda: update_nr(nr))
        elif sel == 1:
            self.show_select_dst_type(nr, show_get_dst_data)
        elif sel == 2:
            self.show_additional_fields_menu(nr, lambda: update_nr(nr))
        elif sel == 3:
            self.start_creation_prompts(nr, update_nr)
        elif sel == 4:
            edit_settings_yaml()
        elif sel == 5:
            self.show_pager(yaml.dump(nr.get_settings()))
        elif sel == 6 or None:
            if nr.changed:
                query = "Are you sure you want to discard all changes?"
                frame = cli.urwid_query_yes_no(
                    query, should_quit_menu, stay, "no"
                )
                self.sub_menu(frame)
            else:
                self.pop_menu()
                self.show_pager("No changes made.")
        elif sel == 7:
            if nr.changed:
                query = "Are you sure you want to apply changes?"
                frame = cli.urwid_query_yes_no(
                    query, should_apply_config, stay, "yes"
                )
                self.sub_menu(frame)
            else:
                self.pop_menu()
                self.show_pager("No changes made.")

    # ----------------------------------------------------------
    # Select Notification Config Menu
    # ----------------------------------------------------------
    def show_config_sel_menu(self, handler: callable):
        menu_items = self.__build_notif_sel_menu_items()
        title = "Select A Notification Config"
        frame = cli.extended_selection_menu(
            title,
            menu_items,
            self.return_footer,
            handler,
        )
        self.sub_menu(frame)

    def handle_edit_config(self, config_id):
        self.pop_menu()
        route = self.__get_route(config_id)
        if route:
            config = route.get(lib.DATA_FIELD, {}).get(
                lib.NOTIF_SETTINGS_FIELD
            )
            if config:
                config = deepcopy(config)
                self.show_config_mgmt_menu(NotificationRoute(config))

    def handle_delete_config(self, config_id):
        name = None

        def confirm_delete(should_delete=False):
            nonlocal name
            self.pop_menu()
            if should_delete:
                self.pop_menu()
                self.push_update(None, config_id)
                self.show_pager(f"Deleted config '{name}'.")
            else:
                self.pop_menu()
                self.show_pager("No config deleted.")

        def cancel(**_):
            self.pop_menu()
            self.show_pager("No config deleted.")

        route = self.__get_route(config_id)
        if route:
            settings = route.get(lib.DATA_FIELD, {}).get(
                lib.NOTIF_SETTINGS_FIELD
            )
            if settings:
                nr = NotificationRoute(settings)
                name = f"{nr.name} | {config_id}"
            else:
                name = config_id
            query = f"Are you sure you want to delete config '{name}'"
            frame = cli.urwid_query_yes_no(
                query, confirm_delete, cancel, default="no"
            )
            self.sub_menu(frame)
        else:
            self.pop_menu()
            self.show_pager("No config deleted.")

    # ----------------------------------------------------------
    # Notification Config Additional Fields
    # ----------------------------------------------------------
    def show_additional_fields_menu(
        self, nr: NotificationRoute, next_func: Callable
    ):
        fields = deepcopy(nr.additional_fields)
        title = "Manage Additional Config Fields"
        menu_items = self.__build_additional_fields_menu_items()
        frame = cli.selection_menu_v2(
            title,
            menu_items,
            0,
            self.return_footer,
            lambda sel: self.handle_additional_fields_menu_selection(
                nr, sel, next_func
            ),
        )
        self.sub_menu(frame, fields)

    def handle_additional_fields_menu_selection(
        self, nr: NotificationRoute, sel: int, next_func: Callable
    ):
        fields = self.curr_menu_data
        if sel == 0:
            self.show_additional_fields(nr, self.show_set_field_value)
        if sel == 1:
            self.show_additional_fields(nr, self.handle_delete_field)
        if sel == 2:
            self.show_pager(yaml.dump({lib.NOTIF_ADDITIONAL_FIELDS: fields}))
        if sel == 3:
            self.pop_menu()
        if sel == 4:
            self.pop_menu()
            nr.update(additional_fields=fields)
            next_func()

    def show_additional_fields(self, nr: NotificationRoute, handler: Callable):
        title = "Select a field to set"
        menu_items = self.__build_additional_fields_options()
        frame = cli.selection_menu_v2(
            title,
            menu_items,
            0,
            self.return_footer,
            lambda field: self.handle_additional_field_selection(
                nr, field, handler
            ),
        )
        self.sub_menu(frame)

    def handle_additional_field_selection(
        self, nr: NotificationRoute, field: str, handler: Callable
    ):
        self.pop_menu()
        handler(nr, field)

    def show_set_field_value(self, nr: NotificationRoute, field: str):
        curr_value = nr.additional_fields.get(field, "")
        frame = cli.urwid_prompt(
            "Value",
            f"Set value for additional field {field}",
            lambda value: self.handle_set_field_value(nr, field, False, value),
            lambda value: self.handle_set_field_value(nr, field, True, value),
            curr_value,
        )
        self.sub_menu(frame)

    def handle_set_field_value(
        self, nr: NotificationRoute, field: str, cancel: bool, value: str
    ):
        self.pop_menu()
        fields = self.curr_menu_data
        if cancel:
            return
        fields[field] = value

    def handle_delete_field(self, nr: NotificationRoute, field: str):
        fields: Dict = self.curr_menu_data
        fields.pop(field, None)

    # ----------------------------------------------------------
    # Notification Config Creation Prompts
    # ----------------------------------------------------------
    def start_creation_prompts(
        self, nr: NotificationRoute = None, next_func: Callable = None
    ):
        def show_select_dst_type():
            self.show_select_dst_type(nr, show_get_dst_data)

        def show_get_dst_data(dst_type: str):
            if dst_type == lib.NOTIF_DST_TGTS:
                self.show_targets_mgmt_menu(nr, show_name_prompt)
            else:
                self.get_dst_data_prompts(nr, dst_type, show_name_prompt)

        def show_name_prompt():
            self.show_edit_name_prompt(nr, show_select_schema_type)

        def show_select_schema_type():
            nonlocal new
            if new and nr.schema:
                show_condition_prompt()
            else:
                self.show_select_schema_type_menu(nr, show_condition_prompt)

        def show_condition_prompt():
            nonlocal new
            if new and nr.condition:
                show_title_prompt()
            else:
                self.show_set_condition_prompt(nr, show_title_prompt)

        def show_title_prompt():
            self.show_set_title_prompt(nr, show_message_prompt)

        def show_message_prompt():
            if next_func:
                self.show_set_message_prompt(nr, lambda: next_func(nr))
            else:
                self.show_set_message_prompt(
                    nr, lambda: self.show_config_mgmt_menu(nr)
                )

        if not nr:
            new = True
            nr = NotificationRoute(deepcopy(DEFAULT_NOTIFICATION_CONFIG))
            self.show_config_template_options(nr, show_select_dst_type)
        else:
            new = False
            nr = deepcopy(nr)
            self.show_select_dst_type(nr, show_get_dst_data)

    # ----------------------------------------------------------
    # Select Notification Config Template Menu (Creation Prompt)
    # ----------------------------------------------------------
    def show_config_template_options(
        self, nr: NotificationRoute, next_func: Callable = None
    ):
        title = "Select Notification Configuration Template or Custom"
        menu_items = [
            cli.menu_item(
                "Custom",
                "Build out a custom Notification Configuration",
                "custom",
            )
        ]
        for config in NOTIF_CONFIG_TEMPLATES:
            menu_items.append(
                cli.menu_item(
                    config.display_name,
                    config.description,
                    config.config_values,
                )
            )
        frame = cli.selection_menu_v2(
            title,
            menu_items,
            0,
            self.return_footer,
            lambda tmpl: self.handle_template_sel(nr, tmpl, next_func),
        )
        self.sub_menu(frame)

    def handle_template_sel(
        self, nr: NotificationRoute, template, next_func: Callable = None
    ):
        self.pop_menu()
        if template is None:
            return
        elif template != "custom":
            nr.update(**template)
        if next_func:
            next_func()

    # ----------------------------------------------------------
    # Select Dst Type (Creation Prompt)
    # ----------------------------------------------------------
    def show_select_dst_type(self, nr: NotificationRoute, next_menu: Callable):
        title = "Select a Destination Type for your Notifications"
        frame = cli.selection_menu_v2(
            title,
            self.__build_dst_type_menu_items(nr),
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
    # Select Target Menu
    # ----------------------------------------------------------
    def show_select_tgt_menu(
        self, targets: List[str], nr_targets: List[str], handler: Callable
    ):
        title = "Select A Target"
        targets.sort()
        menu_items = []
        for name in targets:
            tgt_data: Dict = self.targets[name]
            dst_type = next(iter(tgt_data))
            menu_items.append(
                cli.menu_item(
                    f"{name} ({lib.DST_TYPE_TO_NAME[dst_type]})", "", name
                )
            )
        frame = cli.extended_selection_menu(
            title,
            menu_items,
            self.return_footer,
            lambda tgt_name: handler(tgt_name, nr_targets),
        )
        self.sub_menu(frame)

    def handle_selected_tgt(self, tgt: str, nr_targets: List):
        self.pop_menu()
        nr_targets.append(tgt)
        nr_targets.sort

    def handle_rm_tgt(self, tgt: str, nr_targets: List):
        self.pop_menu()
        nr_targets.pop(nr_targets.index(tgt))

    # ----------------------------------------------------------
    # Targets Management Menu
    # ----------------------------------------------------------
    def show_targets_mgmt_menu(
        self, nr: NotificationRoute, next_menu: Callable = None
    ):
        title = "Manage Destination Targets For this Config"
        frame = cli.selection_menu_v2(
            title,
            self.__build_tgt_mgmt_menu_items(self.targets, nr),
            0,
            self.return_footer,
            lambda sel: self.handle_targets_mgmt_menu(nr, sel, next_menu),
        )
        self.sub_menu(frame, nr.targets.copy())

    def handle_targets_mgmt_menu(
        self, nr: NotificationRoute, sel: int, next_menu: Callable = None
    ):
        nr_targets = self.curr_menu_data
        if sel == 0:
            available_tgts = list(set(self.targets) - set(nr_targets))
            self.show_select_tgt_menu(
                available_tgts, nr_targets, self.handle_selected_tgt
            )
        elif sel == 1:
            self.show_select_tgt_menu(
                nr_targets, nr_targets, self.handle_rm_tgt
            )
        elif sel == 2:
            self.show_pager(yaml.dump(nr_targets))
        elif sel == 3:
            self.pop_menu()
        elif sel == 4:
            self.pop_menu()
            nr.update(
                destination={
                    lib.NOTIF_DST_TGTS: {name: None for name in nr_targets}
                }
            )
            if next_menu:
                next_menu()

    # ----------------------------------------------------------
    # Get Dst Data Menus (Creation Prompt)
    # ----------------------------------------------------------
    def get_dst_data_prompts(
        self, nr: NotificationRoute, dst_type: str, next_menu: Callable = None
    ):
        def show_get_emails():
            self.show_get_emails_prompt(nr, next_menu)

        def show_get_slack_url():
            self.show_get_slack_url_prompt(nr, next_menu)

        def show_get_webhook_url():
            self.show_get_webhook_url(nr, show_get_tls_val)

        def show_get_tls_val():
            self.show_get_webhook_tls_validation(nr, next_menu)

        def show_get_sns_topic():
            self.show_get_sns_topic_arn(nr, show_get_cross_acct_role)

        def show_get_cross_acct_role():
            self.show_get_cross_acct_role(nr, next_menu)

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
        self, nr: NotificationRoute, next_menu: Callable = None
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

        if nr.dst_type == lib.DST_TYPE_EMAIL:
            curr_emails = "\n".join(nr.dst_data)
        else:
            curr_emails = ""
        frame = cli.urwid_multi_line_prompt(
            "Provide email addresses to send notifications to, 1 email per line:",
            lambda emails: self.handle_emails_input(
                nr, False, emails, next_menu
            ),
            lambda emails: self.handle_emails_input(
                nr, True, emails, next_menu
            ),
            curr_emails,
            validator=validate_emails,
        )
        self.sub_menu(frame)

    def handle_emails_input(
        self,
        nr: NotificationRoute,
        canceled: bool,
        emails: str,
        next_menu: Callable = None,
    ):
        self.pop_menu()
        if canceled:
            return
        emails = emails.splitlines()
        emails = [email.strip() for email in emails]
        nr.update(destination={lib.DST_TYPE_EMAIL: emails})
        if next_menu:
            next_menu()

    # Dst Data Slack
    def show_get_slack_url_prompt(
        self, nr: NotificationRoute, next_menu: Callable = None
    ):
        def validate_slack_hook(url: str):
            if not lib.is_valid_slack_url(url.strip()):
                return (
                    'URL must start with "https://hooks.slack.com/services/"'
                )

        if nr.dst_type == lib.DST_TYPE_SLACK:
            curr_url = nr.dst_data["url"]
        else:
            curr_url = ""
        frame = cli.urwid_prompt(
            "url",
            "Provide a Slack Hook URL (e.g. https://hooks.slack.com/services/xxxxxxxxxxx/xxxxxxxxxxx/xxxxxxxxxxxxxxxxxxxxxxxx)",
            lambda url: self.handle_slack_input(nr, False, url, next_menu),
            lambda url: self.handle_slack_input(nr, True, url, next_menu),
            curr_url,
            validator=validate_slack_hook,
        )
        self.sub_menu(frame)

    def handle_slack_input(
        self,
        nr: NotificationRoute,
        canceled: bool,
        url: str,
        next_menu: Callable,
    ):
        self.pop_menu()
        if canceled:
            return
        nr.update(destination={lib.DST_TYPE_SLACK: {"url": url.strip()}})
        if next_menu:
            next_menu()

    # Dst Data Webhook
    def show_get_webhook_url(
        self, nr: NotificationRoute, next_menu: Callable = None
    ):
        def validate_url(url: str):
            if not lib.is_valid_url(url.strip()):
                return f"'{url.strip()}' is not a valid URL."

        if nr.dst_type == lib.DST_TYPE_WEBHOOK:
            curr_url = nr.dst_data["url"]
        else:
            curr_url = ""
        frame = cli.urwid_prompt(
            "url",
            "Provide a webhook URL (e.g. https://my.webhook.example/location/of/webhook",
            lambda url: self.handle_webhook_url_input(
                nr, False, url, next_menu
            ),
            lambda url: self.handle_webhook_url_input(
                nr, True, url, next_menu
            ),
            curr_url,
            validator=validate_url,
        )
        self.sub_menu(frame)

    def handle_webhook_url_input(
        self, nr: NotificationRoute, canceled: bool, url: str, next_menu
    ):
        self.pop_menu()
        if canceled:
            return
        if nr.dst_type == lib.DST_TYPE_WEBHOOK:
            dst_data = deepcopy(nr.dst_data)
            dst_data["url"] = url.strip()
            nr.update(destination={lib.DST_TYPE_WEBHOOK: dst_data})
        else:
            nr.update(destination={lib.DST_TYPE_WEBHOOK: {"url": url.strip()}})
        if next_menu:
            next_menu()

    def show_get_webhook_tls_validation(
        self, nr: NotificationRoute, next_menu: Callable = None
    ):
        if nr.dst_type == lib.DST_TYPE_WEBHOOK:
            default = not nr.dst_data.get("no_tls_validation", True)
        else:
            default = False
        default = "yes" if default else "no"
        frame = cli.urwid_query_yes_no(
            "Would you like to perform TLS Validation on this webhook?",
            lambda resp: self.handle_tls_val_query(nr, resp, False, next_menu),
            lambda resp: self.handle_tls_val_query(nr, resp, True, next_menu),
            default,
        )
        self.sub_menu(frame)

    def handle_tls_val_query(
        self,
        nr: NotificationRoute,
        resp: bool,
        cancel,
        next_menu: Callable = None,
    ):
        self.pop_menu()
        if cancel:
            return
        dst_data = deepcopy(nr.dst_data)
        dst_data["no_tls_validation"] = not resp
        nr.update(destination={lib.DST_TYPE_WEBHOOK: dst_data})
        if next_menu:
            next_menu()

    # Dst Data SNS
    def show_get_sns_topic_arn(
        self, nr: NotificationRoute, next_menu: Callable = None
    ):
        if nr.dst_type == lib.DST_TYPE_SNS:
            curr_topic = nr.dst_data["sns_topic_arn"]
        else:
            curr_topic = ""
        description = "Provide an AWS SNS Topic ARN (e.g. arn:aws:sns:region:account-id:topic-name)"
        frame = cli.urwid_prompt(
            "Topic ARN",
            description,
            lambda topic_arn: self.handle_sns_topic_input(
                nr, topic_arn, False, next_menu
            ),
            lambda topic_arn: self.handle_sns_topic_input(
                nr, topic_arn, False, next_menu
            ),
            curr_topic,
        )
        self.sub_menu(frame)

    def handle_sns_topic_input(
        self,
        nr: NotificationRoute,
        topic_arn: str,
        cancel: bool,
        next_menu: Callable = None,
    ):
        self.pop_menu()
        if cancel:
            return
        if nr.dst_type == lib.DST_TYPE_SNS:
            dst_data = deepcopy(nr.dst_data)
            dst_data["sns_topic_arn"] = topic_arn
            nr.update(destination={lib.DST_TYPE_SNS: dst_data})
        else:
            nr.update(
                destination={lib.DST_TYPE_SNS: {"sns_topic_arn": topic_arn}}
            )
        if next_menu:
            next_menu()

    def show_get_cross_acct_role(
        self, nr: NotificationRoute, next_menu: Callable
    ):
        if nr.dst_type == lib.DST_TYPE_SNS:
            curr_role = nr.dst_data.get("cross_account_iam_role")
        else:
            curr_role = ""
        description = "Provide an AWS IAM Role ARN with cross-account permissions (e.g. arn:aws:iam::account-id:role/role-name)"
        frame = cli.urwid_prompt(
            "Role ARN",
            description,
            lambda role_arn: self.handle_iam_role_input(
                nr, role_arn, False, next_menu
            ),
            lambda role_arn: self.handle_iam_role_input(
                nr, role_arn, True, next_menu
            ),
            curr_role,
        )
        self.sub_menu(frame)

    def handle_iam_role_input(
        self,
        nr: NotificationRoute,
        role_arn: str,
        cancel: bool,
        next_menu: Callable = None,
    ):
        self.pop_menu()
        if cancel:
            return
        dst_data = deepcopy(nr.dst_data)
        dst_data["cross_account_iam_role"] = role_arn
        nr.update(destination={lib.DST_TYPE_SNS: dst_data})
        if next_menu:
            next_menu()

    # ----------------------------------------------------------
    # Set Notification Config Name (Creation Prompt)
    # ----------------------------------------------------------
    def show_edit_name_prompt(
        self, nr: NotificationRoute, next_menu: Callable = None
    ):
        def validate_name(tmp_name: str) -> str:
            if not lib.is_valid_notification_name(tmp_name):
                return lib.TGT_NAME_ERROR_MSG

        self.sub_menu(
            cli.urwid_prompt(
                "Name",
                "Provide a name for the Notification Config.",
                lambda name: self.handle_name_input(
                    nr, False, name, next_menu
                ),
                lambda name: self.handle_name_input(nr, True, name, next_menu),
                nr.name,
                validator=validate_name,
            )
        )

    def handle_name_input(
        self,
        nr: NotificationRoute,
        canceled: bool,
        name: str,
        next_menu: Callable = None,
    ):
        self.pop_menu()
        if canceled:
            return
        nr.update(name=name)
        if next_menu:
            next_menu()

    # ----------------------------------------------------------
    # Select Schema Type Menu (Creation Prompt)
    # ----------------------------------------------------------

    def show_select_schema_type_menu(
        self, nr: NotificationRoute, next_menu: Callable = None
    ):
        title = "Select The Type of Record To Notify On"
        frame = cli.selection_menu_v2(
            title,
            self.__build_schema_type_menu_items(nr),
            0,
            self.return_footer,
            lambda schema_type: self.handle_schema_type_selection(
                nr, schema_type, next_menu
            ),
        )
        self.sub_menu(frame)

    def handle_schema_type_selection(
        self, nr: NotificationRoute, schema_type, next_menu: Callable = None
    ):
        self.pop_menu()
        if schema_type is None:
            return
        nr.update(schema=schema_type)
        if next_menu:
            next_menu()

    # ----------------------------------------------------------
    # Set Condition (Creation Prompt)
    # ----------------------------------------------------------

    def show_set_condition_prompt(
        self, nr: NotificationRoute, next_menu: Callable = None
    ):
        def validate_condition(condition: str):
            return
            condition = condition.strip()
            ctx = cfg.get_current_context()
            try:
                error = api.validate_search_query(
                    *ctx.get_api_data(), nr.schema, condition
                )
                if error:
                    return error
            except Exception as e:
                return str(e)

        if nr.condition:
            curr_condition = nr.condition
        else:
            curr_condition = ""
        description = "Provide a condition for when this Configuration should emit Notifications. (Uses the search syntax defined here: PLACEHOLDER)"
        frame = cli.urwid_prompt(
            "Condition",
            description,
            lambda condition: self.handle_condition_input(
                nr, condition, False, next_menu
            ),
            lambda condition: self.handle_condition_input(
                nr, condition, True, next_menu
            ),
            curr_condition,
            validator=validate_condition,
        )
        self.sub_menu(frame)

    def handle_condition_input(
        self,
        nr: NotificationRoute,
        condition: str,
        cancel: bool,
        next_menu: Callable = None,
    ):
        condition = condition.strip()
        self.pop_menu()
        if cancel:
            return
        nr.update(condition=condition)
        if next_menu:
            next_menu()

    # ----------------------------------------------------------
    # Set Title (Creation Prompt)
    # ----------------------------------------------------------

    def show_set_title_prompt(
        self, nr: NotificationRoute, next_menu: Callable = None
    ):
        if nr.title:
            curr_title = nr.title
        else:
            curr_title = ""
        description = (
            "Provide a title for when notification are emitted. For email"
            " destinations this would be the subject line."
        )
        frame = cli.urwid_prompt(
            "Title",
            description,
            lambda title: self.handle_title_input(nr, title, False, next_menu),
            lambda title: self.handle_title_input(nr, title, True, next_menu),
            curr_title,
        )
        self.sub_menu(frame)

    def handle_title_input(
        self,
        nr: NotificationRoute,
        title: str,
        cancel: bool,
        next_menu: Callable = None,
    ):
        self.pop_menu()
        if cancel:
            return
        nr.update(title=title)
        if next_menu:
            next_menu()

    # ----------------------------------------------------------
    # Set Message (Creation Prompt)
    # ----------------------------------------------------------

    def show_set_message_prompt(
        self, nr: NotificationRoute, next_menu: Callable = None
    ):
        if nr.message:
            curr_message = nr.message
        else:
            curr_message = ""
        prompt = "Provide a message for the body of the notification. This would be the main content of an email or Slack message, etc."
        frame = cli.urwid_multi_line_prompt(
            prompt,
            lambda message: self.handle_message_input(
                nr, message, False, next_menu
            ),
            lambda message: self.handle_message_input(
                nr, message, True, next_menu
            ),
            curr_message,
        )
        self.sub_menu(frame)

    def handle_message_input(
        self,
        nr: NotificationRoute,
        message: str,
        cancel: bool,
        next_menu: Callable = None,
    ):
        self.pop_menu()
        if cancel:
            return
        nr.update(message=message)
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
                edits = yaml.load(edits, lib.UniqueKeyLoader)
            except Exception as e:
                error = f"Unable to load yaml. {e}"
                invalid_func(error)
                return
            error = schemas.valid_object(
                edits, allow_obj_list=False, interactive=True
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
    def __build_notif_sel_menu_items(self) -> List[cli.menu_item]:
        rv = [cli.menu_item("Back", "", None)]
        configs = []
        for route in self.routes:
            data = route.get(lib.DATA_FIELD)
            if not data:
                continue
            name = data.get(lib.NOTIF_NAME_FIELD)
            id = data.get(lib.ID_FIELD)
            if not id:
                continue
            if name:
                option = f"{name} | {id}"
            else:
                option = f"{id}"
            configs.append(cli.menu_item(option, "", id))
        configs.sort(key=lambda tup: tup[0])
        rv.extend(configs)
        return rv

    def __build_notif_mgmt_menu_items(self, nr: NotificationRoute):
        rv = [
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
                f"Additional Fields (curr: {len(nr.additional_fields)})",
                "Set or Clear additional fields like Slack icon or linkback.",
                2,
            ),
            cli.menu_item(
                "Run Prompts",
                "Re-run through creation prompts to set values.",
                3,
            ),
            cli.menu_item("Edit", "Manually edit the Configuration YAML.", 4),
            cli.menu_item("View", "View the Configuration YAML.", 5),
            cli.menu_item(
                "Cancel", "Return to Main Menu without making changes.", 6
            ),
            cli.menu_item("Apply", "Apply changes.", 7),
        ]
        return rv

    def __build_dst_type_menu_items(
        self, nr: NotificationRoute
    ) -> List[cli.menu_item]:
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
        return menu_items

    def __build_tgt_mgmt_menu_items(
        self, targets: Dict, nr: NotificationRoute
    ):
        rv = [
            cli.menu_item(
                "Add",
                "Add existing Target to this Notification Configuration",
                0,
            ),
            cli.menu_item(
                "Remove",
                "Remove Target from this Notification Configuration",
                1,
            ),
            cli.menu_item("View", "View pending Target list.", 2),
            cli.menu_item(
                "Cancel", "Return to previous menu without making changes.", 3
            ),
            cli.menu_item(
                "Done",
                "Confirm setting Target(s) for this Notification Config",
                4,
            ),
        ]
        return rv

    def __build_schema_type_menu_items(self, nr: NotificationRoute):
        rv = []
        current = nr.schema
        rv = []
        if current:
            rv.append(
                cli.menu_item(
                    "Current", f"The current schema type is {current}", current
                )
            )
        rv.extend(
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
        return rv

    def __build_additional_fields_menu_items(self):
        rv = [
            cli.menu_item(
                "Set Field",
                "Here you can set additional fields, such as slack icon or linkback url",
                0,
            ),
            cli.menu_item(
                "Clear Field", "Clear any fields that are currently set", 1
            ),
            cli.menu_item("View", "View all set fields", 2),
            cli.menu_item("Cancel", "Cancel any changes made.", 3),
            cli.menu_item(
                "Done", "Stage changes that will take effect when applied.", 4
            ),
        ]
        return rv

    def __build_additional_fields_options(self):
        rv = [
            cli.menu_item(
                "Slack Icon",
                "An icon that is included at the start of your slack notification",
                "slack_icon",
            ),
            cli.menu_item(
                "Linkback URL",
                'A link that may be included in your notification. If set to "{{ __linkback__ }}", Spyderbat will generate a relevant link to the Spyderbat Console.',
                "linkback_url",
            ),
            cli.menu_item(
                "Linkback Text",
                'This is the text to display for the linkback. Has no effect if "linkback_url" is not set.',
                "linkback_text",
            ),
        ]
        return rv

    def __get_route(self, id) -> Optional[Dict]:
        for route in self.routes:
            data: Dict = route.get(lib.DATA_FIELD, {})
            if data.get(lib.ID_FIELD) == id:
                return route
