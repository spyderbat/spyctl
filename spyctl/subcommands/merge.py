import spyctl.spyctl_lib as lib
import spyctl.cli as cli
import spyctl.resources.baselines as b
import spyctl.resources.policies as p


def handle_merge(filename, with_file, latest, output):
    if not with_file and not latest:
        cli.err_exit("Nothing to merge")
    elif with_file and latest:
        cli.try_log(
            "--latest and --with-file detected. Using --with-file input.."
        )
        latest = False
    resource = lib.load_resource_file(filename)
    resrc_kind = resource.get(lib.KIND_FIELD)
    if with_file:
        with_resource = lib.load_resource_file(with_file)
    else:
        with_resource = None
    if resrc_kind == lib.BASELINE_KIND:
        result = b.merge_baseline(resource, with_resource, latest)
    elif resrc_kind == lib.POL_KIND:
        result = p.merge_policy(resource, with_resource, latest)
    else:
        cli.err_exit(f"The 'merge' command is not supported for {resrc_kind}")
    if result:
        cli.show(result.get_obj_data(), output)
