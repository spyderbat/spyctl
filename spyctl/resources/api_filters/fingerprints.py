"""Handles generation of filters for use by the API instead of doing local
filtering.
"""
from typing import Dict, List
import spyctl.spyctl_lib as lib


def generate_pipeline(
    name_or_uid=None, type=None, latest_model=True, filters={}
):
    pipeline_items = []
    if type == lib.POL_TYPE_CONT or type == lib.POL_TYPE_SVC:
        schema = (
            f"{lib.MODEL_FINGERPRINT_PREFIX}:"
            f"{lib.MODEL_FINGERPRINT_SUBTYPE_MAP[type]}"
        )
    else:
        schema = f"{lib.MODEL_FINGERPRINT_PREFIX}:"
    pipeline_items.append(
        generate_fprint_api_filters(name_or_uid, schema, **filters)
    )
    if latest_model:
        pipeline_items.append({"latest_model": {}})
    return pipeline_items


def generate_fprint_api_filters(name_or_uid, schema, **filters) -> Dict:
    and_items = [{"schema": schema}]
    if name_or_uid:
        and_items.append(
            build_or_block(
                [lib.IMAGE_FIELD, lib.IMAGEID_FIELD, lib.CGROUP_FIELD],
                [name_or_uid],
            )
        )
    for key, values in filters.items():
        if isinstance(values, list) and len(values) > 1:
            and_items.append(build_or_block([key], values))
        else:
            if isinstance(values, list):
                value = values[0]
            else:
                value = values
            property = build_property(key)
            if not property:
                continue
            if "*" in value or "?" in value:
                value = lib.simple_glob_to_regex(value)
                and_items.append({"property": property, "re_match": value})
            else:
                and_items.append({"property": property, "equals": value})
    if len(and_items) > 1:
        rv = {"filter": {"and": and_items}}
    else:
        rv = {"filter": and_items[0]}
    return rv


def build_or_block(keys: str, values: List[str]):
    or_items = []
    for key in keys:
        for value in values:
            if "*" in value or "?" in value:
                value = lib.simple_glob_to_regex(value)
                or_items.append(
                    {"property": build_property(key), "re_match": value}
                )
            else:
                or_items.append(
                    {"property": build_property(key), "equals": value}
                )
    return {"or": or_items}


def build_property(key: str):
    if key == lib.MACHINES_FIELD:
        return "muid"
    if key == lib.POD_FIELD:
        return "pod_uid"
    if key == lib.CLUSTER_FIELD:
        return "cluster_uid"
    if key == lib.NAMESPACE_FIELD:
        return "metadata.namespace"
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
