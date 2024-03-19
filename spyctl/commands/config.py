"""Handles the config subcommand group for spyctl."""

import click

import spyctl.spyctl_lib as lib
from spyctl import cli

import spyctl.config as _c

# ----------------------------------------------------------------- #
#                         Config Subcommand                         #
# ----------------------------------------------------------------- #


@click.group("config", cls=lib.CustomSubGroup, epilog=lib.SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True)
def config():
    """Modify spyctl config files."""


@config.command("delete-context", cls=lib.CustomCommand, epilog=lib.SUB_EPILOG)
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
    type=_c.configs.ContextsParam(),
)
def delete_context(name, force_global, yes=False):
    """Delete the specified context from a spyctl configuration file.

    NAME is the name of the context to delete."""
    if yes:
        cli.set_yes_option()
    _c.configs.delete_context(name, force_global)


@config.command(
    "delete-apisecret", cls=lib.CustomCommand, epilog=lib.SUB_EPILOG
)
@click.help_option("-h", "--help", hidden=True)
@click.option(
    "-y",
    "--yes",
    "--assume-yes",
    is_flag=True,
    help='Automatic yes to prompts; assume "yes" as answer to all prompts and'
    " run non-interactively.",
)
@click.argument("name", type=_c.secrets.SecretsParam())
def delete_apisecret(name, yes=False):
    """Delete the specified apisecret from a spyctl configuration file.

    NAME is the name of the apisecret to delete."""
    if yes:
        cli.set_yes_option()
    _c.secrets.delete_secret(name)


@config.command(
    "current-context", cls=lib.CustomCommand, epilog=lib.SUB_EPILOG
)
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
    _c.configs.current_context(force_global)


@config.command("get-contexts", cls=lib.CustomCommand, epilog=lib.SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.argument("name", required=False, type=_c.configs.ContextsParam())
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
    _c.configs.get_contexts(name, force_global, force_workspace, output)


@config.command("get-apisecrets", cls=lib.CustomCommand, epilog=lib.SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.argument("name", required=False, type=_c.secrets.SecretsParam())
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
    _c.secrets.handle_get_secrets(name, output)


@config.command("init-workspace", cls=lib.CustomCommand, epilog=lib.SUB_EPILOG)
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
    _c.configs.init()


@config.command("set-context", cls=lib.CustomCommand, epilog=lib.SUB_EPILOG)
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
    type=_c.secrets.SecretsParam(),
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
    type=lib.ListParam(),
)
@click.option(
    "-n",
    "--namespace",
    help="Name or Spyderbat ID of Kubernetes namespace.",
    metavar="",
    type=lib.ListParam(),
)
@click.option(
    "-p",
    "--pod",
    help="Name or Spyderbat ID of Kubernetes pod.",
    metavar="",
    type=lib.ListParam(),
)
@click.option(
    "-m",
    "--machines",
    help="Name of machine group, or name or Spyderbat ID of a machine (node).",
    metavar="",
    type=lib.ListParam(),
)
@click.option(
    "-i",
    "--image",
    help="Name of container image, wildcards allowed.",
    metavar="",
    type=lib.ListParam(),
)
@click.option(
    "-d",
    "--image-id",
    help="Container image ID.",
    metavar="",
    type=lib.ListParam(),
)
@click.option(
    "-N",
    "--container-name",
    help="Name of specific container.",
    metavar="",
    type=lib.ListParam(),
)
@click.option(
    "-C",
    "--cgroup",
    help="Linux service cgroup.",
    metavar="",
    type=lib.ListParam(),
)
@click.argument("name")
def set_context(name, secret, force_global, use_ctx, **context):
    """Set a context entry in a spyctl configuration file, or update an
    existing one.
    """
    context = {
        key: value for key, value in context.items() if value is not None
    }
    _c.configs.set_context(name, secret, force_global, use_ctx, **context)


@config.command("set-apisecret", cls=lib.CustomCommand, epilog=lib.SUB_EPILOG)
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
    _c.secrets.set_secret(name, api_url, api_key)


@config.command("use-context", cls=lib.CustomCommand, epilog=lib.SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.option(
    "-g",
    "--global",
    "force_global",
    is_flag=True,
    help="When operating within a spyctl workspace, this changes the"
    " current context in the global configuration file.",
)
@click.argument("name", type=_c.configs.ContextsParam())
def use_context(name, force_global):
    """Set the current-context in a spyctl configuration file."""
    _c.configs.use_context(name, force_global)


@config.command("view", cls=lib.CustomCommand, epilog=lib.SUB_EPILOG)
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
    _c.configs.view_config(force_global, force_workspace, output)
