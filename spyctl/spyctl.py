#! /usr/bin/env python3

import time

import click

import spyctl.cli as cli
import spyctl.commands.create as c
import spyctl.commands.diff as d
import spyctl.commands.get as g
import spyctl.commands.merge as m
import spyctl.commands.update as u
import spyctl.commands.validate as v
import spyctl.config.configs as cfgs
import spyctl.config.secrets as s
import spyctl.spyctl_lib as lib
from spyctl.commands.apply import handle_apply
from spyctl.commands.delete import handle_delete

MAIN_EPILOG = (
    "\b\n"
    'Use "spyctl <command> --help" for more information about a given '
    "command.\n"
    'Use "spyctl --version" for version information'
)
SUB_EPILOG = (
    'Use "spyctl <command> --help" for more information about a given command.'
)

DEFAULT_START_TIME = 1614811600

# ----------------------------------------------------------------- #
#                     Command Tree Entrypoint                       #
# ----------------------------------------------------------------- #


@click.group(cls=lib.CustomGroup, epilog=MAIN_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.version_option(None, "-v", "--version", prog_name="Spyctl", hidden=True)
@click.pass_context
def main(ctx: click.Context):
    """spyctl displays and controls resources within your Spyderbat
    environment
    """
    cfgs.load_config()


# ----------------------------------------------------------------- #
#                         Apply Subcommand                          #
# ----------------------------------------------------------------- #


@main.command("apply", cls=lib.CustomCommand, epilog=SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True, is_eager=True)
@click.option(
    "-f",
    "--filename",
    help="Filename containing Spyderbat resource.",
    metavar="",
    type=click.File(),
    required=True,
)
def apply(filename):
    """Apply a configuration to a resource by file name."""
    handle_apply(filename)


# ----------------------------------------------------------------- #
#                         Config Subcommand                         #
# ----------------------------------------------------------------- #


@main.group("config", cls=lib.CustomSubGroup, epilog=SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.pass_context
def config(ctx: click.Context):
    """Modify spyctl config files."""


@config.command("delete-context", cls=lib.CustomCommand, epilog=SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.option(
    "-g",
    "--global",
    "force_global",
    is_flag=True,
    help="When operating within a spyctl workspace, this deletes a context"
    " from the global spyctl configuration file.",
)
@click.option(
    "-y",
    "--yes",
    "--assume-yes",
    is_flag=True,
    help='Automatic yes to prompts; assume "yes" as answer to all prompts and'
    " run non-interactively.",
)
@click.argument(
    "name",
    type=cfgs.ContextsParam(),
)
def delete_context(name, force_global, yes=False):
    """Delete the specified context from a spyctl configuration file.

    NAME is the name of the context to delete."""
    if yes:
        cli.set_yes_option()
    cfgs.delete_context(name, force_global)


@config.command("delete-apisecret", cls=lib.CustomCommand, epilog=SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.option(
    "-y",
    "--yes",
    "--assume-yes",
    is_flag=True,
    help='Automatic yes to prompts; assume "yes" as answer to all prompts and'
    " run non-interactively.",
)
@click.argument("name", type=s.SecretsParam())
def delete_apisecret(name, yes=False):
    """Delete the specified apisecret from a spyctl configuration file.

    NAME is the name of the apisecret to delete."""
    if yes:
        cli.set_yes_option()
    s.delete_secret(name)


@config.command("current-context", cls=lib.CustomCommand, epilog=SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.option(
    "-g",
    "--global",
    "force_global",
    is_flag=True,
    help="When operating within a spyctl workspace, this displays the"
    " current context in the global configuration.",
)
def current_context(force_global):
    """Display the current-context."""
    cfgs.current_context(force_global)


@config.command("get-contexts", cls=lib.CustomCommand, epilog=SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.argument("name", required=False, type=cfgs.ContextsParam())
@click.option(
    "-o",
    "--output",
    default=lib.OUTPUT_DEFAULT,
    type=click.Choice(
        [lib.OUTPUT_DEFAULT, lib.OUTPUT_WIDE], case_sensitive=False
    ),
)
@click.option(
    "-g",
    "--global",
    "force_global",
    is_flag=True,
    help="When operating within a spyctl workspace, this displays only"
    " contexts within the global spyctl configuration file.",
)
@click.option(
    "-w",
    "--workspace",
    "force_workspace",
    is_flag=True,
    help="When operating within a spyctl workspace, this displays only"
    " contexts within the workspace configuration file.",
)
def get_contexts(force_global, force_workspace, output, name=None):
    """Describe one or many contexts.

    NAME is the name of a specific context to view.

    The default behavior is to show all of the contexts accessible to
    the current working directory. If not using a workspace, this is
    only the contexts in the global config. See --help for \"spyctl
    config init\" for more details.
    """
    if force_global and force_workspace:
        cli.try_log(
            "Both global and workspace flags set; defaulting to global"
        )
    cfgs.get_contexts(name, force_global, force_workspace, output)


@config.command("get-apisecrets", cls=lib.CustomCommand, epilog=SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.argument("name", required=False, type=s.SecretsParam())
@click.option(
    "-o",
    "--output",
    default=lib.OUTPUT_DEFAULT,
    type=click.Choice(
        lib.OUTPUT_CHOICES + [lib.OUTPUT_WIDE], case_sensitive=False
    ),
)
def get_api_secrets(output, name=None):
    """Describe one or many apisecrets."""
    s.handle_get_secrets(name, output)


@config.command("init-workspace", cls=lib.CustomCommand, epilog=SUB_EPILOG)
@click.option(
    "-y",
    "--yes",
    "--assume-yes",
    is_flag=True,
    help='Automatic yes to prompts; assume "yes" as answer to all prompts and'
    " run non-interactively.",
)
@click.help_option("-h", "--help", hidden=True)
def init_workspace(yes=False):
    """Initialize a workspace.

    This command creates a '.spyctl/config' file in the current working
    directory. Workspaces are a spyctl configuration file local to a
    specific directory. They allow you to create contexts only
    accessible from the directory subtree from where the config file
    resides. They also allow you to set a current context for a
    directory subtree.

    This is helpful if you're working on a specific service or
    container and want spyctl to return data relevant only to that
    application.

    For example:
    If your cwd is ``$HOME/myproject/`` and you issue the command
    ``spyctl config current-context`` you will be shown the current
    context in the global configuration. But if create initialize
    a workspace and create a context, you will notice that your
    current context is the one set within the workspace configuration
    file.

    For example:

      # Create a workspace in the current working directory.\n
      spyctl config init-workspace

      # Create a context specific to a Linux Service.\n
      spyctl config set-context --cgroup systemd:/system.slice/my_app.service
      --org my_organization --secret my_secret my_app_context

      # Show the current context and see my_app_context in the output.\n
      spyctl config current-context

    Executing spyctl outside of a workspace directory or any of its
    subdirectories will revert the tool to using the current context in
    the global configuration file.
    """
    if yes:
        cli.set_yes_option()
    cfgs.init()


@config.command("set-context", cls=lib.CustomCommand, epilog=SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.option(
    "-g",
    "--global",
    "force_global",
    is_flag=True,
    help="When operating within a spyctl workspace, this sets a context"
    " in the global spyctl configuration file.",
)
@click.option(
    "-u",
    "--use-context",
    "use_ctx",
    is_flag=True,
    help="Use this context when set. Sets the current-context field in the"
    " config file. The first context added to a config is automatically set as"
    " current-context.",
)
@click.option(
    "-s",
    "--secret",
    help="Name of api config secret.",
    metavar="",
    required=True,
    type=s.SecretsParam(),
)
@click.option(
    "-o",
    "--organization",
    "--org",
    help="ID or name of Spyderbat organization.",
    metavar="",
    required=True,
)
@click.option(
    "-c",
    "--cluster",
    help="Name or Spyderbat ID of Kubernetes cluster.",
    metavar="",
)
@click.option(
    "-n",
    "--namespace",
    help="Name or Spyderbat ID of Kubernetes namespace.",
    metavar="",
)
@click.option(
    "-p", "--pod", help="Name or Spyderbat ID of Kubernetes pod.", metavar=""
)
@click.option(
    "-m",
    "--machines",
    help="Name of machine group, or name or Spyderbat ID of a machine (node).",
    metavar="",
)
@click.option(
    "-i",
    "--image",
    help="Name of container image, wildcards allowed.",
    metavar="",
)
@click.option("-d", "--image-id", help="Container image ID.", metavar="")
@click.option(
    "-N", "--container-name", help="Name of specific container.", metavar=""
)
@click.option("-C", "--cgroup", help="Linux service cgroup.", metavar="")
@click.argument("name")
def set_context(name, secret, force_global, use_ctx, **context):
    """Set a context entry in a spyctl configuration file, or update an
    existing one.
    """
    context = {
        key: value for key, value in context.items() if value is not None
    }
    cfgs.set_context(name, secret, force_global, use_ctx, **context)


@config.command("set-apisecret", cls=lib.CustomCommand, epilog=SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.argument("name", required=False)
@click.option(
    "-k",
    "--apikey",
    "--api-key",
    "api_key",
    help="API key generated via the Spyderbat UI",
    metavar="",
)
@click.option(
    "-u",
    "--apiurl",
    "--api-url",
    "api_url",
    help=f"URL target for api queries. Default: {lib.DEFAULT_API_URL}",
    metavar="",
)
def set_apisecrets(api_key=None, api_url=None, name=None):
    """
    Set a new entry in the spyctl secrets file, or update an existing one.
    """
    s.set_secret(name, api_url, api_key)


@config.command("use-context", cls=lib.CustomCommand, epilog=SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.option(
    "-g",
    "--global",
    "force_global",
    is_flag=True,
    help="When operating within a spyctl workspace, this changes the"
    " current context in the global configuration file.",
)
@click.argument("name", type=cfgs.ContextsParam())
def use_context(name, force_global):
    """Set the current-context in a spyctl configuration file."""
    cfgs.use_context(name, force_global)


@config.command("view", cls=lib.CustomCommand, epilog=SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.option(
    "-g",
    "--global",
    "force_global",
    is_flag=True,
    help="When operating within a spyctl workspace, this displays"
    " the global spyctl configuration file.",
)
@click.option(
    "-w",
    "--workspace",
    "force_workspace",
    is_flag=True,
    help="When operating within a spyctl workspace, this displays"
    " only the workspace configuration file.",
)
@click.option(
    "-o",
    "--output",
    default=lib.OUTPUT_DEFAULT,
    type=click.Choice(lib.OUTPUT_CHOICES, case_sensitive=False),
)
def view(force_global, force_workspace, output):
    """View the current spyctl configuration file. If operating
    within a workspace the default behavior displays a merged
    configuration including contexts from the global config and any
    other workspace configuration files from cwd to root.
    """
    if force_global and force_workspace:
        cli.try_log(
            "Both global and workspace flags set; defaulting to global"
        )
    cfgs.view_config(force_global, force_workspace, output)


# ----------------------------------------------------------------- #
#                         Create Subcommand                         #
# ----------------------------------------------------------------- #


@main.group("create", cls=lib.CustomSubGroup, epilog=SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True)
def create():
    """Create a resource from a file."""
    pass


@create.command("baseline", cls=lib.CustomCommand, epilog=SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.option(
    "-f",
    "--from-file",
    "filename",
    help="File that contains the FingerprintsGroup object, from which spyctl"
    " creates a baseline.",
    required=True,
    metavar="",
    type=click.File(),
)
@click.option(
    "-o",
    "--output",
    default=lib.OUTPUT_DEFAULT,
    type=click.Choice(lib.OUTPUT_CHOICES, case_sensitive=False),
)
def create_baseline(filename, output):
    """Create a Baseline from a file, outputted to stdout"""
    c.handle_create_baseline(filename, output)


@create.command("policy", cls=lib.CustomCommand, epilog=SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.option(
    "-f",
    "--from-file",
    "filename",
    help="File that contains the FingerprintsGroup or SpyderbatBaseline"
    " object, from which spyctl creates a policy",
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
def create_policy(filename, output):
    """Create a Policy object from a file, outputted to stdout"""
    c.handle_create_policy(filename, output)


# ----------------------------------------------------------------- #
#                        Delete Subcommand                          #
# ----------------------------------------------------------------- #


@main.command("delete", cls=lib.CustomCommand, epilog=SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.argument("resource", type=lib.DelResourcesParam())
@click.argument("name_or_id")
@click.option(
    "-y",
    "--yes",
    "--assume-yes",
    is_flag=True,
    help='Automatic yes to prompts; assume "yes" as answer to all prompts and'
    " run non-interactively.",
)
def delete(resource, name_or_id, yes=False):
    """Delete resources by resource and name, or by resource and ids"""
    if yes:
        cli.set_yes_option()
    handle_delete(resource, name_or_id)


# ----------------------------------------------------------------- #
#                          Diff Subcommand                          #
# ----------------------------------------------------------------- #


@main.command("diff", cls=lib.CustomCommand, epilog=SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.option(
    "-f",
    "--filename",
    help="Target file(s) of the diff.",
    metavar="",
    type=lib.FileList(),
    cls=lib.MutuallyExclusiveEatAll,
    mutually_exclusive=["policy"],
)
@click.option(
    "-p",
    "--policy",
    is_flag=False,
    flag_value="all",
    default=None,
    help="Target policy name(s) or uid(s) of the diff. If supplied with no"
    " argument, set to 'all'.",
    metavar="",
    type=lib.ListParam(),
    cls=lib.MutuallyExclusiveOption,
    mutually_exclusive=["filename"],
)
@click.option(
    "-w",
    "--with-file",
    "with_file",
    help="File to diff with target.",
    metavar="",
    type=click.File(),
    cls=lib.MutuallyExclusiveOption,
    mutually_exclusive=["with_policy"],
)
@click.option(
    "-P",
    "--with-policy",
    "with_policy",
    help="Policy uid to diff with target. If supplied with no argument then"
    " spyctl will attempt to find a policy matching the uid in the target's"
    " metadata.",
    metavar="",
    is_flag=False,
    flag_value="matching",
    cls=lib.MutuallyExclusiveOption,
    mutually_exclusive=["with_file"],
)
@click.option(
    "-l",
    "--latest",
    is_flag=True,
    help=f"Diff target with latest records using the value of"
    f" '{lib.LATEST_TIMESTAMP_FIELD}' in '{lib.METADATA_FIELD}'."
    " This replaces --start-time.",
    metavar="",
)
@click.option(
    "-t",
    "--start-time",
    "st",
    help="Start time of the query for fingerprints to diff."
    " Only used if --latest, --with-file, --with-policy are not set."
    " Default is 24 hours ago.",
    default="24h",
    type=lib.time_inp,
)
@click.option(
    "-e",
    "--end-time",
    "et",
    help="End time of the query for fingerprints to diff."
    " Only used if --with-file, and --with-policy are not set."
    " Default is now.",
    default=time.time(),
    type=lib.time_inp,
)
@click.option(
    "-y",
    "--yes",
    "--assume-yes",
    is_flag=True,
    help='Automatic yes to prompts; assume "yes" as answer to all prompts and'
    " run non-interactively.",
)
def diff(
    filename,
    policy,
    st,
    et,
    yes=False,
    with_file=None,
    with_policy=None,
    latest=False,
):
    """Diff target Baselines and Policies with other Resources.

      Diff'ing in Spyctl requires a target Resource (e.g. a Baseline or Policy
    document you are maintaining) and a Resource to diff with the target.
    A target can be either a local file supplied using the -f option or a policy
    you've applied to the Spyderbat Backend supplied with the -p option.
    By default, target's are diff'd with relevant* Fingerprints from the last 24
    hours to now. Targets may also be diff'd with local files with the -w option
    or with data from an existing applied policy using the -P option.

      The output of a diff shows you any lines that would be added to or removed
    from your target Resource as a result of a Merge. diffs may also be performed
    in bulk. Bulk diffs are outputted to a pager like 'less' or 'more'.

      To maintain a target Resource effectively, the goal should be to get to
    get to a point where the diff no longer displays added or removed lines (other
    than timestamps).

    \b
    Examples:
      # diff a local policy file with relevant* Fingerprints from the last
      # 24hrs to now:
      spyctl diff -f policy.yaml\n
    \b
      # diff a local policy file with relevant* Fingerprints from its
      # latestTimestamp field to now:
      spyctl diff -f policy.yaml --latest\n
    \b
      # diff an existing applied policy with relevant* Fingerprints from the
      # last 24hrs to now:
      spyctl diff -p <NAME_OR_UID>\n
    \b
      # Bulk diff all existing policies with relevant* Fingerprints from the
      # last 24hrs to now:
      spyctl diff -p\n
    \b
      # Bulk diff multiple policies with relevant* Fingerprints from the
      # last 24hrs to now:
      spyctl diff -p <NAME_OR_UID1>,<NAME_OR_UID2>\n
    \b
      # Bulk diff all files in cwd matching a pattern with relevant*
      # Fingerprints from the last 24hrs to now:
      spyctl diff -f *.yaml\n
    \b
      # diff an existing applied policy with a local file:
      spyctl diff -p <NAME_OR_UID> --with-file fingerprints.yaml\n
    \b
      # diff a local file with data from an existing applied policy
      spyctl diff -f policy.yaml -P <NAME_OR_UID>\n
    \b
      # diff a local file with a valid UID in its metadata with the matching
      # policy in the Spyderbat Backend
      spyctl diff -f policy.yaml -P

    * Each policy has one or more Selectors in its spec field,
    relevant Fingerprints are those that match those Selectors.

    For time field options such as --start-time and --end-time you can
    use (m) for minutes, (h) for hours (d) for days, and (w) for weeks back
    from now or provide timestamps in epoch format.

    Note: Long time ranges or "get" commands in a context consisting of
    multiple machines can take a long time.
    """  # noqa E501
    if yes:
        cli.set_yes_option()
    d.handle_diff(filename, policy, with_file, with_policy, st, et, latest)


# ----------------------------------------------------------------- #
#                          Get Subcommand                           #
# ----------------------------------------------------------------- #


class GetCommand(lib.ArgumentParametersCommand):
    argument_name = "resource"
    argument_value_parameters = [
        {
            "resource": [lib.REDFLAGS_RESOURCE, lib.OPSFLAGS_RESOURCE],
            "args": [
                click.option(
                    "--severity",
                    lib.FLAG_SEVERITY,
                    help="Only show flags with the given"
                    " severity or higher.",
                ),
            ],
        },
        {
            "resource": [lib.REDFLAGS_RESOURCE],
            "args": [
                click.option(
                    "--include-exceptions",
                    "exceptions",
                    is_flag=True,
                    help="Include redflags marked as exceptions in output."
                    " Off by default.",
                ),
            ],
        },
        {
            "resource": [lib.FINGERPRINTS_RESOURCE],
            "args": [
                click.option(
                    "-f",
                    "--filename",
                    help="Input file to create filters from. Used if you want"
                    " to get fingerprints related to another resource."
                    " E.g. the Fingerprint Groups for a given Baseline file.",
                    metavar="",
                    type=click.File(),
                ),
                click.option(
                    "-p",
                    "--policy",
                    help="Policy uid to build filters from. This will download"
                    " a policy from the spyderbat backend, then filter"
                    " Fingerprints based on the policy's selectors.",
                    metavar="",
                ),
            ],
        },
        {
            "resource": [lib.CONNECTIONS_RESOURCE],
            "args": [
                click.option(
                    "--ignore-ips",
                    "ignore_ips",
                    is_flag=True,
                    help="Ignores differing ips in the table output."
                    " Off by default.",
                ),
            ],
        },
    ]


@main.command("get", cls=GetCommand, epilog=SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.argument("resource", type=lib.GetResourcesParam())
@click.argument("name_or_id", required=False)
@click.option(
    "--image",
    cfgs.IMG_FIELD,
    help="Only show resources tied to this container image."
    " Overrides value current context if it exists.",
)
@click.option(
    "--image-id",
    cfgs.IMGID_FIELD,
    help="Only show resources tied to containers running with this"
    " image id. Overrides value current context if it exists.",
)
@click.option(
    "--container-name",
    cfgs.CONTAINER_NAME_FIELD,
    help="Only show resources tied to containers running with this"
    " container name. Overrides value current context if it exists.",
)
@click.option(
    "--container-id",
    cfgs.CONT_ID_FIELD,
    help="Only show resources tied to containers running with this"
    " container id. Overrides value current context if it exists.",
)
@click.option(
    "--cgroup",
    cfgs.CGROUP_FIELD,
    help="Only show resources tied to machines running Linux services with"
    " this cgroup. Overrides value current context if it exists.",
)
@click.option(
    "--pod",
    cfgs.POD_FIELD,
    help="Only show resources tied to this pod uid."
    " Overrides value current context if it exists.",
)
@click.option(
    f"--{cfgs.MACHINES_FIELD}",
    "--nodes",
    help="Only show resources to these nodes."
    " Overrides value current context if it exists.",
)
@click.option(
    f"--{cfgs.NAMESPACE_FIELD}",
    help="Only show resources tied to this namespace."
    " Overrides value current context if it exists.",
)
@click.option(
    f"--{cfgs.CLUSTER_FIELD}",
    help="Only show resources tied to this cluster."
    " Overrides value current context if it exists.",
)
@click.option(
    "-o",
    "--output",
    default=lib.OUTPUT_DEFAULT,
    type=click.Choice(
        lib.OUTPUT_CHOICES + [lib.OUTPUT_WIDE], case_sensitive=False
    ),
)
@click.option(
    "-l",
    "--latest",
    help="Starting time of the query is set to the"
    f" '{lib.LATEST_TIMESTAMP_FIELD}'"
    f" field the input resource's '{lib.METADATA_FIELD}' and replaces"
    " --start-time. [Requires '--filename' option to be set]",
    is_flag=True,
)
@click.option(
    "-E",
    "--exact",
    "--exact-match",
    is_flag=True,
    help="Exact match for NAME_OR_ID. This command's default behavior"
    "displays any resource that contains the NAME_OR_ID.",
)
@click.option(
    "-t",
    "--start-time",
    "st",
    help="Start time of the query. Default is 24 hours ago.",
    default="24h",
    type=lib.time_inp,
)
@click.option(
    "-e",
    "--end-time",
    "et",
    help="End time of the query. Default is now.",
    default=time.time(),
    type=lib.time_inp,
)
def get(
    resource,
    st,
    et,
    output,
    filename=None,
    exact=False,
    name_or_id=None,
    latest=None,
    **filters,
):
    """Display one or many Spyderbat Resources.

    See https://spyctl.readthedocs.io/en/latest/user/resources.html for a full
    list of available resource.

    \b
    Some resources are retrieved from from databases where a time range can
    be specified:
    - Fingerprints
    - Pods
    - Namespaces
    - Nodes
    - Processes
    - Connections
    - RedFlags
    - OpsFlags

    \b
    Other resources come from databases where time ranges are not applicable:
    - Clusters
    - Machines
    - Policies

    \b
    Examples:
      # Get all observed Pods for the last hour:
      spyctl get pods -t 1h\n
    \b
      # Get all observed Pods from 4 hours ago to 2 hours ago
      spyctl get pods -t 4h -e 2h\n
    \b
      # Get observed pods for a specific time range (using epoch timestamps)
      spyctl get pods -t 1675364629 -e 1675368229\n
    \b
      # Get a Fingerprint Group of all runs of httpd.service for the last 24
      # hours and output to a yaml file
      spyctl get fingerprints httpd.service -o yaml > fprints.yaml\n
    \b
      # Get the latest fingerprints related to a policy yaml file
      spyctl get fingerprints -f policy.yaml --latest

    For time field options such as --start-time and --end-time you can
    use (m) for minutes, (h) for hours (d) for days, and (w) for weeks back
    from now or provide timestamps in epoch format.

    Note: Long time ranges or "get" commands in a context consisting of
    multiple machines can take a long time.
    """
    filters = {
        key: value for key, value in filters.items() if value is not None
    }
    g.handle_get(
        resource,
        name_or_id,
        st,
        et,
        filename,
        latest,
        exact,
        output,
        **filters,
    )


# ----------------------------------------------------------------- #
#                         Merge Subcommand                          #
# ----------------------------------------------------------------- #


@main.command("merge", cls=lib.CustomCommand, epilog=SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.option(
    "-f",
    "--filename",
    help="Target file(s) of the merge.",
    metavar="",
    type=lib.FileList(),
    cls=lib.MutuallyExclusiveEatAll,
    mutually_exclusive=["policy"],
)
@click.option(
    "-p",
    "--policy",
    is_flag=False,
    flag_value=m.ALL,
    default=None,
    help="Target policy name(s) or uid(s) of the merge. If supplied with no"
    " argument, set to 'all'.",
    metavar="",
    type=lib.ListParam(),
    cls=lib.MutuallyExclusiveOption,
    mutually_exclusive=["filename"],
)
@click.option(
    "-w",
    "--with-file",
    "with_file",
    help="File to merge into target.",
    metavar="",
    type=click.File(),
    cls=lib.MutuallyExclusiveOption,
    mutually_exclusive=["with_policy"],
)
@click.option(
    "-P",
    "--with-policy",
    "with_policy",
    help="Policy uid to merge with target. If supplied with no argument then"
    " spyctl will attempt to find a policy matching the uid in the"
    " target's metadata.",
    metavar="",
    is_flag=False,
    flag_value=m.MATCHING,
    cls=lib.MutuallyExclusiveOption,
    mutually_exclusive=["with_file"],
)
@click.option(
    "-l",
    "--latest",
    is_flag=True,
    help=f"Merge file with latest records using the value of"
    f" '{lib.LATEST_TIMESTAMP_FIELD}' in the target's '{lib.METADATA_FIELD}'."
    " This replaces --start-time.",
    metavar="",
)
@click.option(
    "-o",
    "--output",
    default=lib.OUTPUT_DEFAULT,
    type=click.Choice(lib.OUTPUT_CHOICES, case_sensitive=False),
)
@click.option(
    "-t",
    "--start-time",
    "st",
    help="Start time of the query for fingerprints to merge."
    " Only used if --latest, --with-file, and --with-policy are not set."
    " Default is 24 hours ago.",
    default="24h",
    type=lib.time_inp,
)
@click.option(
    "-e",
    "--end-time",
    "et",
    help="End time of the query for fingerprints to merge."
    " Only used if --with-file and --with-policy are not set."
    " Default is now.",
    default=time.time(),
    type=lib.time_inp,
)
@click.option(
    "-O",
    "--output-to-file",
    help="Should output merge to a file. Unique filename created from the name"
    " in the object's metadata.",
    is_flag=True,
)
@click.option(
    "-y",
    "--yes",
    "--assume-yes",
    is_flag=True,
    help='Automatic yes to prompts; assume "yes" as answer to all prompts and'
    " run non-interactively.",
)
def merge(
    filename,
    policy,
    output,
    st,
    et,
    yes=False,
    with_file=None,
    with_policy=None,
    latest=False,
    output_to_file=False,
):
    """Merge target Baselines and Policies with other Resources.

      Merging in Spyctl requires a target Resource (e.g. a Baseline or Policy
    document you are maintaining) and a Resource to merge into the target.
    A target can either be a local file supplied using the -f option or a policy
    you've applied to the Spyderbat Backend supplied with the -p option.
    By default, target's are merged with relevant* Fingerprints from the last 24
    hours to now. Targets may also be merged with local files with the -w option
    or with data from an existing applied policy using the -P option.

      When merging a single local file with another resource, the output will
    be sent to stdout. WARNING: Do not redirect output to the same file you
    used as input. You may use the -O flag to output the merged data to a
    unique file with a name generate by Spyctl.

      When bulk merging local files, the output for each merge operation will
    be outputted to unique files generated by Spyctl (the same as supplying the
    -O flag mentioned above).

      When merging existing applied policies in bulk or individually, the default
    destination for the output will be to apply it directly to the Spyderbat Backend (you
    will have a chance to review the merge before any changes are applied).
    This removes the requirement to deal with local files when managing policies. However,
    it is a good idea to back up policies in a source-control repository. You can also
    use the -O operation to send the output of this merge to a local file.

    \b
    Examples:
      # merge a local policy file with relevant* Fingerprints from the last
      # 24hrs to now:
      spyctl merge -f policy.yaml\n
    \b
      # merge a local policy file with relevant* Fingerprints from its
      # latestTimestamp field to now:
      spyctl merge -f policy.yaml --latest\n
    \b
      # merge an existing applied policy with relevant* Fingerprints from the
      # last 24hrs to now:
      spyctl merge -p <NAME_OR_UID>\n
    \b
      # Bulk merge all existing policies with relevant* Fingerprints from the
      # last 24hrs to now:
      spyctl merge -p\n
    \b
      # Bulk merge multiple policies with relevant* Fingerprints from the
      # last 24hrs to now:
      spyctl merge -p <NAME_OR_UID1>,<NAME_OR_UID2>\n
    \b
      # Bulk merge all files in cwd matching a pattern with relevant*
      # Fingerprints from the last 24hrs to now:
      spyctl merge -f *.yaml\n
    \b
      # merge an existing applied policy with a local file:
      spyctl merge -p <NAME_OR_UID> --with-file fingerprints.yaml\n
    \b
      # merge a local file with data from an existing applied policy
      spyctl merge -f policy.yaml -P <NAME_OR_UID>\n
    \b
      # merge a local file with a valid UID in its metadata with the matching
      # policy in the Spyderbat Backend
      spyctl merge -f policy.yaml -P

    * Each policy has one or more Selectors in its spec field,
    relevant Fingerprints are those that match those Selectors.

    For time field options such as --start-time and --end-time you can
    use (m) for minutes, (h) for hours (d) for days, and (w) for weeks back
    from now or provide timestamps in epoch format.

    Note: Long time ranges or "get" commands in a context consisting of
    multiple machines can take a long time.
    """  # noqa E501
    if yes:
        cli.set_yes_option()
    if output == lib.OUTPUT_DEFAULT:
        output = lib.OUTPUT_YAML
    m.handle_merge(
        filename,
        policy,
        with_file,
        with_policy,
        st,
        et,
        latest,
        output,
        output_to_file,
    )


# ----------------------------------------------------------------- #
#                       Validate Subcommand                         #
# ----------------------------------------------------------------- #


@main.command("validate", cls=lib.CustomCommand, epilog=SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.option(
    "-f",
    "--filename",
    "file",
    help="Target file to validate",
    metavar="",
    required=True,
    type=click.File(),
)
def validate(file):
    """Validate spyderbat resource and spyctl configuration files.

    \b
    example:
      spyctl validate -f my_baseline.yaml
    """
    v.handle_validate(file)


if __name__ == "__main__":
    main()


# ----------------------------------------------------------------- #
#                    Hidden Update Subcommand                       #
# ----------------------------------------------------------------- #


@main.group("update", cls=lib.CustomSubGroup, hidden=True)
@click.help_option("-h", "--help", hidden=True)
def update():
    pass


@update.command("response-actions", cls=lib.CustomCommand)
@click.help_option("-h", "--help", hidden=True)
@click.option(
    "-b",
    "--backup-file",
    "backup_file",
    help="location to place policy backups",
    type=click.Path(exists=True, writable=True, file_okay=False),
)
def update_response_actions(backup_file=None):
    u.handle_update_response_actions(backup_file)
