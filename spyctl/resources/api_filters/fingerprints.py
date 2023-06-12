"""Handles generation of filters for use by the API instead of doing local
filtering.
"""
from typing import Dict, List
import spyctl.spyctl_lib as lib

# Filters for Container Fingerprints
CONT_FPRINT_FILTER_FIELDS = {
    lib.MACHINES_FIELD,
    lib.POD_FIELD,
    lib.NAMESPACE_FIELD,
    lib.CLUSTER_FIELD,
}


def generate_pipeline(type, latest_model=True, filters={}):
    pipeline_items = []
    if type == lib.POL_TYPE_CONT:
        pipeline_items.append(generate_container_fprint_api_filters(**filters))
    if latest_model:
        pipeline_items.append({"latest_model": {}})
    return {"pipeline": pipeline_items}


def generate_container_fprint_api_filters(**filters) -> Dict:
    and_items = [
        {
            "schema": f"{lib.MODEL_FINGERPRINT_PREFIX}:"
            f"{lib.MODEL_FINGERPRINT_SUBTYPE_MAP[lib.POL_TYPE_CONT]}"
        }
    ]
    for key, values in filters.items():
        if len(values) > 1:
            and_items.append(build_or_block(key, values))
        else:
            value = values[0]
            property = build_property(key)
            if not property:
                continue
            if "*" in value or "?" in value:
                value = lib.simple_glob_to_regex(value)
                and_items.append({"property": property, "re_match": value})
            else:
                and_items.append({"property": property, "equals": value})
    rv = {"filter": {"and", and_items}}
    return rv


def build_or_block(key: str, values: List[str]):
    or_items = []
    for value in values:
        if "*" in value or "?" in value:
            value = lib.simple_glob_to_regex(value)
            or_items.append(
                {"property": build_property(key), "re_match": value}
            )
        else:
            or_items.append({"property": build_property(key), "equals": value})
    return {"or", or_items}


def build_property(key: str):
    if key == lib.MACHINES_FIELD:
        return "muid"
    if key == lib.POD_FIELD:
        return "pod_uid"
    if key == lib.CLUSTER_FIELD:
        return "cluster_uid"
    if key == lib.NAMESPACE_FIELD:
        return "namespace"
    if key == lib.CGROUP_FIELD:
        return "cgroup"
    if key == lib.IMAGE_FIELD:
        return "image"
    if key == lib.IMAGEID_FIELD:
        return "image_id"
    if key == lib.CONTAINER_ID_FIELD:
        return "container_id"
    if key == lib.CONTAINER_NAME_FIELD:
        return "container_name"
