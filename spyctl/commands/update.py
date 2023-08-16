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


def handle_update_policy_modes(backup_dir: Optional[str]):
    ctx = cfg.get_current_context()
    print("Updating Guardian Policies")
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
        mode = pol_data[lib.SPEC_FIELD].get(
            lib.POL_MODE_FIELD, lib.POL_MODE_ENFORCE
        )
        if mode not in lib.POL_MODES:
            mode = lib.POL_MODE_ENFORCE
        lib.try_log(
            f"Setting mode for policy"
            f" '{policy[lib.METADATA_FIELD][lib.METADATA_UID_FIELD]}' to"
            f" '{mode}'"
        )
        pol_data[lib.SPEC_FIELD][lib.POL_MODE_FIELD] = mode
        pol_data = p.Policy(pol_data).as_dict()
        apply.handle_apply_policy(pol_data)
    print("Updating Suppression Policies")
    policies = api.get_policies(
        *ctx.get_api_data(),
        params={lib.METADATA_TYPE_FIELD: lib.POL_TYPE_TRACE},
    )
    for policy in policies:
        if backup_path:
            try:
                uid = policy[lib.METADATA_FIELD][lib.METADATA_UID_FIELD]
                outfile = Path.joinpath(backup_path, uid)
                print(f"Backing up {uid} tp {str(outfile)}")
                outfile.write_text(yaml.dump(policy, sort_keys=False))
            except Exception:
                import traceback

                s = traceback.format_exc()
                print(s)
                lib.err_exit("Error saving policy backups.. canceling")
        mode = policy[lib.SPEC_FIELD].get(
            lib.POL_MODE_FIELD, lib.POL_MODE_ENFORCE
        )
        if mode not in lib.POL_MODES:
            mode = lib.POL_MODE_ENFORCE
        lib.try_log(
            f"Setting mode for suppression policy"
            f" '{policy[lib.METADATA_FIELD][lib.METADATA_UID_FIELD]}' to"
            f" '{mode}'"
        )
        policy[lib.SPEC_FIELD][lib.POL_MODE_FIELD] = mode
        apply.handle_apply_suppression_policy(policy)
