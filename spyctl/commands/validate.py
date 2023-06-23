import spyctl.cli as cli
import spyctl.spyctl_lib as lib


def handle_validate(file):
    if file:
        resrc_data = lib.load_resource_file(file, validate_cmd=True)
    if isinstance(resrc_data, list):
        cli.try_log("List of objects valid!")
    else:
        kind = resrc_data[lib.KIND_FIELD]
        cli.try_log(f"{kind} valid!")
