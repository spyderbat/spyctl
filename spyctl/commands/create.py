"""Handles the create subcommand group for spyctl."""

import time
from typing import IO, Dict, List, Optional, Tuple

import click

import spyctl.config.configs as cfg
import spyctl.resources as _r
import spyctl.spyctl_lib as lib
from spyctl import api, cli, search

# ----------------------------------------------------------------- #
#                         Create Subcommand                         #
# ----------------------------------------------------------------- #


@click.group("create", cls=lib.CustomSubGroup, epilog=lib.SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True)
def create():
    """Create a resource from a file."""


@create.command("cluster-policy", cls=lib.CustomCommand, epilog=lib.SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.option(
    "-n",
    "--name",
    help="Name for the Cluster Policy.",
    metavar="",
    required=True,
)
@click.option(
    "-o",
    "--output",
    default=lib.OUTPUT_DEFAULT,
    type=click.Choice(lib.OUTPUT_CHOICES, case_sensitive=False),
)
@click.option(
    "-m",
    "--mode",
    type=click.Choice(lib.POL_MODES),
    default=lib.POL_MODE_AUDIT,
    metavar="",
    help="This determines what the policy should do when applied and enabled."
    " Default is audit mode. Audit mode will generate log messages when a"
    " violation occurs and when it would have taken an action, but it will not"
    " actually take an action or generate a violation flag. Enforce mode"
    " will take actions, generate flags, and also generate audit events.",
    hidden=False,
)
@click.option(
    "-t",
    "--start-time",
    "st",
    help="Time to start generating statements from. Default is 1.5 hours ago.",
    default="1.5h",
    metavar="",
    type=lib.time_inp,
)
@click.option(
    "-e",
    "--end-time",
    "et",
    help="Time to stop generating statements from. Default is now.",
    default=time.time(),
    metavar="",
    type=lib.time_inp,
)
@click.option(
    "-g",
    "--no-ruleset-gen",
    "no_rs_gen",
    help="Does not generate rulesets for the cluster policies if set.",
    metavar="",
    is_flag=True,
)
@click.option(
    "-C",
    "--cluster",
    help="Name or Spyderbat ID of Kubernetes cluster.",
    metavar="",
    type=lib.ListParam(),
)
@click.option(
    "-N",
    "--namespace",
    is_flag=False,
    flag_value="__all__",
    default=None,
    metavar="",
    type=lib.ListParam(),
    help="Generate ruleset for all or some namespaces. If not provided, the"
    " ruleset will be generated for the cluster(s) without namespace"
    " context. Supplying this option with no arguments will generate the"
    " ruleset with namespace context. If one or more namespaces are supplied,"
    " the ruleset will generate for only the namespace(s) provided.",
)
def create_cluster_policy(
    name, output, mode, st, et, no_rs_gen, cluster, namespace
):
    """
    Create a Cluster Policy yaml document and accompanying rulesets, outputted to stdout  # noqa
    """
    handle_create_cluster_policy(
        name, mode, output, st, et, no_rs_gen, cluster, namespace
    )


@create.command(
    "notification-target", cls=lib.CustomCommand, epilog=lib.SUB_EPILOG
)
@click.help_option("-h", "--help", hidden=True)
@click.option(
    "-n",
    "--name",
    help="A name for the target. Used by other resources to refer to the"
    " configured target destination.",
    required=True,
)
@click.option(
    "-T",
    "--type",
    "tgt_type",
    required=True,
    type=click.Choice(lib.DST_TYPES, case_sensitive=False),
    help="The type of destination for the target.",
)
@click.option(
    "-o",
    "--output",
    default=lib.OUTPUT_DEFAULT,
    type=click.Choice(lib.OUTPUT_CHOICES, case_sensitive=False),
)
def create_notif_tgt(name, tgt_type, output):
    """Create a Notification Target resource outputted to stdout."""
    handle_create_notif_tgt(name, tgt_type, output)


@create.command(
    "notification-config", cls=lib.CustomCommand, epilog=lib.SUB_EPILOG
)
@click.help_option("-h", "--help", hidden=True)
@click.option(
    "-n", "--name", help="A name for the config.", metavar="", required=True
)
@click.option(
    "-T",
    "--target",
    help="The name or ID of a notification target. Tells the config where to"
    " send notifications.",
    metavar="",
    required=True,
)
@click.option(
    "-P",
    "--template",
    help="The name or ID of a notification configuration template."
    " If omitted, the config will be completely custom.",
    metavar="",
    default="CUSTOM",
)
@click.option(
    "-o",
    "--output",
    default=lib.OUTPUT_DEFAULT,
    type=click.Choice(lib.OUTPUT_CHOICES, case_sensitive=False),
)
def create_notif_route(name, target, template, output):
    """Create a Notification Config resource outputted to stdout."""
    handle_create_notif_config(name, target, template, output)


@create.command("policy", cls=lib.CustomCommand, epilog=lib.SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.option(
    "-f",
    "--from-file",
    "filename",
    help="File that contains the FingerprintsGroup or SpyderbatBaseline"
    " object, from which spyctl creates a Guardian Policy",
    metavar="",
    required=True,
    type=click.File(),
)
@click.option(
    "-o",
    "--output",
    default=lib.OUTPUT_DEFAULT,
    type=click.Choice(lib.OUTPUT_CHOICES, case_sensitive=False),
)
@click.option(
    "-n",
    "--name",
    help="Optional name for the Guardian Policy, if not provided, a name will"
    " be generated automatically",
    metavar="",
)
@click.option(
    "-d",
    "--disable-processes",
    "disable_procs",
    type=click.Choice(lib.DISABLE_PROCS_STRINGS),
    metavar="",
    hidden=False,
    help="Disable processes detections for this policy. Disabling all "
    "processes detections effectively turns this into a network policy.",
)
@click.option(
    "-D",
    "--disable-connections",
    "disable_conns",
    type=click.Choice(lib.DISABLE_CONN_OPTIONS_STRINGS),
    metavar="",
    help="Disable detections for all, public, or private connections.",
    hidden=False,
)
@click.option(
    "--include-imageid",
    help="Include the image id in the container selector when creating the"
    " policy.",
    metavar="",
    is_flag=True,
)
@click.option(
    "-m",
    "--mode",
    type=click.Choice(lib.POL_MODES),
    default=lib.POL_MODE_AUDIT,
    metavar="",
    help="This determines what the policy should do when applied and enabled."
    " Default is audit mode. Audit mode will generate log messages when a"
    " violation occurs and when it would have taken an action, but it will not"
    " actually take an action or generate a violation flag. Enforce mode"
    " will take actions, generate flags, and also generate audit events.",
    hidden=False,
)
@click.option(
    "-a",
    "--api",
    "use_api",
    metavar="",
    default=False,
    hidden=True,
    is_flag=True,
)
@lib.colorization_option
def create_policy(
    filename,
    output,
    name,
    colorize,
    mode,
    disable_procs,
    disable_conns,
    use_api,
    include_imageid,
):
    """Create a Guardian Policy object from a file, outputted to stdout"""
    if not colorize:
        lib.disable_colorization()
    handle_create_guardian_policy(
        filename,
        output,
        name,
        mode,
        disable_procs,
        disable_conns,
        use_api,
        include_imageid,
    )


@create.command(
    "cluster-ruleset", cls=lib.CustomCommand, epilog=lib.SUB_EPILOG
)
@click.help_option("-h", "--help", hidden=True)
@click.option(
    "-o",
    "--output",
    default=lib.OUTPUT_DEFAULT,
    type=click.Choice(lib.OUTPUT_CHOICES, case_sensitive=False),
)
@click.option(
    "-n",
    "--name",
    help="Optional name for the Cluster Ruleset, if not provided, a name will"
    " be generated automatically",
    metavar="",
)
@click.option(
    "-g",
    "--generate-rules",
    help="Generate all or some types of rules for the policy ruleset.",
    metavar="",
    is_flag=True,
)
@click.option(
    "-t",
    "--start-time",
    "st",
    help="Time to start generating statements from. Default is 1.5 hours ago.",
    default="1.5h",
    metavar="",
    type=lib.time_inp,
)
@click.option(
    "-e",
    "--end-time",
    "et",
    help="Time to stop generating statements from. Default is now.",
    default=time.time(),
    metavar="",
    type=lib.time_inp,
)
@click.option(
    "-C",
    "--cluster",
    help="Name or Spyderbat ID of Kubernetes cluster.",
    metavar="",
)
@click.option(
    "-N",
    "--namespace",
    is_flag=False,
    flag_value="__all__",
    default=None,
    metavar="",
    type=lib.ListParam(),
    help="Generate ruleset for all or some namespaces. If not provided, the"
    " ruleset will be generated for the cluster without namespace"
    " context. Supplying this option with no arguments will generate the"
    " ruleset with namespace context. If one or more namespaces are supplied,"
    " the ruleset will generate for only the namespace(s) provided.",
)
def create_policy_ruleset(output, name, generate_rules, st, et, **filters):
    """Create a Policy Rule to be used in cluster policies."""
    filters = {
        key: value for key, value in filters.items() if value is not None
    }
    handle_create_cluster_ruleset(
        output, name, generate_rules, (st, et), **filters
    )


class SuppressionPolicyCommand(lib.ArgumentParametersCommand):
    """
    Class contains options specific to creating the different types of
    Suppression Policies
    """

    argument_name = "type"
    argument_value_parameters = [
        {
            "type": [lib.POL_TYPE_TRACE],
            "args": [
                click.option(
                    f"--{lib.SUP_POL_CMD_TRIG_ANCESTORS}",
                    help="Scope the policy to Spydertraces with these"
                    " ancestors from trigger. This option will overwrite"
                    f" any auto-generated {lib.TRIGGER_ANCESTORS_FIELD} values"
                    " generated using '--id'",
                    metavar="",
                    type=lib.ListParam(),
                ),
                click.option(
                    f"--{lib.SUP_POL_CMD_TRIG_CLASS}",
                    help="Scope the policy to Spydertraces with these"
                    " trigger classes. This option will overwrite"
                    f" any auto-generated {lib.TRIGGER_CLASS_FIELD} values"
                    " generated using '--id'",
                    metavar="",
                    type=lib.ListParam(),
                ),
                click.option(
                    f"--{lib.SUP_POL_CMD_INT_USERS}",
                    help="Scope the policy to Spydertraces with these"
                    " interactive users. This option will overwrite"
                    f" any auto-generated {lib.USERS_FIELD} values generated"
                    " using '--id'",
                    metavar="",
                    type=lib.ListParam(),
                ),
                click.option(
                    f"--{lib.SUP_POL_CMD_N_INT_USERS}",
                    help="Scope the policy to Spydertraces with these"
                    " non-interactive users. This option will overwrite"
                    f" any auto-generated {lib.USERS_FIELD} values generated"
                    " using '--id'",
                    metavar="",
                    type=lib.ListParam(),
                ),
            ],
        },
    ]


@create.command(
    "suppression-policy",
    cls=SuppressionPolicyCommand,
    epilog=lib.SUB_EPILOG,
)
@click.help_option("-h", "--help", hidden=True)
@click.argument("type", type=lib.SuppressionPolTypeParam())
@click.option(
    "-i",
    "--id",
    "trace_id",
    default=None,
    help="UID of the object to build a Suppression Policy from.",
    metavar="",
)
@click.option(
    "-o",
    "--output",
    default=lib.OUTPUT_DEFAULT,
    type=click.Choice(lib.OUTPUT_CHOICES, case_sensitive=False),
)
@click.option(
    "-u",
    "--auto-generate-user-scope",
    "include_users",
    help=f"Auto generate the {lib.USERS_FIELD} in the"
    f" suppression policies {lib.USER_SELECTOR_FIELD} if"
    "'--id' is provided.",
    default=False,
    is_flag=True,
    metavar="",
)
@click.option(
    "-n",
    "--name",
    help="Optional name for the Suppression Policy, if not provided, a name"
    " will be generated automatically",
    metavar="",
)
@click.option(
    "-m",
    "--mode",
    type=click.Choice(lib.POL_MODES),
    default=lib.POL_MODE_AUDIT,
    metavar="",
    help="This determines what the policy should do when applied and enabled."
    " Default is audit mode. Audit mode will generate log messages when a"
    " an object matches the policy and would be suppressed, but it will not"
    " suppress the object. Enforce mode actually suppress the object if it"
    " matches the policy.",
    hidden=False,
)
@click.option(
    f"--{lib.SUP_POL_CMD_USERS}",
    help="Scope the policy to these users. This option will overwrite"
    f" any auto-generated {lib.USERS_FIELD} values generated"
    " using '--id'",
    metavar="",
    type=lib.ListParam(),
)
@click.option(
    "-a",
    "--api",
    "use_api",
    metavar="",
    default=False,
    hidden=True,
    is_flag=True,
)
@lib.tmp_context_options
@lib.colorization_option
def create_suppression_policy(
    type,
    trace_id,
    include_users,
    output,
    name,
    colorize,
    mode,
    use_api,
    **selectors,
):
    """Create a Suppression Policy object from a file, outputted to stdout"""
    if not colorize:
        lib.disable_colorization()
    selectors = {
        key: value for key, value in selectors.items() if value is not None
    }
    org_uid = selectors.pop(lib.CMD_ORG_FIELD, None)
    api_key = selectors.pop(lib.API_KEY_FIELD, None)
    api_url = selectors.pop(lib.API_URL_FIELD, "https://api.spyderbat.com")
    if org_uid and api_key and api_url:
        cfg.use_temp_secret_and_context(org_uid, api_key, api_url)
    handle_create_suppression_policy(
        type, trace_id, include_users, output, mode, name, use_api, **selectors
    )


# ----------------------------------------------------------------- #
#                         Create Handlers                           #
# ----------------------------------------------------------------- #


def handle_create_cluster_policy(
    name: str,
    mode: str,
    output: str,
    st: float,
    et: float,
    no_rs_gen: bool,
    cluster: str = None,
    namespace: List[str] = None,
):
    """
    Handles the creation of a cluster policy.

    Args:
        name (str): The name of the cluster policy.
        mode (str): The mode of the cluster policy.
        output (str): The output format of the policy.
        st (float): The start time to gather data for the policy rulesets.
        et (float): The end time to gather data for the policy rulesets.
        no_rs_gen (bool): Flag indicating whether to generate ruleset(s) for
            the policy.
        cluster (str, optional): The cluster to apply the policy to.
            Defaults to None.
        namespace (List[str], optional): The namespaces to apply the policy to.
            Defaults to None.
    """
    policy = _r.cluster_policies.create_cluster_policy(
        name, mode, st, et, no_rs_gen, cluster, namespace
    )
    if output == lib.OUTPUT_DEFAULT:
        output = lib.OUTPUT_YAML
    cli.show(policy, output)


def handle_create_guardian_policy(
    file: IO,
    output: str,
    name: str,
    mode: str,
    disable_procs: str,
    disable_conns: str,
    do_api=False,
    include_imageid=False,
):
    """
    Handles the creation of a guardian policy.

    Args:
        file (IO): The input file containing the policy data.
        output (str): The desired output format for displaying the policy.
        name (str): The name of the policy.
        mode (str): The mode of the policy.
        disable_procs (str): The flag indicating whether to disable processes.
        disable_conns (str): The flag indicating whether to disable
            connections.
        do_api (bool, optional): Flag indicating whether to use the API for
            policy creation. Defaults to False.

    Returns:
        None
    """
    if do_api:
        ctx = cfg.get_current_context()
        resrc_data = lib.load_file_for_api_test(file)
        policy = api.api_create_guardian_policy(
            *ctx.get_api_data(), name, mode, resrc_data
        )
        cli.show(policy, lib.OUTPUT_RAW)
    else:
        policy = create_guardian_policy_from_file(
            file, name, mode, disable_procs, disable_conns, include_imageid
        )
        if output == lib.OUTPUT_DEFAULT:
            output = lib.OUTPUT_YAML
        cli.show(policy, output)


def create_guardian_policy_from_file(
    file: IO,
    name: str,
    mode: str,
    disable_procs: str,
    disable_conns: str,
    include_imageid: bool = False,
):
    """
    Create a Guardian policy from a file.

    Args:
        file (IO): The file object containing the resource data.
        name (str): The name of the policy.
        mode (str): The mode of the policy.
        disable_procs (str): The processes to disable.
        disable_conns (str): The connections to disable.

    Returns:
        policy: The created Guardian policy.
    """
    resrc_data = lib.load_resource_file(file)
    policy = _r.policies.create_policy(
        resrc_data,
        name=name,
        mode=mode,
        disable_procs=disable_procs,
        disable_conns=disable_conns,
        include_imageid=include_imageid,
    )
    return policy


def create_guardian_policy_from_json(
    name: str,
    mode: str,
    input_objects: List[Dict],
    ctx: cfg.Context,
    include_imageid: bool = False,
):
    """
    Create a Guardian policy from JSON.

    Args:
        name (str): The name of the policy.
        mode (str): The mode of the policy.
        input_objects (List[Dict]): A list of input objects in JSON format.
        ctx (cfg.Context): The context for the policy.

    Returns:
        The created Guardian policy.
    """
    policy = _r.policies.create_policy(
        input_objects,
        mode=mode,
        name=name,
        ctx=ctx,
        include_imageid=include_imageid,
    )
    return policy


def handle_create_suppression_policy(
    pol_type: str,
    trace_id: Optional[str],
    include_users: bool,
    output: str,
    mode: str,
    name: str = None,
    do_api: bool = False,
    **selectors,
):
    """
    Handles the creation of a suppression policy.

    Args:
        pol_type (str): The type of suppression policy.
        trace_id (Optional[str]): The ID of the suppression policy.
        include_users (bool): Flag indicating whether to include user scope in
            the suppression policy.
        output (str): The output format for the suppression policy.
        mode (str): The mode of the suppression policy.
        name (str, optional): The name of the suppression policy.
            Defaults to None.
        do_api (bool, optional): Flag indicating whether to use the API for
            creating the suppression policy. Defaults to False.
        **selectors: Additional selectors for the suppression policy.

    Returns:
        None
    """
    if pol_type == lib.POL_TYPE_TRACE:
        handle_create_trace_suppression_policy(
            trace_id, include_users, output, mode, name, do_api, **selectors
        )


def handle_create_cluster_ruleset(
    output: str,
    name: str,
    generate_rules: bool,
    time_tup: Tuple[float, float],
    **filters,
):
    """
    Create a cluster ruleset with the given parameters.

    Args:
        output (str): The output format for the ruleset.
        name (str): The name of the ruleset.
        generate_rules (bool): Whether to generate rules for the ruleset.
        time_tup (Tuple[float, float]): A tuple representing the time range
            for the ruleset.
        **filters: Additional filters to be applied to the ruleset.

    Returns:
        None
    """
    ruleset = _r.cluster_rulesets.create_ruleset(
        name, generate_rules, time_tup, **filters
    )
    if output == lib.OUTPUT_DEFAULT:
        output = lib.OUTPUT_YAML
    cli.show(ruleset.as_dict(), output)


def handle_create_trace_suppression_policy(
    trace_id: str,
    include_users: bool,
    output: str,
    mode: str,
    name: str = None,
    do_api: bool = False,
    **selectors,
):
    """
    Handles the creation of a trace suppression policy.

    Args:
        trace_id (str): The ID of the trace.
        include_users (bool): Whether to include users in the suppression
            policy.
        output (str): The output format for displaying the created policy.
        mode (str): The mode of the suppression policy.
        name (str, optional): The name of the suppression policy.
            Defaults to None.
        do_api (bool, optional): Whether to use the API to create the policy.
            Defaults to False.
        **selectors: Additional keyword arguments for selecting specific
            elements.

    Returns:
        None
    """
    if do_api:
        ctx = cfg.get_current_context()
        policy = api.api_create_suppression_policy(
            *ctx.get_api_data(),
            name,
            lib.POL_TYPE_TRACE,
            include_users,
            trace_id,
            **selectors,
        )
        cli.show(policy, lib.OUTPUT_RAW)
    else:
        pol = create_trace_suppression_policy(
            trace_id, include_users, mode, name, **selectors
        )
        if output == lib.OUTPUT_DEFAULT:
            output = lib.OUTPUT_YAML
        cli.show(pol.as_dict(), output)


def create_trace_suppression_policy(
    trace_id,
    include_users,
    mode,
    name: str = None,
    ctx: cfg.Context = None,
    **selectors,
) -> _r.suppression_policies.TraceSuppressionPolicy:
    """
    Create a trace suppression policy.

    Args:
        trace_id: The ID of the trace.
        include_users: A list of users to include in the suppression policy.
        mode: The suppression mode.
        name: The name of the suppression policy (optional).
        ctx: The context (optional).
        **selectors: Additional selectors for the suppression policy.

    Returns:
        The created trace suppression policy.

    Raises:
        ValueError: If the trace or trace summary cannot be found.
    """
    if trace_id:
        trace = search.search_for_trace_by_uid(trace_id, ctx)
        if not trace:
            cli.err_exit(f"Unable to find a Trace with UID {trace_id}")
        summary_uid = trace.get(lib.TRACE_SUMMARY_FIELD)
        if not summary_uid:
            cli.err_exit(
                f"Unable to find a Trace Summary for Trace {trace_id}"
            )
        t_sum = search.search_for_trace_summary_by_uid(summary_uid, ctx)
        if not t_sum:
            cli.err_exit(
                f"Unable to find a Trace Summary with UID {summary_uid}"
            )
        pol = _r.suppression_policies.build_trace_suppression_policy(
            t_sum, include_users, mode=mode, name=name, **selectors
        )
    else:
        pol = _r.suppression_policies.build_trace_suppression_policy(
            mode=mode, name=name, **selectors
        )
    return pol


def handle_create_notif_tgt(name, tgt_type, output):
    """
    Create a notification target and display it.

    Args:
        name (str): The name of the target.
        tgt_type (str): The type of the target.
        output (str): The output format.

    Returns:
        None
    """
    target = _r.notification_targets.create_target(name, tgt_type)
    if output == lib.OUTPUT_DEFAULT:
        output = lib.OUTPUT_YAML
    cli.show(target, output)


def handle_create_notif_config(
    name: str, target: str, template: str, output: str
):
    """
    Create a notification configuration.

    Args:
        name (str): The name of the configuration.
        target (str): The target of the configuration.
        template (str): The template to use for the configuration.
        output (str): The output format for displaying the configuration.

    Returns:
        None
    """
    config = _r.notification_configs.create_config(name, target, template)
    if output == lib.OUTPUT_DEFAULT:
        output = lib.OUTPUT_YAML
    cli.show(config, output)
