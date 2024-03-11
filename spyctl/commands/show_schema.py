"""Handle the show-schema subcommand for spyctl."""

import click

import spyctl.schemas_v2 as schemas
import spyctl.spyctl_lib as lib
from spyctl import cli

# ----------------------------------------------------------------- #
#                      ShowSchema Subcommand                        #
# ----------------------------------------------------------------- #


@click.command("show-schema", cls=lib.CustomCommand, epilog=lib.SUB_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.argument("kind", type=click.Choice(lib.RESOURCES_WITH_SCHEMAS))
def show_schema(kind):
    "Display the schema of a specific resource"
    handle_show_schema(kind)


# ----------------------------------------------------------------- #
#                       Show Schema Handlers                        #
# ----------------------------------------------------------------- #


def handle_show_schema(resource: str):
    kind = __kind_helper(resource)
    if not kind:
        cli.err_exit(f"show-schema is not supported for '{kind}'")
    schema = schemas.handle_show_schema(kind)
    cli.show(schema, lib.OUTPUT_RAW)


def __kind_helper(resource: str):
    if resource == lib.BASELINES_RESOURCE:
        return lib.BASELINE_KIND
    if resource == lib.CONFIG_ALIAS:
        return lib.CONFIG_KIND
    if resource == lib.FINGERPRINTS_RESOURCE:
        return lib.FPRINT_KIND
    if resource == lib.FINGERPRINT_GROUP_RESOURCE:
        return lib.FPRINT_GROUP_KIND
    if resource == lib.POLICIES_RESOURCE:
        return lib.POL_KIND
    if resource == lib.SECRETS_ALIAS:
        return lib.SECRET_KIND
    if resource == lib.CLUSTER_POLICY_RESOURCE:
        return (lib.POL_KIND, lib.POL_TYPE_CLUS)
    if resource == lib.SUPPRESSION_POLICY_RESOURCE:
        return (lib.POL_KIND, lib.POL_TYPE_TRACE)
    if resource == lib.UID_LIST_RESOURCE:
        return lib.UID_LIST_KIND
    return None
