import json
import time
from typing import Dict, List, Tuple

import yaml
import zulu
from tabulate import tabulate

import spyctl.cli as cli
import spyctl.spyctl_lib as lib
import spyctl.merge_lib as m_lib

FPRINT_KIND = "SpyderbatFingerprint"
FPRINT_TYPE_CONT = "container"
FPRINT_TYPE_SVC = "linux-service"
FPRINT_TYPES = {FPRINT_TYPE_CONT, FPRINT_TYPE_SVC}
GROUP_KIND = "FingerprintGroup"
FIRST_TIMESTAMP_FIELD = lib.FIRST_TIMESTAMP_FIELD
LATEST_TIMESTAMP_FIELD = lib.LATEST_TIMESTAMP_FIELD
FINGERPRINTS_FIELD = "fingerprints"
CONT_NAMES_FIELD = "containerNames"
CONT_IDS_FIELD = "containerIDs"
MACHINES_FIELD = "machines"
NOT_AVAILABLE = "N/A"

FPRINT_METADATA_MERGE_SCHEMA = m_lib.MergeSchema(
    lib.METADATA_FIELD,
    merge_functions={
        lib.METADATA_NAME_FIELD: m_lib.wildcard_merge,
        lib.METADATA_TYPE_FIELD: m_lib.all_eq_merge,
        lib.LATEST_TIMESTAMP_FIELD: m_lib.greatest_value_merge,
    },
)
FPRINT_MERGE_SCHEMAS = [
    FPRINT_METADATA_MERGE_SCHEMA,
    m_lib.SPEC_MERGE_SCHEMA,
]


class InvalidFingerprintError(Exception):
    pass


class InvalidFprintGroup(Exception):
    pass


class Fingerprint:
    required_keys = {
        lib.API_FIELD,
        lib.KIND_FIELD,
        lib.METADATA_FIELD,
        lib.SPEC_FIELD,
    }
    spec_required_keys = {lib.PROC_POLICY_FIELD, lib.NET_POLICY_FIELD}
    type_requred_selector = {
        FPRINT_TYPE_CONT: lib.CONT_SELECTOR_FIELD,
        FPRINT_TYPE_SVC: lib.SVC_SELECTOR_FIELD,
    }

    def __init__(self, fprint: Dict) -> None:
        if not isinstance(fprint, dict):
            raise InvalidFingerprintError(
                "Fingerprint should be a dictionary."
            )
        for key in self.required_keys:
            if key not in fprint:
                raise InvalidFingerprintError(
                    f"Fingerprint missing {key} field."
                )
        if not lib.valid_api_version(fprint[lib.API_FIELD]):
            raise InvalidFingerprintError(f"Invalid {lib.API_FIELD}.")
        if not lib.valid_kind(fprint[lib.KIND_FIELD], FPRINT_KIND):
            raise InvalidFingerprintError(f"Invalid {lib.KIND_FIELD}.")
        self.metadata = fprint[lib.METADATA_FIELD]
        if not isinstance(self.metadata, dict):
            raise InvalidFingerprintError("metadata is not a dictionary.")
        self.name = self.metadata.get(lib.METADATA_NAME_FIELD)
        if not self.name:
            raise InvalidFingerprintError("Invalid name.")
        self.type = self.metadata.get(lib.METADATA_TYPE_FIELD)
        if self.type not in FPRINT_TYPES:
            raise InvalidFingerprintError("Invalid type.")
        self.spec = fprint["spec"]
        if not isinstance(self.spec, dict):
            raise InvalidFingerprintError("Spec must be a dictionary.")
        for key in self.spec_required_keys.union(
            {self.type_requred_selector[self.type]}
        ):
            if key not in self.spec:
                raise InvalidFingerprintError(
                    f"Missing {key} from {lib.SPEC_FIELD} for {self.type}"
                    f" fingerprint."
                )
        self.selectors = {
            key: value
            for key, value in self.spec.items()
            if key.endswith("Selector")
        }
        for selector_name, selector in self.selectors.items():
            if not isinstance(selector, dict):
                raise InvalidFingerprintError(
                    f"{selector_name} must be a dictionary."
                )

    def as_dict(self) -> Dict:
        rv = {
            lib.API_FIELD: lib.API_VERSION,
            lib.KIND_FIELD: FPRINT_KIND,
            lib.METADATA_FIELD: self.metadata,
            lib.SPEC_FIELD: self.spec,
        }
        return rv


class FingerprintGroup:
    def __init__(self, fingerprint: Dict) -> None:
        self.fingerprints = {}
        self.first_timestamp = NOT_AVAILABLE
        self.latest_timestamp = NOT_AVAILABLE
        self.pods = set()
        self.namespaces = set()
        self.machines = set()

    def add_fingerprint(self, fingerprint: Dict):
        machine_uid = fingerprint[lib.METADATA_FIELD].get("muid")
        if machine_uid:
            self.machines.add(machine_uid)
        self.__update_first_timestamp(
            fingerprint[lib.METADATA_FIELD].get(FIRST_TIMESTAMP_FIELD)
        )
        self.__update_latest_timestamp(
            fingerprint[lib.METADATA_FIELD].get(LATEST_TIMESTAMP_FIELD)
        )
        fprint_id = fingerprint[lib.METADATA_FIELD].get("id")
        if fprint_id is None:
            fprint_id = lib.make_uuid()
        if (
            fprint_id not in self.fingerprints
            or LATEST_TIMESTAMP_FIELD
            not in self.fingerprints.get(fprint_id, {}).get(
                lib.METADATA_FIELD, {}
            )
        ):
            self.fingerprints[fprint_id] = fingerprint
        elif self.fingerprints[fprint_id][lib.METADATA_FIELD][
            LATEST_TIMESTAMP_FIELD
        ] <= fingerprint[lib.METADATA_FIELD].get(LATEST_TIMESTAMP_FIELD, 0):
            self.fingerprints[fprint_id] = fingerprint

    def __update_first_timestamp(self, timestamp):
        if timestamp is None:
            return
        if (
            self.first_timestamp is None
            or self.first_timestamp == NOT_AVAILABLE
        ):
            self.first_timestamp = timestamp
        elif timestamp < self.first_timestamp:
            self.first_timestamp = timestamp

    def __update_latest_timestamp(self, timestamp):
        if timestamp is None:
            return
        if (
            self.latest_timestamp is None
            or self.latest_timestamp == NOT_AVAILABLE
        ):
            self.latest_timestamp = timestamp
        elif timestamp > self.latest_timestamp:
            self.latest_timestamp = timestamp

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
        self.container_ids = set()
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
        container_name = fingerprint[lib.METADATA_FIELD].get(
            lib.CONT_NAME_FIELD
        )
        if container_name:
            self.container_names.add(container_name)
        container_id = fingerprint[lib.METADATA_FIELD].get(lib.CONT_ID_FIELD)
        if container_id:
            self.container_ids.add(container_id)

    def as_dict(self) -> Dict:
        rv = {
            lib.API_FIELD: lib.API_VERSION,
            lib.KIND_FIELD: GROUP_KIND,
            lib.METADATA_FIELD: {
                lib.IMAGE_FIELD: self.image,
                lib.IMAGEID_FIELD: self.image_id,
                FIRST_TIMESTAMP_FIELD: self.first_timestamp,
                LATEST_TIMESTAMP_FIELD: self.latest_timestamp,
            },
            lib.DATA_FIELD: {
                FINGERPRINTS_FIELD: list(self.fingerprints.values()),
                MACHINES_FIELD: list(self.machines),
                CONT_NAMES_FIELD: list(self.container_names),
                CONT_IDS_FIELD: list(self.container_ids),
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
                LATEST_TIMESTAMP_FIELD: self.latest_timestamp,
            },
            lib.DATA_FIELD: {
                FINGERPRINTS_FIELD: list(self.fingerprints.values()),
                MACHINES_FIELD: list(self.machines),
            },
        }
        return rv


def fprint_grp_output_summary(fingerprint_groups: Tuple) -> str:
    cont_fprint_grps, svc_fprint_grps = fingerprint_groups
    output_list = []
    if len(cont_fprint_grps) > 0:
        container_headers = [
            "IMAGE",
            "IMAGEID",
            "CONTAINERS",
            "FINGERPRINTS",
            "MACHINES",
            "FIRST_TIMESTAMP",
            "LATEST_TIMESTAMP",
        ]
        container_data = []
        for fprint_grp in cont_fprint_grps:
            container_data.append(cont_grp_output_data(fprint_grp))
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
            "LATEST_TIMESTAMP",
        ]
        service_data = []
        for fprint_grp in svc_fprint_grps:
            service_data.append(svc_grp_output_data(fprint_grp))
        service_data.sort(key=lambda x: x[0])
        service_tbl = tabulate(service_data, service_headers, tablefmt="plain")
        if len(output_list) > 0:
            service_tbl = "\n" + service_tbl
        output_list.append(service_tbl)
    return "\n".join(output_list)


def cont_grp_output_data(grp: Dict) -> List[str]:
    first_timestamp = grp[lib.METADATA_FIELD].get(
        FIRST_TIMESTAMP_FIELD, NOT_AVAILABLE
    )
    try:
        first_timestamp = (
            zulu.Zulu.fromtimestamp(first_timestamp).format(
                "YYYY-MM-ddTHH:mm:ss"
            )
            + "Z"
        )
    except Exception:
        pass
    latest_timestamp = grp[lib.METADATA_FIELD].get(
        LATEST_TIMESTAMP_FIELD, NOT_AVAILABLE
    )
    try:
        latest_timestamp = (
            zulu.Zulu.fromtimestamp(latest_timestamp).format(
                "YYYY-MM-ddTHH:mm:ss"
            )
            + "Z"
        )
    except Exception:
        pass
    rv = [
        grp[lib.METADATA_FIELD][lib.IMAGE_FIELD],
        grp[lib.METADATA_FIELD][lib.IMAGEID_FIELD][:12],
        len(grp[lib.DATA_FIELD][CONT_IDS_FIELD]),
        len(grp[lib.DATA_FIELD][FINGERPRINTS_FIELD]),
        len(grp[lib.DATA_FIELD][MACHINES_FIELD]),
        first_timestamp,
        latest_timestamp,
    ]
    return rv


def svc_grp_output_data(grp: Dict) -> List[str]:
    first_timestamp = grp[lib.METADATA_FIELD].get(
        FIRST_TIMESTAMP_FIELD, NOT_AVAILABLE
    )
    try:
        first_timestamp = (
            zulu.Zulu.fromtimestamp(first_timestamp).format(
                "YYYY-MM-ddTHH:mm:ss"
            )
            + "Z"
        )
    except Exception:
        pass
    latest_timestamp = grp[lib.METADATA_FIELD].get(
        LATEST_TIMESTAMP_FIELD, NOT_AVAILABLE
    )
    try:
        latest_timestamp = (
            zulu.Zulu.fromtimestamp(latest_timestamp).format(
                "YYYY-MM-ddTHH:mm:ss"
            )
            + "Z"
        )
    except Exception:
        pass
    rv = [
        grp[lib.METADATA_FIELD][lib.CGROUP_FIELD],
        len(grp[lib.DATA_FIELD][FINGERPRINTS_FIELD]),
        len(grp[lib.DATA_FIELD][MACHINES_FIELD]),
        first_timestamp,
        latest_timestamp,
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
) -> Tuple[List[Dict], List[Dict]]:
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
                try:
                    cont_fprint_grps[key] = ContainerFingerprintGroup(fprint)
                except Exception as e:
                    cli.try_log(
                        "Unable to create fingerprint group."
                        f" {' '.join(e.args)}"
                    )
            else:
                try:
                    cont_fprint_grps[key].add_fingerprint(fprint)
                except Exception as e:
                    cli.try_log(
                        "Unable to add fingerprint to group."
                        f" {' '.join(e.args)}"
                    )
        elif type == FPRINT_TYPE_SVC:
            cgroup = fprint[lib.SPEC_FIELD][lib.SVC_SELECTOR_FIELD][
                lib.CGROUP_FIELD
            ]
            key = cgroup
            if key not in svc_fprint_grps:
                try:
                    svc_fprint_grps[key] = ServiceFingerprintGroup(fprint)
                except Exception as e:
                    cli.try_log(
                        "Unable to create fingerprint group."
                        f" {' '.join(e.args)}"
                    )
            else:
                try:
                    svc_fprint_grps[key].add_fingerprint(fprint)
                except Exception as e:
                    cli.try_log(
                        "Unable to add fingerprint to group."
                        f" {' '.join(e.args)}"
                    )
    return (
        [grp.as_dict() for grp in cont_fprint_grps.values()],
        [grp.as_dict() for grp in svc_fprint_grps.values()],
    )
