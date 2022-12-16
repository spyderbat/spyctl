import spyctl.cli as cli
import spyctl.resources.policies as p
import spyctl.api as api
import spyctl.config.configs as u_conf


def upload_policy_input(args) -> p.Policy:
    policies = cli.policy_input([args.file])
    if len(policies) > 1:
        cli.err_exit(
            "multiple policies provided; only one policy allowed to be"
            " uploaded at a time"
        )
    elif len(policies) == 0:
        cli.err_exit("No policies inputted, exiting")
    return policies[0]


def handle_upload_policy(args):
    policy = upload_policy_input(args)
    arg_uid = args.uid
    uid, data = policy.get_data_for_api_call()
    if arg_uid is not None and uid is not None and arg_uid != uid:
        cli.try_log(
            "Warning: argument-provided uid & metadata uid mismatch, using"
            " argument-provided uid"
        )
    req_uid = arg_uid or uid
    if req_uid is None:
        # We are uploading a new policy
        api.post_new_policy(*u_conf.read_config(), data, cli.api_err_exit)
    else:
        if args.yes:
            perform_update = True
        else:
            perform_update = cli.query_yes_no(
                f"Are you sure you want to update policy {req_uid}?"
            )
        if perform_update:
            # We are attempting to update an existing policy
            api.put_policy_update(
                *u_conf.read_config(), req_uid, data, cli.api_err_exit
            )
