import spyctl.api as api
import spyctl.cli as cli
import spyctl.config.configs as cfg
import spyctl.config.secrets as s
import spyctl.resources.policies as p
import spyctl.spyctl_lib as lib


def handle_delete(resource, name_or_id):
    if resource == lib.POLICIES_RESOURCE:
        handle_delete_policy(name_or_id)
    else:
        cli.err_exit(f"The 'delete' command is not supported for {resource}")


def del_policy_input(args) -> p.Policy:
    policies = cli.policy_input([args.policy_file])
    if len(policies) > 1:
        cli.err_exit(
            "multiple policies provided; only one policy allowed to be deleted"
            " at a time"
        )
    elif len(policies) == 0:
        cli.err_exit("No policies inputted, exiting")
    return policies[0]


def handle_delete_policy(uid, yes=False):
    ctx = cfg.get_current_context()
    if yes:
        perform_delete = True
    else:
        perform_delete = cli.query_yes_no(
            f"Are you sure you want to delete policy {uid} from Spyderbat?"
        )
    if perform_delete:
        api.delete_policy(
            *ctx.get_api_data(),
            uid,
        )
        cli.try_log(f"Successfully deleted policy {uid}")
