import time
from copy import deepcopy
from typing import Dict, List, Optional

from tabulate import tabulate

import spyctl.api as api
import spyctl.cli as cli
import spyctl.config.configs as cfg
import spyctl.resources.notification_config_templates as nct
import spyctl.spyctl_lib as lib

NOTIFICATIONS_HEADERS = [
    "NAME",
    "ID",
    "TYPE",
    "TARGET",
    "STATUS",
    "AGE",
]

NOTIF_CONFIG_TMPL_HEADERS = [
    "NAME",
    "ID",
    "TYPE",
    "SCHEMA_TYPE",
    "DESCRIPTION",
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
        lib.NOTIF_DEFAULT_SCHEMA: "",
        lib.NOTIF_CONDITION_FIELD: "",
        lib.NOTIF_TITLE_FIELD: "",
        lib.NOTIF_MESSAGE_FIELD: "",
        lib.NOTIF_TEMPLATE_FIELD: "CUSTOM",
        lib.NOTIF_TARGET_FIELD: "",
        lib.NOTIF_ADDITIONAL_FIELDS: {},
    },
}


class NotificationConfig:
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
      title: "Agent Offline"
      message: "Detected {{ ref.id }} offline at {{ time }}."
      target: TARGET_NAME
      template: TEMPLATE_NAME
      additionalFields:
        slack_icon: ":large_green_circle:"
    """

    # Default config type is "object" but custom type can
    # be determined by schema type such as "metrics"
    config_types = {"event_metric": lib.NOTIF_TYPE_METRICS}

    def __init__(self, config_resource: Dict = None) -> None:
        if not config_resource:
            config_resource = deepcopy(DEFAULT_NOTIFICATION_CONFIG)
        meta: Dict = config_resource[lib.METADATA_FIELD]
        spec: Dict = config_resource[lib.SPEC_FIELD]
        if lib.METADATA_UID_FIELD not in meta:
            self.id = "notif:" + lib.make_uuid()
            meta[lib.METADATA_UID_FIELD] = self.id
            self.new = True
            self.create_time = None
            self.last_updated = None
        else:
            self.id = meta[lib.METADATA_UID_FIELD]
            self.new = False
            self.create_time = meta.get(lib.NOTIF_CREATE_TIME, None)
            self.last_updated = meta.get(lib.NOTIF_LAST_UPDATED, None)
        self.changed = False
        self.name = meta.get(lib.NAME_FIELD, "")
        self.enabled = spec.get(lib.ENABLED_FIELD, True)
        self.schema_type = spec.get(lib.NOTIF_DEFAULT_SCHEMA, "")
        self.sub_schema = spec.get(lib.NOTIF_SUB_SCHEMA)
        self.condition = spec.get(lib.NOTIF_CONDITION_FIELD, "")
        self.title = spec.get(lib.NOTIF_TITLE_FIELD)
        self.message = spec.get(lib.NOTIF_MESSAGE_FIELD)
        self.target = spec.get(lib.NOTIF_TARGET_FIELD, "")
        self.template = spec.get(lib.NOTIF_TEMPLATE_FIELD, "")
        self.additional_fields = spec.get(lib.NOTIF_ADDITIONAL_FIELDS, {})
        self.cooldown = spec.get(lib.NOTIF_COOLDOWN_FIELD)
        self.for_duration = spec.get(lib.NOTIF_FOR_DURATION_FIELD)

    def update(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if hasattr(self, key) and getattr(self, key) != value:
                self.changed = True
                setattr(self, key, value)

    def set_last_updated(self):
        now = time.time()
        self.last_updated = now
        if not self.create_time:
            self.create_time = now

    def as_dict(self) -> Dict:
        rv = {
            lib.API_FIELD: lib.API_VERSION,
            lib.KIND_FIELD: lib.NOTIFICATION_KIND,
            lib.METADATA_FIELD: {
                lib.METADATA_UID_FIELD: self.id,
                lib.METADATA_NAME_FIELD: self.name,
                lib.METADATA_TYPE_FIELD: self.config_type(self.schema_type),
            },
            lib.SPEC_FIELD: {
                lib.ENABLED_FIELD: self.enabled,
                lib.NOTIF_DEFAULT_SCHEMA: self.schema_type,
                lib.NOTIF_CONDITION_FIELD: self.condition,
                lib.NOTIF_TARGET_FIELD: self.target,
                lib.NOTIF_TITLE_FIELD: self.title,
                lib.NOTIF_MESSAGE_FIELD: self.message,
                lib.NOTIF_TEMPLATE_FIELD: self.template,
                lib.NOTIF_ADDITIONAL_FIELDS: self.additional_fields,
            },
        }
        if self.for_duration is not None:
            rv[lib.SPEC_FIELD][
                lib.NOTIF_FOR_DURATION_FIELD
            ] = self.for_duration
        if self.cooldown is not None:
            rv[lib.SPEC_FIELD][lib.NOTIF_COOLDOWN_FIELD] = self.cooldown
        if self.sub_schema is not None:
            rv[lib.SPEC_FIELD][lib.NOTIF_SUB_SCHEMA] = self.sub_schema
        if self.create_time:
            rv[lib.METADATA_FIELD][lib.NOTIF_CREATE_TIME] = self.create_time
            rv[lib.METADATA_FIELD][lib.NOTIF_LAST_UPDATED] = self.last_updated
        return rv

    @property
    def route(self) -> Dict:
        rv = {}
        if isinstance(self.target, str):
            targets = [self.target]
        else:
            targets = self.target
        rv[lib.TARGETS_FIELD] = targets
        rv[lib.DATA_FIELD] = {
            lib.NOTIF_CREATE_TIME: self.create_time,
            lib.ID_FIELD: self.id,
            lib.NOTIF_LAST_UPDATED: self.last_updated,
            lib.NOTIF_SETTINGS_FIELD: self.as_dict(),
            lib.NOTIF_NAME_FIELD: self.name,
        }
        rv[lib.ROUTE_EXPR] = {"property": "data.route_id", "equals": self.id}
        return rv

    @property
    def type(self) -> str:
        return self.config_type(self.schema_type)

    @classmethod
    def config_type(cls, schema_type: str):
        if schema_type in cls.config_types:
            return cls.config_types[schema_type]
        else:
            return lib.NOTIF_TYPE_OBJECT


class NotificationConfigTemplate:
    def __init__(self, config_template: Dict) -> None:
        self.display_name = config_template["display_name"]
        self.description = config_template["description"]
        self.config_values = config_template["config"]
        self.id = config_template["id"]
        self.type = config_template["type"]

    def update_rt(self, rt: NotificationConfig):
        for key in rt.settings[lib.SPEC_FIELD]:
            if key in self.pre_conf_fields:
                rt.update(**{key: self.pre_conf_fields[key]})

    def as_dict(self):
        rv = {
            lib.API_FIELD: lib.API_VERSION,
            lib.KIND_FIELD: lib.NOTIF_TMPL_KIND,
            lib.METADATA_FIELD: {
                lib.METADATA_NAME_FIELD: self.display_name,
                lib.METADATA_UID_FIELD: self.id,
                lib.METADATA_TYPE_FIELD: self.type,
            },
            lib.SPEC_FIELD: {
                lib.TMPL_DESCRIPTION_FIELD: self.description,
                lib.TMPL_CONFIG_VALUES_FIELD: self.config_values,
            },
        }
        return rv


def __load_notif_configs() -> List[NotificationConfigTemplate]:
    rv = []
    for config in nct.TEMPLATES:
        rv.append(NotificationConfigTemplate(config))
    return rv


NOTIF_CONFIG_TEMPLATES: List[
    NotificationConfigTemplate
] = __load_notif_configs()


def notif_config_tmpl_summary_output(
    templates: List[NotificationConfigTemplate],
):
    data = []
    for tmpl in templates:
        data.append(
            [
                tmpl.display_name,
                tmpl.id,
                tmpl.type,
                tmpl.config_values["schema_type"],
                __wrap_text(tmpl.description, 45),
            ]
        )
    data.sort(key=lambda row: row[2])
    return tabulate(data, NOTIF_CONFIG_TMPL_HEADERS, "plain")


def __wrap_text(text, max_line_length=30) -> str:
    lines = text.split("\n")
    wrapped_lines = []

    for line in lines:
        while len(line) > max_line_length:
            # Find the last space within the max_line_length
            last_space = line.rfind(" ", 0, max_line_length)
            if last_space == -1:
                # If no space is found, split the line at max_line_length
                last_space = max_line_length

            # Append the portion of the line up to the last space to the result
            wrapped_lines.append(line[:last_space])
            # Remove the portion that was added to the result
            last_space_plus_one = last_space + 1
            line = line[last_space_plus_one:]

        # Append the remaining portion of the line to the result
        wrapped_lines.append(line)

    return "\n".join(wrapped_lines)


def notifications_summary_output(routes: Dict, notif_type: str):
    data = []
    if (
        notif_type == lib.NOTIF_TYPE_ALL
        or notif_type == lib.NOTIF_TYPE_DASHBOARD
    ):
        dashboard_search_notifications = __parse_legacy_notifications(routes)
        if dashboard_search_notifications:
            data.extend(__get_dashboard_data(dashboard_search_notifications))
    notif_configs = __parse_notification_configs(routes)
    if notif_type != lib.NOTIF_TYPE_ALL:
        notif_configs = list(
            filter(lambda cfg: cfg.type == notif_type, notif_configs)
        )
    data.extend(__get_config_data(notif_configs))
    data.sort(key=lambda row: (row[2], row[0]))
    return tabulate(data, NOTIFICATIONS_HEADERS, "plain")


def notifications_wide_output(routes: Dict, notif_type: str):
    data = []
    if (
        notif_type == lib.NOTIF_TYPE_ALL
        or notif_type == lib.NOTIF_TYPE_DASHBOARD
    ):
        dashboard_search_notifications = __parse_legacy_notifications(routes)
        if dashboard_search_notifications:
            data.extend(
                __get_dashboard_data_wide(dashboard_search_notifications)
            )
    notif_configs = __parse_notification_configs(routes)
    if notif_type != lib.NOTIF_TYPE_ALL:
        notif_configs = list(
            filter(lambda cfg: cfg.type == notif_type, notif_configs)
        )
    data.extend(__get_config_data_wide(notif_configs))
    data.sort(key=lambda row: (row[2], row[0]))
    return tabulate(data, NOTIFICATIONS_HEADERS, "plain")


def __parse_notification_configs(routes: Dict) -> List[NotificationConfig]:
    rv = []
    for route in routes:
        if __is_notification_config(route):
            config = NotificationConfig(
                route[lib.DATA_FIELD][lib.NOTIF_SETTINGS_FIELD]
            )
            rv.append(config)
    return rv


def __parse_legacy_notifications(routes: Dict):
    rv = []
    if not isinstance(routes, list):
        return rv
    for route in routes:
        if __is_dashboard_notification(route):
            rv.append(route)
    return rv


def __is_notification_config(route: Dict) -> bool:
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


def __get_config_data(configs: List[NotificationConfig]):
    table_rows = []
    for config in configs:
        if isinstance(config.target, list):
            if len(config.target) == 1:
                target = config.target[0]
            else:
                target = f"{len(config.target)} targets"
        else:
            target = config.target
        status = "Enabled" if config.enabled else "Disabled"
        table_rows.append(
            [
                config.name,
                config.id,
                config.type,
                target,
                status,
                lib.calc_age(config.create_time),
            ]
        )
    return table_rows


def __get_config_data_wide(configs: List[NotificationConfig]):
    table_rows = []
    for config in configs:
        if isinstance(config.target, list):
            if len(config.target) == 1:
                target = config.target[0]
            else:
                target = "\n".join(config.target)
        else:
            target = config.target
        status = "Enabled" if config.enabled else "Disabled"
        table_rows.append(
            [
                config.name,
                config.id,
                config.type,
                target,
                status,
                lib.calc_age(config.create_time),
            ]
        )
    return table_rows


def __get_dashboard_data(routes: List[Dict]):
    table_rows = []
    for route in routes:
        targets = route.get(lib.TARGETS_FIELD)
        if targets:
            if len(targets) == 1:
                target = targets[0]
            else:
                target = f"{len(targets)} targets"
        else:
            target = lib.NOT_AVAILABLE
        data = route.get(lib.DATA_FIELD, {})
        if isinstance(data, dict):
            id = data.get(lib.ID_FIELD, lib.NOT_AVAILABLE)
            name = data.get(lib.NAME_FIELD, lib.NOT_AVAILABLE)
            create_time = data.get(lib.NOTIF_CREATE_TIME)
            if create_time:
                age = lib.calc_age(create_time)
            else:
                age = lib.NOT_AVAILABLE
        else:
            id = lib.NOT_AVAILABLE
            name = lib.NOT_AVAILABLE
            age = lib.NOT_AVAILABLE
        table_rows.append(
            [
                name,
                id,
                lib.NOTIF_TYPE_DASHBOARD,
                target,
                "Enabled",
                age,
            ]
        )
    return table_rows


def __get_dashboard_data_wide(routes: List[Dict]):
    table_rows = []
    for route in routes:
        targets = route.get(lib.TARGETS_FIELD)
        if targets:
            if len(targets) == 1:
                target = targets[0]
            else:
                target = "\n".join(targets)
        else:
            target = lib.NOT_AVAILABLE
        data = route.get(lib.DATA_FIELD, {})
        if isinstance(data, dict):
            id = data.get(lib.ID_FIELD, lib.NOT_AVAILABLE)
            name = data.get(lib.NAME_FIELD, lib.NOT_AVAILABLE)
            create_time = data.get(lib.NOTIF_CREATE_TIME)
            if create_time:
                age = lib.calc_age(create_time)
            else:
                age = lib.NOT_AVAILABLE
        else:
            id = lib.NOT_AVAILABLE
            name = lib.NOT_AVAILABLE
            age = lib.NOT_AVAILABLE
        table_rows.append(
            [
                name,
                id,
                lib.NOTIF_TYPE_DASHBOARD,
                target,
                "Enabled",
                age,
            ]
        )
    return table_rows


def create_config(name, tgt_name_or_id, tmpl_name_or_id):
    import spyctl.resources.notification_targets as nt

    config = NotificationConfig()
    target: nt.NotificationTarget = nt.get_target(tgt_name_or_id)
    if not target:
        cli.err_exit(f'No target with name or uid "{tgt_name_or_id}"')
    if tmpl_name_or_id != "CUSTOM":
        template = get_template(tmpl_name_or_id)
    else:
        template = tmpl_name_or_id
    if not template:
        cli.err_exit(f'No template with name or uid "{tmpl_name_or_id}"')
    if template == "CUSTOM":
        config.update(template="CUSTOM")
    else:
        config.update(template=template.display_name)
        config.update(**template.config_values)
    config.update(target=target.name)
    config.update(name=name)
    return config.as_dict()


def get_template(name_or_id) -> Optional[NotificationConfigTemplate]:
    for tmpl in NOTIF_CONFIG_TEMPLATES:
        if name_or_id == tmpl.display_name or name_or_id == tmpl.id:
            return tmpl


def put_and_get_notif_pol(
    nr: NotificationConfig = None, delete_id: str = None
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
