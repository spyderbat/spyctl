import spyctl.cli as cli
import spyctl.schemas_v2 as schemas
import spyctl.spyctl_lib as lib


def handle_show_schema(kind: str):
    kind = __kind_helper(kind)
    schema = schemas.handle_show_schema(kind)
    cli.show(schema, lib.OUTPUT_RAW)


def __kind_helper(kind: str):
    if kind == lib.SUP_POL_KIND_ALIAS:
        return (lib.POL_KIND, lib.POL_TYPE_TRACE)
    return kind
