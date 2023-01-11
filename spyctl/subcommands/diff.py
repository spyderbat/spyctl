import yaml

import spyctl.cli as cli
import spyctl.spyctl_lib as lib
import spyctl.resources.baselines as spyctl_baselines
import spyctl.resources.policies as spyctl_policies


def handle_diff(filename, with_file, latest):
    if not with_file and not latest:
        cli.err_exit("Nothing to diff")
    elif with_file and latest:
        cli.try_log("Latest and with-file detected. Only diffing with file.")
        latest = False
    resource = lib.load_resource_file(filename)
    resrc_kind = resource.get(lib.KIND_FIELD)
    if with_file:
        with_resource = lib.load_resource_file(with_file)
    else:
        with_resource = None
    if resrc_kind == lib.BASELINE_KIND:
        spyctl_baselines.diff_baseline(resource, with_resource, latest)
    elif resrc_kind == lib.POL_KIND:
        spyctl_policies.diff_policy(resource, with_resource, latest)
    else:
        cli.err_exit(f"The 'diff' command is not supported for {resrc_kind}")
