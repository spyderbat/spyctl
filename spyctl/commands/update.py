# A hidden command, used by support to assist with migrating documents
# that need to be updated

from typing import Optional
import spyctl.api as api
import spyctl.config.configs as cfg
import yaml
from pathlib import Path
import spyctl.resources.policies as p
import spyctl.spyctl_lib as lib
import spyctl.commands.apply as apply


def handle_update_response_actions(backup_dir: Optional[str]):
    ctx = cfg.get_current_context()
    policies = api.get_policies(*ctx.get_api_data())
    if backup_dir:
        backup_path = Path(backup_dir)

    for policy in policies:
        pol_data = p.policies_output([policy])
        if backup_path:
            try:
                uid = pol_data[lib.METADATA_FIELD][lib.METADATA_UID_FIELD]
                outfile = Path.joinpath(backup_path, uid)
                print(f"Backing up {uid} tp {str(outfile)}")
                outfile.write_text(yaml.dump(pol_data, sort_keys=False))
            except Exception:
                import traceback

                s = traceback.format_exc()
                print(s)
                lib.err_exit("Error saving policy backups.. canceling")
        del pol_data[lib.SPEC_FIELD][lib.RESPONSE_FIELD]
        pol_data = p.Policy(pol_data).as_dict()
        apply.handle_apply_policy(pol_data)
