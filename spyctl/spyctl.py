#! /usr/bin/env python3

import time
from typing import Dict, List

import click

import spyctl.config.configs as cfgs
import spyctl.config.secrets as s
import spyctl.spyctl_lib as lib
import spyctl.subcommands.get as g
import spyctl.subcommands.create as c
import spyctl.subcommands.merge as m
from spyctl.subcommands.apply import handle_apply
from spyctl.subcommands.delete import handle_delete

MAIN_EPILOG = (
    'Use "spyctl <command> --help" for more information about a given command'
)
DEFAULT_API_URL = "https://api.spyderbat.com"
DEFAULT_START_TIME = 1614811600


# ----------------------------------------------------------------- #
#                     Command Tree Entrypoint                       #
# ----------------------------------------------------------------- #


@click.group(cls=lib.CustomGroup, epilog=MAIN_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.pass_context
def main(ctx):
    """spyctl displays and controls resources within your Spyderbat
    environment
    """
    cfgs.load_config()


# ----------------------------------------------------------------- #
#                         Apply Subcommand                          #
# ----------------------------------------------------------------- #


@main.command("apply", cls=lib.CustomCommand, epilog=MAIN_EPILOG)
@click.help_option("-h", "--help", hidden=True, is_eager=True)
@click.option(
    "-f",
    "--filename",
    help="Filename containing Spyderbat resource.",
    metavar="",
)
def apply(filename):
    """Apply a configuration to a resource by file name."""
    handle_apply(filename)


# ----------------------------------------------------------------- #
#                         Config Subcommand                         #
# ----------------------------------------------------------------- #


@main.group("config", cls=lib.CustomSubGroup, epilog=MAIN_EPILOG)
@click.help_option("-h", "--help", hidden=True)
def config():
    """Modify spyctl config files."""
    pass


@config.command("delete-context", cls=lib.CustomCommand, epilog=MAIN_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.option(
    "-g",
    "--global",
    "force_global",
    is_flag=True,
    help="When operating within a spyctl workspace, this forces a change to"
    " the global spyctl config.",
)
@click.argument("name")
def delete_context(name, force_global):
    """Delete the specified context from a spyctl configuration file."""
    cfgs.delete_context(name, force_global)


@config.command("current-context", cls=lib.CustomCommand, epilog=MAIN_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.option(
    "-g",
    "--global",
    "force_global",
    is_flag=True,
    help="When operating within a spyctl workspace, this forces a change to"
    " the global spyctl config.",
)
def current_context(force_global):
    """Display the current-context."""
    cfgs.current_context(force_global)


@config.command("set-context", cls=lib.CustomCommand, epilog=MAIN_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.option(
    "-g",
    "--global",
    "force_global",
    is_flag=True,
    help="When operating within a spyctl workspace, this forces a change to"
    " the global spyctl config.",
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
)
@click.option(
    "-o",
    "--organization",
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
    """Set a context entry in a spyctl configuration file."""
    context = {
        key: value for key, value in context.items() if value is not None
    }
    cfgs.set_context(name, secret, force_global, use_ctx, **context)


@config.command("use-context", cls=lib.CustomCommand, epilog=MAIN_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.option(
    "-g",
    "--global",
    "force_global",
    is_flag=True,
    help="When operating within a spyctl workspace, this forces a change to"
    " the global spyctl config.",
)
@click.argument("name")
def use_context(name, force_global):
    """Set the current-context in a spyctl configuration file."""
    cfgs.use_context(name, force_global)


@config.command("view", cls=lib.CustomCommand, epilog=MAIN_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.option(
    "-g",
    "--global",
    "force_global",
    is_flag=True,
    help="When operating within a spyctl workspace, this forces a change to"
    " the global spyctl config.",
)
@click.option(
    "-w",
    "--workspace",
    "force_workspace",
    is_flag=True,
    help="View merged configuration file. Supply a flag to view global"
    " configuration file or local workspace configuration file.",
)
@click.option("-o", "--output", default=lib.OUTPUT_YAML, metavar="")
def view(force_global, force_workspace, output):
    """View the current spyctl configuration file(s)."""
    cfgs.view_config(force_global, force_workspace, output)


# ----------------------------------------------------------------- #
#                         Create Subcommand                         #
# ----------------------------------------------------------------- #


@main.group("create", cls=lib.CustomSubGroup, epilog=MAIN_EPILOG)
@click.help_option("-h", "--help", hidden=True)
def create():
    """Create a resource from a file."""
    pass


@create.command("baseline", cls=lib.CustomCommand, epilog=MAIN_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.option(
    "-f",
    "--from-file",
    "filename",
    help="File that contains the FingerprintsGroup object, from which spyctl"
    " creates a baseline.",
    metavar="",
)
@click.option("-o", "--output", default=lib.OUTPUT_YAML, metavar="")
def create_baseline(filename, output):
    """Create a Baseline from a file, outputted to stdout"""
    c.handle_create_baseline(filename, output)


@create.command("policy", cls=lib.CustomCommand, epilog=MAIN_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.option(
    "-f",
    "--from-file",
    "filename",
    help="File that contains the FingerprintsGroup or SpyderbatBaseline"
    " object, from which spyctl creates a policy",
    metavar="",
)
def create_policy(filename):
    """Create a Policy object from a file, outputted to stdout"""
    pass


@create.group("secret", cls=lib.CustomSubGroup, epilog=MAIN_EPILOG)
@click.help_option("-h", "--help", hidden=True)
def create_secret():
    """Create a Secret object from the command line."""
    pass


@create_secret.command("apicfg", cls=lib.CustomCommand, epilog=MAIN_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.option(
    "-k",
    "--apikey",
    "--api-key",
    "api_key",
    help="API key generated via the Spyderbat UI, base64 encoded."
    " Use 'echo -n <apikey> | base64 -w 0'",
    metavar="",
)
@click.option(
    "-u",
    "--apiurl",
    "--api-url",
    "api_url",
    help=f"URL target for api queries. Default: {DEFAULT_API_URL}",
    default=DEFAULT_API_URL,
    metavar="",
)
@click.argument("name")
def create_apicfg_secret(name, api_key, api_url):
    """Create an apicfg secret. spyctl requires an api secret be applied to a
    context in order to run successful api queries.
    """
    s.create_secret(
        name,
        s.S_TYPE_APICFG,
        data={lib.API_KEY_FIELD: api_key},
        string_data={lib.API_URL_FIELD: api_url},
    )


@create_secret.command("opaque", cls=lib.CustomCommand, epilog=MAIN_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.option(
    "--data",
    help="Key/value pairs, base64 encoded.",
    metavar="",
)
@click.option(
    "--string-data",
    "string_data",
    help="Key/value pairs, plain text.",
    default=DEFAULT_API_URL,
    metavar="",
)
@click.argument("name")
def create_opque_secret(name, data=None, string_data=None):
    """Create an opaque secret. May contain an arbitrary amount of base64
    encoded data and plaintext string data.
    """
    s.create_secret(name, s.S_TYPE_OPAQUE, data, string_data)


# ----------------------------------------------------------------- #
#                        Delete Subcommand                          #
# ----------------------------------------------------------------- #


@main.command("delete", cls=lib.CustomCommand, epilog=MAIN_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.argument("resource")
@click.argument("name_or_id")
def delete(resource, name_or_id):
    """Delete resources by resource and names, or by resource and ids"""
    handle_delete(resource, name_or_id)


# ----------------------------------------------------------------- #
#                          Diff Subcommand                          #
# ----------------------------------------------------------------- #


@main.command("diff", cls=lib.CustomCommand, epilog=MAIN_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.option(
    "-f",
    "--filename",
    help="Target file of the diff.",
    metavar="",
)
@click.option(
    "-w",
    "--with-file",
    help="File to diff with target file.",
    metavar="",
)
@click.option(
    "-l",
    "--latest",
    help="Diff file with latest records using the value of lastTimestamp in"
    " metadata",
    metavar="",
)
def diff(filename, with_file=None, latest=None):
    """Diff FingerprintsGroups with SpyderbatBaselines and SpyderbatPolicies"""
    pass


# ----------------------------------------------------------------- #
#                          Get Subcommand                           #
# ----------------------------------------------------------------- #


@main.group("get", cls=lib.CustomCommand, epilog=MAIN_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.argument("resource")
@click.argument("name_or_id", required=False)
@click.option(
    f"--{cfgs.IMG_FIELD}",
    help="Only show clusters with pods or nodes running this container image."
    " Overrides value current context if it exists.",
)
@click.option(
    f"--{cfgs.IMGID_FIELD}",
    "imageID",
    help="Only show clusters with pods or nodes running containers with this"
    " image id. Overrides value current context if it exists.",
)
@click.option(
    f"--{cfgs.CONTAINER_NAME_FIELD}",
    help="Only show clusters with pods or node running containers with this"
    " container name. Overrides value current context if it exists.",
)
@click.option(
    f"--{cfgs.CGROUP_FIELD}",
    help="Only show clusters with nodes running Linux services with this"
    " cgroup. Overrides value current context if it exists.",
)
@click.option(
    f"--{cfgs.POD_FIELD}",
    help="Only show clusters with nodes running this pod."
    " Overrides value current context if it exists.",
)
@click.option(
    f"--{cfgs.MACHINES_FIELD}",
    "--nodes",
    help="Only show clusters linked to these nodes."
    " Overrides value current context if it exists.",
)
@click.option(
    f"--{cfgs.NAMESPACE_FIELD}",
    help="Only show clusters with this namespace."
    " Overrides value current context if it exists.",
)
@click.option(
    f"--{cfgs.CLUSTER_FIELD}",
    help="Only show this cluster."
    " Overrides value current context if it exists.",
)
@click.option("-o", "--output", default=lib.OUTPUT_DEFAULT)
@click.option(
    "-l",
    "--latest",
    help=f"Filename for resource. If there is a {lib.LATEST_TIMESTAMP_FIELD}"
    " in the resources metadata field, the start time of the query is set to"
    " that.",
    metavar="",
)
@click.option(
    "-t",
    "--start-time",
    "st",
    help="Start time of the query. Default is beginning of time.",
    default="2h",
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
def get(resource, st, et, output, name_or_id=None, latest=None, **filters):
    """Display one or many resources."""
    filters = {
        key: value for key, value in filters.items() if value is not None
    }
    g.handle_get(resource, name_or_id, st, et, latest, output, **filters)


# ----------------------------------------------------------------- #
#                         Init Subcommand                           #
# ----------------------------------------------------------------- #


@main.command("init", cls=lib.CustomCommand, epilog=MAIN_EPILOG)
@click.help_option("-h", "--help", hidden=True)
def init():
    """Initialize a workspace"""
    cfgs.init()


# ----------------------------------------------------------------- #
#                         Merge Subcommand                          #
# ----------------------------------------------------------------- #


@main.command("merge", cls=lib.CustomCommand, epilog=MAIN_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.option(
    "-f",
    "--filename",
    help="Target file of the merge.",
    metavar="",
    required=True,
)
@click.option(
    "-w",
    "--with-file",
    help="File to merge into target file.",
    metavar="",
)
@click.option(
    "-l",
    "--latest",
    is_flag=True,
    help=f"Merge file with latest records using the value of"
    f" {lib.LATEST_TIMESTAMP_FIELD} in the input file's metadata",
    metavar="",
)
@click.option("-o", "--output", default=lib.OUTPUT_DEFAULT)
def merge(filename, output, with_file=None, latest=False):
    """Merge FingerprintsGroups into SpyderbatBaselines and
    SpyderbatPolicies
    """
    if output == lib.OUTPUT_DEFAULT:
        output = lib.OUTPUT_YAML
    m.handle_merge(filename, with_file, latest, output)


if __name__ == "__main__":
    main()
