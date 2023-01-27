import spyctl.cli as cli
import spyctl.spyctl_lib as lib


def handle_validate(file):
    if file:
        resrc_data = lib.load_resource_file(file)
    kind = resrc_data[lib.KIND_FIELD]
    cli.try_log(f"{kind} valid!")
