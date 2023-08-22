import binascii
import json
from base64 import urlsafe_b64decode as b64url_d
from base64 import urlsafe_b64encode as b64url
from time import sleep
import time
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
    full: bool,
    since_iterator: str,
):
    if resource == lib.POLICIES_RESOURCE:
        handle_policy_logs(
            name_or_id, follow, st, et, tail, timestamps, full, since_iterator
        )
    else:
        cli.err_exit(f"The 'logs' command is not supported for '{resource}'")


def handle_policy_logs(
    name_or_uid: str,
    follow: bool,
    st: float,
    et: float,
    tail: int,
    timestamps: bool,
    full: bool,
    since_iterator: str,
):
    ctx = cfg.get_current_context()
    policies = api.get_policies(*ctx.get_api_data())
    policies = [
        p
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
        if since_iterator:
            st, since_id = decode_audit_iterator(since_iterator)
            time = (st, et)
        else:
            time = (st, et)
            since_id = None
        audit_events = api.get_audit_events_tail(
            *ctx.get_api_data(), time, policy_uid, tail, since_id=since_id
        )
        show_policy_logs(audit_events, timestamps, full)
        if audit_events:
            e_time = audit_events[-1]["time"]
            e_id = audit_events[-1]["id"]
            iterator = encode_audit_iterator(e_time, e_id)
        else:
            iterator = "N/A"
        cli.try_log(f"Last Log Iterator: {iterator}")
    else:
        get_audit_events_follow(
            st,
            policy_uid,
            timestamps,
            full,
            tail,
            since_iterator=since_iterator,
        )


def get_audit_events_follow(
    st,
    src_uid,
    timestamps: bool,
    full: bool,
    tail: int = -1,
    msg_type=None,
    since_iterator=None,
) -> Tuple[List[Dict], str]:
    ctx = cfg.get_current_context()
    while True:
        et = time.time()
        if since_iterator:
            st, since_id = decode_audit_iterator(since_iterator)
            q_time = (st, et)
        else:
            q_time = (st, et)
            since_id = None
        audit_events = api.get_audit_events_tail(
            *ctx.get_api_data(),
            q_time,
            src_uid,
            tail,
            msg_type,
            since_id=since_id,
            disable_pbar=True,
        )
        tail = -1
        show_policy_logs(audit_events, timestamps, full)
        if audit_events:
            e_time = audit_events[-1]["time"]
            e_id = audit_events[-1]["id"]
            since_iterator = encode_audit_iterator(e_time, e_id)
        sleep(2.5)


def show_policy_logs(
    policy_audit_events: List[Dict], timestamps: bool, full: bool
):
    for event in policy_audit_events:
        if timestamps:
            ts = lib.epoch_to_zulu(event["time"]) + " -- "
        else:
            ts = ""
        if full:
            log = json.dumps(event)
        else:
            log = event["description"]
        msg = f"{ts}{log}"
        cli.show(msg, lib.OUTPUT_RAW)


def encode_audit_iterator(time: float, id: str):
    time -= 60
    iterator_bytes = f"{time}|{id}".encode("ascii")
    iterator = b64url(iterator_bytes).decode("ascii").strip("=")
    return iterator


def decode_audit_iterator(iterator: str):
    try:
        try:
            b = b64url_d(iterator + "==")
        except binascii.Error:
            try:
                b = b64url_d(iterator + "=")
            except binascii.Error:
                b = b64url_d(iterator)
        iterator_str = b.decode("ascii")
        time, id = iterator_str.split("|")
    except Exception:
        cli.err_exit("Unable to parse iterator")
    return float(time), id
