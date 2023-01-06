from typing import List

import spyctl.cli as cli
import spyctl.subcommands.delete as d
import spyctl.spyctl_lib as lib
import spyctl.resources.policies as p
import spyctl.subcommands.upload as upload


def manage_policy_input(args) -> p.Policy:
    policies = cli.policy_input([args.file])
    if len(policies) > 1:
        cli.try_log(
            "Warning: multiple policies provided, only considering first"
            " policy"
        )
    elif len(policies) == 0:
        cli.err_exit("No policies inputted, exiting")
    return policies[0]


def handle_manage_policy(args):
    cmd = args.pol_cmd
    if cmd == "add-response":
        handle_manage_add_resp(args)
    elif cmd == "enable":
        policy = manage_policy_input(args)
        policy.enable()
        cli.show(policy.get_output(), args)
    elif cmd == "disable":
        policy = manage_policy_input(args)
        policy.disable()
        cli.show(policy.get_output(), args)
    elif cmd == "upload":
        upload.handle_upload_policy(args)
    elif cmd == "delete":
        d.handle_delete_policy(args)


def handle_manage_add_resp(args):
    policy = manage_policy_input(args)
    resp_action = {}
    action_name = args.action
    resp_action[lib.RESP_ACTION_NAME_FIELD] = action_name
    if action_name == lib.ACTION_WEBHOOK:
        template = args.template
        if template is None:
            cli.err_exit(
                f"template required when action is '{lib.ACTION_WEBHOOK}'"
            )
        resp_action[lib.RESP_TEMPLATE_FIELD] = template
        url = args.url
        if url is None:
            cli.err_exit(f"url required when action is '{lib.ACTION_WEBHOOK}'")
        resp_action[lib.RESP_URL_FIELD] = url
    severity = args.severity
    if severity is not None:
        resp_action[lib.RESP_SEVERITY_FILED] = severity
    pod_labels = args.pod_labels
    if pod_labels is not None:
        resp_action[lib.POD_SELECTOR_FIELD] = {
            lib.MATCH_LABELS_FIELD: pod_labels
        }
    namespace_labels = args.namespace_labels
    if namespace_labels is not None:
        resp_action[lib.NAMESPACE_SELECTOR_FIELD] = {
            lib.MATCH_LABELS_FIELD: namespace_labels
        }
    policy.add_response_action(resp_action)
    cli.show(policy.get_output(), args)
