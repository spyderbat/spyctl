"""Handles generation of filters for use by the API instead of doing local
filtering.
"""
from typing import Dict, List
import spyctl.spyctl_lib as lib


def generate_pipeline(
    name_or_uid=None, type=None, latest_model=True, filters={}
):
    # TODO implement type when supported by analytics
    pipeline_items = []
    schema = lib.MODEL_AGENT_SCHEMA_PREFIX
    pipeline_items.append(
        generate_fprint_api_filters(name_or_uid, schema, **filters)
    )
    if latest_model:
        pipeline_items.append({"latest_model": {}})
    return pipeline_items


def generate_metrics_pipeline():
    pipeline_items = []
    schema = lib.EVENT_AGENT_METRICS_PREFIX
    pipeline_items.append(generate_fprint_api_filters(None, schema))
    pipeline_items.append({"latest_model": {}})
    return pipeline_items


def generate_fprint_api_filters(name_or_uid, schema, **filters) -> Dict:
    and_items = [{"schema": schema}]
    if name_or_uid:
        and_items.append(
            build_or_block(
                [lib.AGENT_ID, lib.AGENT_HOSTNAME, lib.MACHINES_FIELD],
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


def build_or_block(keys: List[str], values: List[str]):
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
    if key == lib.AGENT_ID:
        return "id"
    if key == lib.AGENT_HOSTNAME:
        return "hostname"
