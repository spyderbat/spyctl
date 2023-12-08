import spyctl.api as api
import spyctl.cli as cli
import spyctl.config.configs as cfg
import spyctl.spyctl_lib as lib


def handle_test_notification(target_names=[]):
    if not target_names:
        cli.err_exit("No targets provided.")
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
