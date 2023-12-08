import time
from copy import deepcopy
from dataclasses import dataclass
from typing import Dict, Optional

import yaml
from tabulate import tabulate

import spyctl.api as api
import spyctl.cli as cli
import spyctl.config.configs as cfg
import spyctl.spyctl_lib as lib

TARGETS_HEADERS = ["NAME", "ID", "AGE", "TYPE", "DESTINATIONS"]

TGT_DEFAULT = {"NAME": {"data": {}, "description": ""}}

TGT_DEFAULT_DSTS = {
    lib.DST_TYPE_EMAIL: ["example@example.com"],
    lib.DST_TYPE_SLACK: {
        "url": "https://hooks.slack.com/services/xxxxxxxxxxx/xxxxxxxxxxx/xxxxxxxxxxxxxxxxxxxxxxxx"  # noqa: E501
    },
    lib.DST_TYPE_SNS: {
        "sns_topic_arn": "arn:aws:sns:region:account-id:topic-name"
    },
    lib.DST_TYPE_WEBHOOK: {
        "url": "https://my.webhook.example/location/of/webhook",
        "no_tls_validation": True,
    },
}


@dataclass
class Emails:
    emails: list

    @property
    def sum_dest(self):
        if self.emails:
            return "\n".join(self.emails)
        else:
            return lib.NOT_AVAILABLE


@dataclass
class Slack:
    url: str = None

    @property
    def sum_dest(self):
        if self.url:
            return self.url
        else:
            return lib.NOT_AVAILABLE

    @property
    def dest(self):
        return {"url": self.url}


@dataclass
class SNS:
    cross_account_iam_role: str = None
    sns_topic_arn: str = None

    @property
    def sum_dest(self):
        if self.sns_topic_arn:
            return self.sns_topic_arn
        else:
            return lib.NOT_AVAILABLE

    @property
    def dest(self):
        rv = {}
        if self.cross_account_iam_role:
            rv.update({"cross_account_iam_role": self.cross_account_iam_role})
        if self.sns_topic_arn:
            rv.update({"sns_topic_arn": self.sns_topic_arn})
        return rv


@dataclass
class Users:
    users: list

    @property
    def sum_dest(self):
        if self.emails:
            return "\n".join(self.emails)
        else:
            return lib.NOT_AVAILABLE


@dataclass
class Webhook:
    url: str = None
    no_tls_validation: bool = None

    @property
    def sum_dest(self):
        if self.url:
            return self.url
        else:
            return lib.NOT_AVAILABLE

    @property
    def dest(self):
        rv = {"url": self.url}
        if self.no_tls_validation:
            rv.update({"no_tls_validation": self.no_tls_validation})
        return rv


def create_target(name, type) -> Dict:
    target = Target(initial_name=name, initial_type=type)
    return target.as_dict()


class Target:
    def __init__(
        self,
        target_resource: Dict = None,
        backend_target: Dict[str, Dict] = None,
        initial_name=None,
        initial_type=None,
    ) -> None:
        if target_resource:
            self.from_resource(target_resource)
        else:
            if backend_target is None:
                backend_target = deepcopy(TGT_DEFAULT)
            name, tgt_data = next(iter(backend_target.items()))
            if initial_name:
                self.name = initial_name
            else:
                self.name = name
            self.description = tgt_data.get(lib.TGT_DESCRIPTION_FIELD)
            if initial_type:
                self.destination = {
                    initial_type: TGT_DEFAULT_DSTS[initial_type]
                }
            else:
                self.destination = None
                for dst_type in lib.DST_TYPES:
                    if dst_type in tgt_data:
                        self.destination = {dst_type: tgt_data[dst_type]}
                        break
            data = tgt_data.get(lib.DATA_FIELD, {})
            if lib.ID_FIELD in data:
                self.id = data.pop(lib.ID_FIELD)
            else:
                self.id = "notif_tgt:" + lib.make_uuid()
            self.additional_data = data

    def from_resource(self, tgt_resource: Dict):
        tgt_resource = deepcopy(tgt_resource)
        self.name = tgt_resource[lib.METADATA_FIELD].pop(
            lib.METADATA_NAME_FIELD
        )
        self.id = tgt_resource[lib.METADATA_FIELD].pop(lib.METADATA_UID_FIELD)
        self.description = tgt_resource[lib.METADATA_FIELD].pop(
            lib.TGT_DESCRIPTION_FIELD, ""
        )
        self.additional_data = tgt_resource[lib.METADATA_FIELD]
        self.destination = tgt_resource[lib.SPEC_FIELD]

    def as_dict(self) -> Dict:
        rv = {
            lib.API_FIELD: lib.API_VERSION,
            lib.KIND_FIELD: lib.TARGET_KIND,
            lib.METADATA_FIELD: {
                lib.METADATA_UID_FIELD: self.id,
                lib.METADATA_NAME_FIELD: self.name,
                lib.TGT_DESCRIPTION_FIELD: self.description,
                **self.additional_data,
            },
            lib.SPEC_FIELD: self.destination,
        }
        if not self.description:
            rv[lib.METADATA_FIELD].pop(lib.TGT_DESCRIPTION_FIELD)
        return rv

    def as_target(self) -> Dict:
        rv = {
            self.name: {
                **self.destination,
                "data": {lib.ID_FIELD: self.id, **self.additional_data},
            }
        }
        if self.description:
            rv[self.name][lib.TGT_DESCRIPTION_FIELD] = self.description
        return rv

    def set_last_update_time(self):
        now = time.time()
        self.additional_data[lib.NOTIF_LAST_UPDATED] = now
        if lib.NOTIF_CREATE_TIME not in self.additional_data:
            self.additional_data[lib.NOTIF_CREATE_TIME] = now


class NotificationTarget:
    def __init__(self, name, tgt_data=None) -> None:
        self.name = name
        self.old_name = name
        self.type = None
        self.dst_data = None
        if tgt_data:
            self.new = False
            self.changed = False
            self.data = tgt_data.get(lib.DATA_FIELD, {})
            self.data[lib.DST_DESCRIPTION] = self.name
            for dst_type in lib.DST_TYPES:
                if dst_type in tgt_data:
                    self.type = dst_type
                    self.dst_data = tgt_data[dst_type]

                    break
        else:
            now = time.time()
            self.new = True
            self.changed = True
            self.data = {
                lib.NOTIF_CREATE_TIME: now,
                lib.NOTIF_LAST_UPDATED: now,
                lib.ID_FIELD: "notif_tgt:" + lib.make_uuid(),
                lib.DST_DESCRIPTION: self.name,
            }

    def update_name(self, new_name):
        if new_name != self.name:
            self.changed = True
            self.name = new_name
            self.data[lib.DST_DESCRIPTION] = self.name

    def update_destination(self, dst_type, dst_data):
        if self.type != dst_type or self.dst_data != dst_data:
            self.changed = True
            self.type = dst_type
            self.dst_data = dst_data

    def set_last_updated(self, time: float):
        self.data[lib.NOTIF_LAST_UPDATED] = time

    @property
    def tgt_type_name(self) -> Optional[str]:
        if self.type:
            return lib.DST_TYPE_TO_NAME[self.type]

    @property
    def tgt_data(self) -> Dict:
        return {
            self.name: {self.type: self.dst_data, lib.DATA_FIELD: self.data}
        }

    @property
    def editable_tgt_data(self) -> Dict:
        rv_dict = {self.name: {self.type: self.dst_data}}
        return rv_dict

    @property
    def dst_yaml(self):
        return yaml.dump(self.tgt_data)


def targets_summary_output(targets: Dict):
    row_data = []
    for tgt_name, tgt_data in targets.items():
        types = []
        dest_count = 0
        for tgt_type in lib.DST_TYPES:
            if tgt_type in tgt_data:
                dest_count += len(tgt_data[tgt_type])
                types.append(tgt_type)
        if lib.DATA_FIELD not in tgt_data:
            age = lib.NOT_AVAILABLE
            tgt_id = lib.NOT_AVAILABLE
        else:
            data = tgt_data[lib.DATA_FIELD]
            if lib.NOTIF_CREATE_TIME in data:
                age = lib.calc_age(data[lib.NOTIF_CREATE_TIME])
            else:
                age = lib.NOT_AVAILABLE
            if lib.ID_FIELD in data:
                tgt_id = data[lib.ID_FIELD]
            else:
                tgt_id = lib.NOT_AVAILABLE
        if len(types) == 1:
            type = types[0]
        elif len(types) > 1:
            type = f"{len(types)} types"
        else:
            type = lib.NOT_AVAILABLE
        row_data.append([tgt_name, tgt_id, age, type, dest_count])
    row_data.sort(key=lambda row: row[0].lower())
    return tabulate(row_data, TARGETS_HEADERS, "plain")


def targets_wide_output(targets: Dict):
    row_data = []
    for tgt_name, tgt_data in targets.items():
        types = []
        dests = {}
        for tgt_type in lib.DST_TYPES:
            if tgt_type in tgt_data:
                if tgt_type == lib.DST_TYPE_EMAIL:
                    dests[tgt_type] = Emails(tgt_data[tgt_type])
                elif tgt_type == lib.DST_TYPE_SLACK:
                    dests[tgt_type] = Slack(**tgt_data[tgt_type])
                elif tgt_type == lib.DST_TYPE_SNS:
                    dests[tgt_type] = SNS(**tgt_data[tgt_type])
                elif tgt_type == lib.DST_TYPE_USERS:
                    dests[tgt_type] = Users(tgt_data[tgt_type])
                elif tgt_type == lib.DST_TYPE_WEBHOOK:
                    dests[tgt_type] = Webhook(**tgt_data[tgt_type])
                else:
                    cli.err_exit("Unsupported tgt type.")
                types.append(tgt_type)
        if lib.DATA_FIELD not in tgt_data:
            age = lib.NOT_AVAILABLE
            tgt_id = lib.NOT_AVAILABLE
        else:
            data = tgt_data[lib.DATA_FIELD]
            if lib.NOTIF_CREATE_TIME in data:
                age = lib.calc_age(data[lib.NOTIF_CREATE_TIME])
            else:
                age = lib.NOT_AVAILABLE
            if lib.ID_FIELD in data:
                tgt_id = data[lib.ID_FIELD]
            else:
                tgt_id = lib.NOT_AVAILABLE
        if types:
            for i, tgt_type in enumerate(types):
                if i == 0:
                    row_data.append(
                        [
                            tgt_name,
                            tgt_id,
                            age,
                            tgt_type,
                            dests[tgt_type].sum_dest,
                        ]
                    )
                else:
                    row_data.append(
                        ["", tgt_id, "", tgt_type, dests[tgt_type].sum_dest]
                    )
        else:
            row_data.append(
                [tgt_name, tgt_id, age, lib.NOT_AVAILABLE, lib.NOT_AVAILABLE]
            )
    row_data.sort(key=lambda row: row[0].lower())
    return tabulate(row_data, TARGETS_HEADERS, "plain")


def get_target(name_or_uid: str, targets: Dict = None) -> Optional[Target]:
    if not targets:
        ctx = cfg.get_current_context()
        n_pol = api.get_notification_policy(*ctx.get_api_data())
        if not n_pol or not isinstance(n_pol, dict):
            cli.err_exit("Could not load notification targets")
        targets = n_pol.get(lib.TARGETS_FIELD, {})
    if name_or_uid in targets:
        return Target(backend_target={name_or_uid: targets[name_or_uid]})
    for tgt_name, tgt_data in targets.items():
        tgt_obj = Target(backend_target={tgt_name: tgt_data})
        if tgt_obj.id == name_or_uid:
            return tgt_obj


def put_and_get_notif_pol(nt: NotificationTarget, delete_name=None):
    ctx = cfg.get_current_context()
    notif_pol = api.get_notification_policy(*ctx.get_api_data())
    targets: Dict = notif_pol.get(lib.TARGETS_FIELD, {})
    if delete_name:
        targets.pop(delete_name, None)
    if nt:
        targets.update(nt.tgt_data)
    notif_pol[lib.TARGETS_FIELD] = targets
    api.put_notification_policy(*ctx.get_api_data(), notif_pol)
    rv_pol = api.get_notification_policy(*ctx.get_api_data())
    return rv_pol
