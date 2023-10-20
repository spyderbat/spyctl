import spyctl.api as api
import spyctl.cli as cli
import spyctl.config.configs as cfg
import spyctl.spyctl_lib as lib
import spyctl.filter_resource as filt
import spyctl.resources.notification_targets as nt


def handle_test_notification(target_names=[], route_ids=[]):
    if not target_names and not route_ids:
        cli.err_exit("No targets or routes provided.")
    ctx = cfg.get_current_context()
    notif_pol = api.get_notification_policy(*ctx.get_api_data())
    if not notif_pol or not notif_pol.get(lib.TARGETS_FIELD):
        cli.err_exit(
            "No targets to test. Use 'spyctl create notification-target'."
        )
    pol_targets = notif_pol[lib.TARGETS_FIELD]
    if target_names:
        for target_name in target_names:
            if target_name not in pol_targets:
                cli.try_log(
                    f"Target '{target_name}' is not in the notification policy.. skipping.",
                    is_warning=True,
                )
                continue
            resp = api.post_test_notification(*ctx.get_api_data(), target_name)
            if resp.status_code == 200:
                cli.try_log(f"Successfully sent test to '{target_name}'")
    if not route_ids:
        return
    pol_routes = notif_pol.get(lib.ROUTES_FIELD)
    if not pol_routes:
        cli.err_exit("No routes to send test notifications to.")
    for route_id in route_ids:
        route = None
        for p_route in pol_routes:
            if route.get(lib.ROUTE_DATA, {}).get(lib.ID_FIELD) == route_id:
                route = p_route
        if not route:
            cli.try_log(
                f"Route with ID '{route_id}' is not in the notification policy.. skipping."
            )
            continue
        r_targets = route.get(lib.ROUTE_TARGETS)
        if not r_targets:
            cli.try_log(f"Route '{route_id}' has no targets.. skipping.")
        for target_name in r_targets:
            resp = api.post_test_notification(*ctx.get_api_data(), target_name)
            if resp.status_code == 200:
                cli.try_log(
                    f"Successfully sent test to '{target_name}' in route '{route_id}'"
                )
