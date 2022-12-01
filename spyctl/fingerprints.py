import json
import time
from typing import Dict, List

import yaml

FPRINT_KIND = "SpyderbatFingerprint"
FPRINT_TYPE_CONT = "container"
FPRINT_TYPE_SVC = "service"
FPRINT_TYPES = {FPRINT_TYPE_CONT, FPRINT_TYPE_SVC}


class InvalidFingerprintError(KeyError):
    ...


class Fingerprint:
    def __init__(self, fprint) -> None:
        req_keys = ["apiVersion", "kind", "spec", "metadata"]
        for key in req_keys:
            if key not in fprint:
                raise InvalidFingerprintError(key)
        self.fprint = fprint
        if self.kind != FPRINT_KIND:
            raise InvalidFingerprintError(f"Invalid kind - {self.kind}")
        if "name" not in self.metadata:
            raise InvalidFingerprintError("metadata.name")
        if self.fprint_type not in FPRINT_TYPES:
            raise InvalidFingerprintError(
                f"{self.fprint_type} is not a valid fingerprint type"
            )
        self.calc_lengths()
        to_metadata = ["time", "valid_from", "valid_to"]
        for key in to_metadata:
            if key in self.fprint:
                self.metadata[key] = self.fprint[key]

    @property
    def metadata(self) -> Dict:
        return self.fprint["metadata"]

    @property
    def fprint_type(self) -> str:
        return self.metadata.get("type")

    @property
    def kind(self) -> str:
        return self.fprint["kind"]

    def get_id(self):
        return self.fprint.get("id")

    def preview_str(self, include_yaml=False):
        fprint_yaml = yaml.dump(
            dict(spec=self.fprint["spec"]), sort_keys=False
        )
        return (
            f"{self.metadata['name']}{self.suppr_str} --"
            + f" proc_nodes: {self.fprint['proc_fprint_len']},"
            + f" ingress_nodes: {self.fprint['ingress_len']},"
            + f" egress_nodes: {self.fprint['egress_len']}"
            + (f"|{fprint_yaml}" if include_yaml else "")
        )

    def get_output(self):
        copy_fields = ["apiVersion", "kind", "metadata", "spec"]
        rv = dict()
        for key in copy_fields:
            rv[key] = self.fprint[key]
        return rv

    def set_num_suppressed(self, num: int):
        self.suppr_str = f" ({num} suppressed)"

    def calc_lengths(self):
        proc_fprint_len = 0
        node_queue = self.fprint["spec"]["processPolicy"].copy()
        for node in node_queue:
            proc_fprint_len += 1
            if "children" in node:
                node_queue += node["children"]
        ingress_len = len(self.fprint["spec"]["networkPolicy"]["ingress"])
        egress_len = len(self.fprint["spec"]["networkPolicy"]["egress"])
        self.fprint["proc_fprint_len"] = proc_fprint_len
        self.fprint["ingress_len"] = ingress_len
        self.fprint["egress_len"] = egress_len

    @staticmethod
    def prepare_many(objs: List) -> List:
        latest: Dict[str, Fingerprint] = {}
        # keep only the latest fingerprints with the same id
        # can only filter out fingerprints that have ids, aka directly
        # from the api
        ex_n = 0
        obj: Fingerprint
        for obj in objs:
            f_id = obj.get_id()
            if f_id is None:
                latest[ex_n] = obj
                ex_n += 1
                continue
            if f_id not in latest:
                latest[f_id] = obj
            elif latest[f_id].fprint["time"] < obj.fprint["time"]:
                latest[f_id] = obj
        checksums = {}
        for obj in latest.values():
            checksum = obj.metadata["checksum"]
            if checksum not in checksums:
                checksums[checksum] = {"print": obj, "suppressed": 0}
            else:
                entry = checksums[checksum]
                entry["suppressed"] += 1
                obj.set_num_suppressed(entry["suppressed"])
                entry["print"] = obj
        rv = [val["print"] for val in checksums.values()]
        rv.sort(key=lambda f: f.preview_str())
        return rv


def fingerprint_summary(fingerprints: List[Dict]) -> List[str]:
    checksums = {}
    for fprint in fingerprints:
        proc_pol_len = recursive_length(fprint["spec"]["processPolicy"])
        ingress_len = len(fprint["spec"]["networkPolicy"]["ingress"])
        egress_len = len(fprint["spec"]["networkPolicy"]["egress"])
        metadata = fprint["metadata"]
        checksum = metadata["checksum"]
        time_created = time.strftime(
            "%a, %d %b %Y %H:%M:%S %Z", time.localtime(metadata["valid_from"])
        )
        time_emitted = time.strftime(
            "%a, %d %b %Y %H:%M:%S %Z", time.localtime(metadata["time"])
        )
        type = metadata["type"]
        if type == FPRINT_TYPE_CONT:
            container_selector = fprint["spec"].get("containerSelector", {})
            key = (
                "Container Name:"
                + f" {container_selector.get('containerName', {})} |"
                + f" Image Name: {container_selector.get('image', '')} |"
                + " Short Img ID:"
                + f" {container_selector.get('imageID', '')[:12]}"
            )
            s = (
                f"\t\tMachine UID: {metadata['muid']} | "
                + f" Time Created: {time_created} |"
                + f" Time Emitted: {time_emitted}\n"
                + f"\t\tProc Policy Len: {proc_pol_len} | Ingress Len:"
                + f" {ingress_len} | Egress Len: {egress_len}"
            )
            if checksum not in checksums:
                checksums[checksum] = (
                    proc_pol_len + ingress_len + egress_len,
                    key,
                    s,
                )
        elif type == FPRINT_TYPE_SVC:
            service_selector = fprint["spec"].get("serviceSelector", {})
            key = (
                "Service Cgroup:" + f" {service_selector.get('cgroup', {})}\n"
            )
            s = (
                f"\t\tMachine UID: {metadata['muid']}"
                + f" Time Created: {time_created} |"
                + f" Time Emitted: {time_emitted}\n"
                + f"\t\tProc Policy Len: {proc_pol_len} | Ingress Len:"
                + f" {ingress_len} | Egress Len: {egress_len}"
            )
            if checksum not in checksums:
                checksums[checksum] = (
                    proc_pol_len + ingress_len + egress_len,
                    key,
                    s,
                )
    str_list = [
        "Unique Fingerprint Summary",
        f"\tTotal Fingerprints Gathered: {len(fingerprints)} -- Unique"
        " Fingerprints Shown: {len(checksums)}",
        "-----",
    ]
    sum_list = [
        tup
        for tup in sorted(
            checksums.values(), key=lambda tup: tup[0], reverse=True
        )
    ]
    sum_tbl = {}
    for _, key, s in sum_list:
        sum_tbl.setdefault(key, [])
        sum_tbl[key].append(s)
    for key, s_list in sum_tbl.items():
        str_list.append(key)
        str_list.extend(s_list)
    rv = "\n".join(str_list)
    return rv


def recursive_length(node_list):
    answer = 0
    for d in node_list:
        for x in d.values():
            if isinstance(x, list) and isinstance(x[0], dict):
                answer += recursive_length(x)
        answer += 1
    return answer
