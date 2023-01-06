import spyctl.cli as cli
import spyctl.spyctl_lib as lib
import spyctl.resources.baselines as b
import spyctl.resources.policies as p


def handle_create_baseline(filename, output):
    resrc_data = lib.load_resource_file(filename)
    baseline = b.create_baseline(resrc_data)
    if output == lib.OUTPUT_DEFAULT:
        output = lib.OUTPUT_YAML
    cli.show(baseline, output)


def handle_create_policy(filename, output):
    resrc_data = lib.load_resource_file(filename)
    policy = p.create_policy(resrc_data)
    if output == lib.OUTPUT_DEFAULT:
        output = lib.OUTPUT_YAML
    cli.show(policy, output)
