import spyctl.api as api
import spyctl.cli as cli
import spyctl.config.configs as cfg
import spyctl.spyctl_lib as lib
import spyctl.resources.notification_targets as nt


def handle_test_notification(test_targets=[]):
    if not test_targets:
        cli.err_exit("No targets provided.")
    ctx = cfg.get_current_context()
    notif_pol = api.get_notification_policy(*ctx.get_api_data())
    if not notif_pol or not notif_pol.get(lib.TARGETS_FIELD):
        cli.err_exit(
            "No targets to test. Use 'spyctl create notification-target'."
        )
    pol_targets = notif_pol.get(lib.TARGETS_FIELD)
    if not pol_targets:
        cli.err_exit("No targets to test.")
    for name_or_id in test_targets:
        test_target = None
        # check if name exists
        if name_or_id in pol_targets:
            tgt_data = pol_targets[name_or_id]
            test_target = nt.Target(backend_target={name_or_id: tgt_data})
        if not test_target:
            for tgt_name, tgt in pol_targets.items():
                id = tgt.get(lib.DATA_FIELD, {}).get(lib.ID_FIELD)
                if id is None:
                    continue
                if id == name_or_id:
                    test_target = nt.Target(backend_target={tgt_name: tgt})
                    break
        if not test_target:
            cli.err_exit(f"No notification targets matching '{name_or_id}'.")
        resp = api.post_test_notification(
            *ctx.get_api_data(), test_target.name
        )
        if resp.status_code == 200:
            cli.try_log(f"Successfully sent test to '{test_target.name}'")
