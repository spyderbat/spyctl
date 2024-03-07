import spyctl.spyctl_lib as lib
import spyctl.cli as cli
import spyctl.commands.apply as apply


def handle_import(filename):
    all_data = lib.load_resource_file(filename)
    for resrc_data in all_data[lib.ITEMS_FIELD]:
        kind = resrc_data.get(lib.KIND_FIELD)
        if kind == lib.POL_KIND:
            r_type = resrc_data[lib.METADATA_FIELD][lib.METADATA_TYPE_FIELD]
            if r_type in lib.SUPPRESSION_POL_TYPES:
                apply.handle_apply_suppression_policy(resrc_data)
            else:
                cli.err_exit(f"Unsupported import policy type '{type}'.")
        elif kind == lib.NOTIFICATION_KIND:
            apply.handle_apply_notification_config(resrc_data)
        elif kind == lib.TARGET_KIND:
            apply.handle_apply_notification_target(resrc_data)
        else:
            cli.err_exit(f"Unsupported import kind '{kind}'.")
