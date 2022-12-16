import json
import time
from typing import Dict, List, Tuple

import yaml
from tabulate import tabulate
import spyctl.spyctl_lib as lib
import zulu

FPRINT_KIND = "SpyderbatFingerprint"
FPRINT_TYPE_CONT = "container"
FPRINT_TYPE_SVC = "linux-service"
FPRINT_TYPES = {FPRINT_TYPE_CONT, FPRINT_TYPE_SVC}
GROUP_KIND = "FingerprintGroup"
FIRST_TIMESTAMP_FIELD = "firstTimestamp"
LAST_TIMESTAMP_FIELD = "lastTimestamp"
FINGERPRINTS_FIELD = "fingerprints"
CONT_NAMES_FIELD = "containerNames"
MACHINES_FIELD = "machines"


class InvalidFingerprintError(KeyError):
    ...


class InvalidFprintGroup(Exception):
    pass


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


class FingerprintGroup:
    def __init__(self, fingerprint: Dict) -> None:
        self.fingerprints = {}
        self.first_timestamp = None
        self.last_timestamp = None
        self.pods = set()
        self.namespaces = set()
        self.machines = set()

    def add_fingerprint(self, fingerprint: Dict):
        self.machines.add(fingerprint["muid"])
        self.__update_first_timestamp(fingerprint["valid_from"])
        self.__update_last_timestamp(fingerprint["time"])
        fprint_id = fingerprint["id"]
        if fprint_id not in self.fingerprints:
            self.fingerprints[fprint_id] = fingerprint
        elif self.fingerprints[fprint_id]["time"] <= fingerprint["time"]:
            self.fingerprints[fprint_id] = fingerprint

    def __update_first_timestamp(self, timestamp):
        if self.first_timestamp is None:
            self.first_timestamp = timestamp
        elif timestamp < self.first_timestamp:
            self.first_timestamp = timestamp

    def __update_last_timestamp(self, timestamp):
        if self.last_timestamp is None:
            self.last_timestamp = timestamp
        elif timestamp > self.last_timestamp:
            self.last_timestamp = timestamp

    def as_dict():
        return {}


class ContainerFingerprintGroup(FingerprintGroup):
    def __init__(self, fingerprint: Dict) -> None:
        super().__init__(fingerprint)
        self.image_id = fingerprint[lib.SPEC_FIELD][lib.CONT_SELECTOR_FIELD][
            lib.IMAGEID_FIELD
        ]
        self.image = fingerprint[lib.SPEC_FIELD][lib.CONT_SELECTOR_FIELD][
            lib.IMAGE_FIELD
        ]
        self.container_names = set()
        self.add_fingerprint(fingerprint)

    def add_fingerprint(self, fingerprint: Dict):
        super().add_fingerprint(fingerprint)
        image_id = fingerprint[lib.SPEC_FIELD][lib.CONT_SELECTOR_FIELD][
            lib.IMAGEID_FIELD
        ]
        if image_id != self.image_id:
            raise InvalidFprintGroup(
                "Container fprint group must all have the same image ID"
            )
        image = fingerprint[lib.SPEC_FIELD][lib.CONT_SELECTOR_FIELD][
            lib.IMAGE_FIELD
        ]
        if image != self.image:
            raise InvalidFprintGroup(
                "Container fprint group must all have the same image"
            )
        container_name = fingerprint[lib.SPEC_FIELD][lib.CONT_SELECTOR_FIELD][
            lib.CONT_NAME_FIELD
        ]
        self.container_names.add(container_name)

    def as_dict(self) -> Dict:
        rv = {
            lib.API_FIELD: lib.API_VERSION,
            lib.KIND_FIELD: GROUP_KIND,
            lib.METADATA_FIELD: {
                lib.IMAGE_FIELD: self.image,
                lib.IMAGEID_FIELD: self.image_id,
                FIRST_TIMESTAMP_FIELD: self.first_timestamp,
                LAST_TIMESTAMP_FIELD: self.last_timestamp,
            },
            lib.DATA_FIELD: {
                FINGERPRINTS_FIELD: list(self.fingerprints.values()),
                MACHINES_FIELD: list(self.machines),
                CONT_NAMES_FIELD: list(self.container_names),
            },
        }
        return rv


class ServiceFingerprintGroup(FingerprintGroup):
    def __init__(self, fingerprint: Dict) -> None:
        super().__init__(fingerprint)
        self.cgroup = fingerprint[lib.SPEC_FIELD][lib.SVC_SELECTOR_FIELD][
            lib.CGROUP_FIELD
        ]
        self.add_fingerprint(fingerprint)

    def add_fingerprint(self, fingerprint: Dict):
        super().add_fingerprint(fingerprint)
        cgroup = fingerprint[lib.SPEC_FIELD][lib.SVC_SELECTOR_FIELD][
            lib.CGROUP_FIELD
        ]
        if cgroup != self.cgroup:
            raise InvalidFprintGroup(
                "Linux service fprint group must all have the same cgroup"
            )

    def as_dict(self) -> Dict:
        rv = {
            lib.API_FIELD: lib.API_VERSION,
            lib.KIND_FIELD: GROUP_KIND,
            lib.METADATA_FIELD: {
                lib.CGROUP_FIELD: self.cgroup,
                FIRST_TIMESTAMP_FIELD: self.first_timestamp,
                LAST_TIMESTAMP_FIELD: self.last_timestamp,
            },
            lib.DATA_FIELD: {
                FINGERPRINTS_FIELD: list(self.fingerprints.values()),
                MACHINES_FIELD: list(self.machines),
            },
        }
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


def fprint_grp_output_summary(fingerprint_groups: Tuple) -> str:
    cont_fprint_grps, svc_fprint_grps = fingerprint_groups
    output_list = []
    if len(cont_fprint_grps) > 0:
        container_headers = [
            "IMAGE",
            "IMAGEID",
            "FINGERPRINTS",
            "MACHINES",
            "FIRST_TIMESTAMP",
            "LAST_TIMESTAMP",
        ]
        container_data = []
        for fprint_grp in cont_fprint_grps:
            container_data.append(container_group_summary(fprint_grp))
        container_data.sort(key=lambda x: [x[0]])
        container_tbl = tabulate(
            container_data, container_headers, tablefmt="plain"
        )
        output_list.append(container_tbl)
    if len(svc_fprint_grps) > 0:
        service_headers = [
            "CGROUP",
            "FINGERPRINTS",
            "MACHINES",
            "FIRST_TIMESTAMP",
            "LAST_TIMESTAMP",
        ]
        service_data = []
        for fprint_grp in svc_fprint_grps:
            service_data.append(service_group_summary(fprint_grp))
        service_data.sort(key=lambda x: x[0])
        service_tbl = tabulate(service_data, service_headers, tablefmt="plain")
        if len(output_list) > 0:
            service_tbl = "\n" + service_tbl
        output_list.append(service_tbl)
    return "\n".join(output_list)


def container_group_summary(grp: Dict) -> List[str]:
    rv = [
        grp[lib.METADATA_FIELD][lib.IMAGE_FIELD],
        grp[lib.METADATA_FIELD][lib.IMAGEID_FIELD][:12],
        len(grp[lib.DATA_FIELD][FINGERPRINTS_FIELD]),
        len(grp[lib.DATA_FIELD][MACHINES_FIELD]),
        str(
            zulu.Zulu.fromtimestamp(
                grp[lib.METADATA_FIELD][FIRST_TIMESTAMP_FIELD]
            ).format("YYYY-MM-ddTHH:mm:ss")
        )
        + "Z",
        str(
            zulu.Zulu.fromtimestamp(
                grp[lib.METADATA_FIELD][LAST_TIMESTAMP_FIELD]
            ).format("YYYY-MM-ddTHH:mm:ss")
        )
        + "Z",
    ]
    return rv


def service_group_summary(grp: Dict) -> List[str]:
    rv = [
        grp[lib.METADATA_FIELD][lib.CGROUP_FIELD],
        len(grp[lib.DATA_FIELD][FINGERPRINTS_FIELD]),
        len(grp[lib.DATA_FIELD][MACHINES_FIELD]),
        str(
            zulu.Zulu.fromtimestamp(
                grp[lib.METADATA_FIELD][FIRST_TIMESTAMP_FIELD]
            ).format("YYYY-MM-ddTHH:mm:ss")
        )
        + "Z",
        str(
            zulu.Zulu.fromtimestamp(
                grp[lib.METADATA_FIELD][LAST_TIMESTAMP_FIELD]
            ).format("YYYY-MM-ddTHH:mm:ss")
        )
        + "Z",
    ]
    return rv


def fprint_groups_output(groups: List[FingerprintGroup]) -> Dict:
    if len(groups) == 1:
        return groups[0]
    elif len(groups) > 1:
        return {
            lib.API_FIELD: lib.API_VERSION,
            lib.ITEMS_FIELD: groups,
        }
    else:
        return {}


def recursive_length(node_list):
    answer = 0
    for d in node_list:
        for x in d.values():
            if isinstance(x, list) and isinstance(x[0], dict):
                answer += recursive_length(x)
        answer += 1
    return answer


def latest_fingerprints(fingerprints: List[Dict]) -> List[Dict]:
    fprint_map = {}
    for fingerprint in fingerprints:
        fprint_id = fingerprint["id"]
        if fprint_id not in fprint_map:
            fprint_map[fprint_id] = fingerprint
        elif fprint_map[fprint_id]["time"] <= fingerprint["time"]:
            fprint_map[fprint_id] = fingerprint
    return list(fprint_map.values())


def make_fingerprint_groups(
    fingerprints: List[Dict],
) -> List[FingerprintGroup]:
    cont_fprint_grps: Dict[Tuple[str, str], ContainerFingerprintGroup] = {}
    svc_fprint_grps: Dict[str, ServiceFingerprintGroup] = {}
    for fprint in fingerprints:
        type = fprint[lib.METADATA_FIELD][lib.METADATA_TYPE_FIELD]
        if type == FPRINT_TYPE_CONT:
            image = fprint[lib.SPEC_FIELD][lib.CONT_SELECTOR_FIELD][
                lib.IMAGE_FIELD
            ]
            if not image:
                continue
            image_id = fprint[lib.SPEC_FIELD][lib.CONT_SELECTOR_FIELD][
                lib.IMAGEID_FIELD
            ]
            if not image_id:
                continue
            key = (image, image_id)
            if key not in cont_fprint_grps:
                cont_fprint_grps[key] = ContainerFingerprintGroup(fprint)
            else:
                cont_fprint_grps[key].add_fingerprint(fprint)
        elif type == FPRINT_TYPE_SVC:
            cgroup = fprint[lib.SPEC_FIELD][lib.SVC_SELECTOR_FIELD][
                lib.CGROUP_FIELD
            ]
            key = cgroup
            if key not in svc_fprint_grps:
                svc_fprint_grps[key] = ServiceFingerprintGroup(fprint)
            else:
                svc_fprint_grps[key].add_fingerprint(fprint)
    return (
        [grp.as_dict() for grp in cont_fprint_grps.values()],
        [grp.as_dict() for grp in svc_fprint_grps.values()],
    )
