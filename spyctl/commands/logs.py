from time import sleep
from typing import Dict, List, Tuple

import spyctl.api as api
import spyctl.cli as cli
import spyctl.config.configs as cfg
import spyctl.filter_resource as filt
import spyctl.spyctl_lib as lib


def handle_logs(
    resource: str,
    name_or_id: str,
    follow: bool,
    st: float,
    et: float,
    tail: int,
    timestamps: bool,
):
    if resource == lib.POLICIES_RESOURCE:
        handle_policy_logs(name_or_id, follow, str, et, tail, timestamps)


def handle_policy_logs(
    name_or_uid: str,
    follow: bool,
    st: float,
    et: float,
    tail: int,
    timestamps: bool,
):
    ctx = cfg.get_current_context()
    policies = api.get_policies(*ctx.get_api_data())
    policies = [
        (
            p[lib.METADATA_FIELD][lib.METADATA_UID_FIELD],
            p[lib.METADATA_FIELD][lib.METADATA_NAME_FIELD],
        )
        for p in filt.filter_obj(
            policies,
            [
                [lib.METADATA_FIELD, lib.METADATA_NAME_FIELD],
                [lib.METADATA_FIELD, lib.METADATA_UID_FIELD],
            ],
            name_or_uid,
        )
    ]
    if len(policies) == 0:
        cli.err_exit(f"No policies matching name_or_uid '{name_or_uid}'.")
    elif len(policies) > 1:
        cli.err_exit("Policy name is ambiguous, use uid.")
    policy = policies[0]
    policy_uid = policy[lib.METADATA_FIELD][lib.METADATA_UID_FIELD]
    if not follow:
        audit_events = api.get_audit_events_tail(
            *ctx,
            (st, et),
            policy_uid,
            tail,
        )
        show_policy_logs(audit_events, timestamps)
    else:
        while True:
            sleep(1)


def get_audit_events_follow(
    time,
    src_uid,
    tail: int = -1,
    msg_type=None,
    iterator=None,
) -> Tuple[List[Dict], str]:
    ctx = cfg.get_current_context()
    audit_events = api.get_audit_events_tail(
        *ctx, time, src_uid, tail, msg_type
    )
    if iterator:
        audit_events = scan_for_iterator()
    if not audit_events:
        return [], iterator
    new_iterator = encode_audit_iterator(audit_events[-1])
    return audit_events, new_iterator


def show_policy_logs(policy_audit_events: List[Dict], timestamps: bool):
    for event in policy_audit_events:
        if timestamps:
            ts = lib.epoch_to_zulu(event["time"]) + " -- "
        else:
            ts = ""
        msg = ts + event["description"]
        cli.show(msg, lib.OUTPUT_RAW)


def encode_audit_iterator(event: Dict):
    pass


def decode_audit_iterator(event: Dict):
    pass


def scan_for_iterator(iterator: str, events: List[Dict]):
    pass
