import json

import yaml
import spyctl.cli as cli
import spyctl.spyctl_lib as lib
import spyctl.config.secrets as secrets


def handle_apply(filename):
    try:
        with open(filename) as f:
            resrc_data = yaml.load(f, yaml.Loader)
    except Exception:
        try:
            resrc_data = json.load(filename)
        except Exception:
            cli.err_exit("Unable to load resource file.")
    if not isinstance(resrc_data, dict):
        cli.err_exit("Resource file does not contain a dictionary.")
    kind = resrc_data.get(lib.KIND_FIELD)
    if kind == secrets.SECRET_KIND:
        secrets.apply_secret(resrc_data)
