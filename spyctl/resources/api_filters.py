"""Handles generation of filters for use by the API instead of doing local
filtering.
"""

from typing import Dict, List, Union
import spyctl.spyctl_lib as lib


class API_Filter:
    property_map = {}
    name_or_uid_props: []

    @classmethod
    def generate_pipeline(
        cls, schema, name_or_uid=None, latest_model=True, filters={}
    ) -> List:
        pipeline_items = []
        pipeline_items.append(
            cls.generate_fprint_api_filters(schema, name_or_uid, **filters)
        )
        if latest_model:
            pipeline_items.append({"latest_model": {}})
        return []

    @classmethod
    def generate_fprint_api_filters(
        cls,
        schema,
        name_or_uid: Union[str, List],
        **filters,
    ) -> Dict:
        and_items = [{"schema": schema}]
        if name_or_uid:
            and_items.append(
                cls.build_or_block(
                    cls.name_or_uid_props,
                    [name_or_uid],
                )
            )
        for key, values in filters.items():
            if isinstance(values, list) and len(values) > 1:
                and_items.append(cls.build_or_block([key], values))
            else:
                if isinstance(values, list):
                    value = values[0]
                else:
                    value = values
                property = cls.build_property(key)
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

    @classmethod
    def build_or_block(cls, keys: List[str], values: List[str]):
        or_items = []
        for key in keys:
            for value in values:
                if "*" in value or "?" in value:
                    value = lib.simple_glob_to_regex(value)
                    or_items.append(
                        {
                            "property": cls.build_property(key),
                            "re_match": value,
                        }
                    )
                else:
                    or_items.append(
                        {
                            "property": cls.build_property(key),
                            "equals": value,
                        }
                    )
        return {"or": or_items}

    @classmethod
    def build_property(cls, key: str, property_map: Dict):
        return cls.property_map[key]


class Agents(API_Filter):
    property_map = {
        lib.MACHINES_FIELD: "muid",
        lib.AGENT_ID: "id",
        lib.AGENT_HOSTNAME: "hostname",
    }
    name_or_uid_props = [lib.AGENT_ID, lib.AGENT_HOSTNAME, lib.MACHINES_FIELD]

    @classmethod
    def generate_pipeline(
        cls, name_or_uid=None, type=None, latest_model=True, filters={}
    ) -> List:
        # TODO implement type when supported by analytics
        schema = lib.MODEL_AGENT_SCHEMA_PREFIX
        return super(Agents, cls).generate_pipeline(
            schema, name_or_uid, latest_model, filters
        )

    @classmethod
    def generate_metrics_pipeline(cls):
        schema = lib.EVENT_AGENT_METRICS_PREFIX
        return super(Agents, cls).generate_pipeline(schema, latest_model=True)


class Connections(API_Filter):
    property_map = {
        lib.CONN_ID: lib.CONN_ID,
        lib.PROC_NAME_FIELD: lib.PROC_NAME_FIELD,
        lib.REMOTE_HOSTNAME_FIELD: lib.REMOTE_HOSTNAME_FIELD,
        lib.PROTOCOL_FIELD: "proto",
    }
    name_or_uid_props = [
        lib.CONN_ID,
        lib.REMOTE_HOSTNAME_FIELD,
        lib.PROC_NAME_FIELD,
    ]

    @classmethod
    def generate_pipeline(
        cls, name_or_uid=None, latest_model=True, filters={}
    ) -> List:
        schema = lib.MODEL_CONNECTION_PREFIX
        return super(Connections, cls).generate_pipeline(
            schema, name_or_uid, latest_model, filters
        )


class Fingerprints(API_Filter):
    property_map = {
        lib.MACHINES_FIELD: "muid",
        lib.POD_FIELD: "pod_uid",
        lib.CLUSTER_FIELD: "cluster_uid",
        lib.NAMESPACE_FIELD: "metadata.namespace",
        lib.CGROUP_FIELD: "cgroup",
        lib.IMAGE_FIELD: "image",
        lib.IMAGEID_FIELD: "image_id",
        lib.CONTAINER_ID_FIELD: "container_id",
        lib.CONTAINER_NAME_FIELD: "container_name",
    }

    name_or_uid_prop_names = [
        lib.IMAGE_FIELD,
        lib.IMAGEID_FIELD,
        lib.CGROUP_FIELD,
    ]

    @classmethod
    def generate_pipeline(
        cls, name_or_uid=None, type=None, latest_model=True, filters={}
    ) -> List:
        if type == lib.POL_TYPE_CONT or type == lib.POL_TYPE_SVC:
            schema = (
                f"{lib.MODEL_FINGERPRINT_PREFIX}:"
                f"{lib.MODEL_FINGERPRINT_SUBTYPE_MAP[type]}"
            )
        else:
            schema = f"{lib.MODEL_FINGERPRINT_PREFIX}:"
        return super(Fingerprints, cls).generate_pipeline(
            schema, name_or_uid, latest_model, filters
        )


class UID_List(API_Filter):
    @classmethod
    def generate_pipeline(cls, uid_list: Dict):
        pipeline_items = [{"latest_model": {}}]
        or_items = []
        for uid in uid_list[lib.DATA_FIELD][lib.UIDS_FIELD]:
            or_items.append({"property": lib.ID_FIELD, "equals": uid})
        filter = {"filter": {"or": or_items}}
        pipeline_items.append(filter)
        return pipeline_items
