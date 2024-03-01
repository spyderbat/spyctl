import spyctl.spyctl_lib as lib
import spyctl.cli as cli
import spyctl.commands.apply as apply


def handle_import(filename):
    all_data = lib.load_resource_file(filename)
    for resrc_data in all_data[lib.ITEMS_FIELD]:
        kind = resrc_data.get(lib.KIND_FIELD)
        if kind == lib.POL_KIND:
            type = resrc_data[lib.METADATA_FIELD][lib.METADATA_TYPE_FIELD]
            if type in lib.SUPPRESSION_POL_TYPES:
                try:
                    apply.handle_apply_suppression_policy(resrc_data)
                except Exception as e:
                    cli.try_log(
                        "Failed to apply suppression policy: "
                        f"{resrc_data[lib.METADATA_FIELD][lib.METADATA_UID_FIELD]}"
                    )
            else:
                cli.err_exit(f"Unsupported import policy type '{type}'.")
