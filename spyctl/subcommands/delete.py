import spyctl.api as api
import spyctl.cli as cli
import spyctl.resources.policies as p
import spyctl.config.configs as u_conf
import spyctl.config.secrets as s
import spyctl.spyctl_lib as lib


def handle_delete(resource, name_or_id):
    if resource == lib.SECRETS_RESOURCE:
        s.delete_secret(name_or_id)


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


def handle_delete_policy(args):
    uid = args.uid
    if uid is None:
        uid = del_policy_input(args).get_uid()
    if uid is None:
        cli.err_exit("No uid found")
    if args.yes:
        perform_delete = True
    else:
        perform_delete = cli.query_yes_no(
            f"Are you sure you want to delete policy {uid} from Spyderbat?"
        )
    if perform_delete:
        api.delete_policy(
            *u_conf.read_config(),
            uid,
        )
