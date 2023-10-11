import spyctl.cli as cli
import spyctl.api as api
import spyctl.config.configs as cfg
import spyctl.spyctl_lib as lib
from tabulate import tabulate
from typing import Dict, List
from dataclasses import dataclass

TARGETS_HEADERS = ["NAME", "AGE", "TYPE", "DESTINATIONS"]


@dataclass
class Emails:
    emails: list

    @property
    def dest(self):
        if self.emails:
            return "\n".join(self.emails)
        else:
            return lib.NOT_AVAILABLE


@dataclass
class Slack:
    url: str = None

    @property
    def dest(self):
        if self.url:
            return self.url
        else:
            return lib.NOT_AVAILABLE


@dataclass
class SNS:
    cross_account_iam_role: str = None
    sns_topic_arn: str = None

    @property
    def dest(self):
        if self.sns_topic_arn:
            return self.sns_topic_arn
        else:
            return lib.NOT_AVAILABLE


@dataclass
class Users:
    users: list

    @property
    def dest(self):
        if self.emails:
            return "\n".join(self.emails)
        else:
            return lib.NOT_AVAILABLE


@dataclass
class Webhook:
    url: str = None
    no_tls_validation: bool = None

    @property
    def dest(self):
        if self.url:
            return self.url
        else:
            return lib.NOT_AVAILABLE


def targets_summary_output(targets: Dict):
    row_data = []
    for tgt_name, tgt_data in targets.items():
        types = []
        dest_count = 0
        for tgt_type in lib.TGT_TYPES:
            if tgt_type in tgt_data:
                dest_count += len(tgt_data[tgt_type])
                types.append(tgt_type)
        if lib.DATA_FIELD not in tgt_data:
            age = lib.NOT_AVAILABLE
        else:
            data = tgt_data[lib.DATA_FIELD]
            if lib.NOTIF_CREATE_TIME in data:
                age = lib.calc_age(data[lib.NOTIF_CREATE_TIME])
            else:
                age = lib.NOT_AVAILABLE
        if len(types) == 1:
            type = types[0]
        elif len(types) > 1:
            type = f"{len(types)} types"
        else:
            type = lib.NOT_AVAILABLE
        row_data.append([tgt_name, age, type, dest_count])
    return tabulate(row_data, TARGETS_HEADERS, "plain")


def targets_wide_output(targets: Dict):
    row_data = []
    for tgt_name, tgt_data in targets.items():
        types = []
        dests = {}
        for tgt_type in lib.TGT_TYPES:
            if tgt_type in tgt_data:
                if tgt_type == lib.TGT_TYPE_EMAIL:
                    dests[tgt_type] = Emails(tgt_data[tgt_type])
                elif tgt_type == lib.TGT_TYPE_SLACK:
                    dests[tgt_type] = Slack(**tgt_data[tgt_type])
                elif tgt_type == lib.TGT_TYPE_SNS:
                    dests[tgt_type] = SNS(**tgt_data[tgt_type])
                elif tgt_type == lib.TGT_TYPE_USERS:
                    dests[tgt_type] = Users(tgt_data[tgt_type])
                elif tgt_type == lib.TGT_TYPE_WEBHOOK:
                    dests[tgt_type] = Webhook(**tgt_data[tgt_type])
                else:
                    cli.err_exit("Unsupported tgt type.")
                types.append(tgt_type)
        if lib.DATA_FIELD not in tgt_data:
            age = lib.NOT_AVAILABLE
        else:
            data = tgt_data[lib.DATA_FIELD]
            if lib.NOTIF_CREATE_TIME in data:
                age = lib.calc_age(data[lib.NOTIF_CREATE_TIME])
            else:
                age = lib.NOT_AVAILABLE
        if types:
            for i, tgt_type in enumerate(types):
                if i == 0:
                    row_data.append(
                        [tgt_name, age, tgt_type, dests[tgt_type].dest]
                    )
                else:
                    row_data.append(["", "", tgt_type, dests[tgt_type].dest])
        else:
            row_data.append(
                [tgt_name, age, lib.NOT_AVAILABLE, lib.NOT_AVAILABLE]
            )
    return tabulate(row_data, TARGETS_HEADERS, "plain")
