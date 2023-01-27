import json
from typing import Dict

import spyctl.api as api
import spyctl.cli as cli
import spyctl.config.configs as cfg
import spyctl.resources.policies as p
import spyctl.spyctl_lib as lib


def handle_apply(filename):
    resrc_data = lib.load_resource_file(filename)
    kind = resrc_data.get(lib.KIND_FIELD)
    if kind == lib.POL_KIND:
        handle_apply_policy(resrc_data)
    else:
        cli.err_exit(f"The 'apply' command is not supported for {kind}")


def handle_apply_policy(policy: Dict):
    ctx = cfg.get_current_context()
    policy = p.Policy(policy)
    uid, api_data = p.get_data_for_api_call(policy)
    if uid:
        resp = api.put_policy_update(*ctx.get_api_data(), uid, api_data)
        if resp.status_code == 200:
            cli.try_log(f"Successfully updated policy {uid}")
    else:
        resp = api.post_new_policy(*ctx.get_api_data(), api_data)
        if resp and resp.text:
            uid = json.loads(resp.text).get("uid", "")
            cli.try_log(f"Successfully applied new policy with uid: {uid}")
