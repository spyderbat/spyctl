from schema import SchemaError

import spyctl.cli as cli
import spyctl.spyctl_lib as lib
import spyctl.schemas as schemas


def handle_validate(file):
    if file:
        resrc_data = lib.load_resource_file(file)
    kind = resrc_data[lib.KIND_FIELD]
    cli.try_log(f"{kind} valid!")
