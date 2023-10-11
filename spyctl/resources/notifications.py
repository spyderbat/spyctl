import spyctl.cli as cli
import spyctl.api as api
import spyctl.config.configs as cfg
import spyctl.spyctl_lib as lib
from tabulate import tabulate
from typing import Dict, List

NOTIFICATIONS_HEADERS = [
    "NAME",
    "TYPE",
    "TARGETS",
    "AGE",
]


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
    if notif_type == lib.NOTIF_TYPE_ALL or notif_type == lib.NOTIF_TYPE_AGENT:
        agent_health_notifications = __parse_agent_notifications(routes)
        if agent_health_notifications:
            data.extend(__make_agent_notif_table(agent_health_notifications))
    return tabulate(data, NOTIFICATIONS_HEADERS, "plain")


def __parse_agent_notifications(routes: Dict):
    rv = []
    for route in routes:
        if __is_agent_notification(route):
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


def __is_agent_notification(route: Dict) -> bool:
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
        notif_type = lib.get_metadata_type(settings)
        if notif_type == lib.NOTIF_TYPE_AGENT:
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


def __make_agent_notif_table(routes: List[Dict]):
    return ""


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
