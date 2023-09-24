"""Handles generation of filters for use by the API instead of doing local
filtering.
"""

from copy import deepcopy
from typing import Dict, List, Tuple, Union

import spyctl.api as api
import spyctl.config.configs as cfg
import spyctl.filter_resource as filt
import spyctl.spyctl_lib as lib

# Source types
SOURCE_TYPE_CLUID = "cluid"
SOURCE_TYPE_CLUID_BASE = "cluid_base"
SOURCE_TYPE_CLUID_CBUN = "cluid_cbun"
SOURCE_TYPE_CLUID_POCO = "cluid_poco"
SOURCE_TYPE_CLUID_FLAG = "cluid_flag"
CLUSTER_SOURCES = [
    SOURCE_TYPE_CLUID,
    SOURCE_TYPE_CLUID_BASE,
    SOURCE_TYPE_CLUID_CBUN,
    SOURCE_TYPE_CLUID_FLAG,
    SOURCE_TYPE_CLUID_POCO,
]
SOURCE_TYPE_GLOBAL = "global"
SOURCE_TYPE_MUID = "muid"
SOURCE_TYPE_POL = "pol"


def get_filtered_cluids(**filters) -> List[str]:
    ctx = cfg.get_current_context()
    clusters = api.get_clusters(*ctx.get_api_data())
    clusters = filt.filter_clusters(clusters, **filters)
    cluids = [c["uid"] for c in clusters]
    return cluids


def get_filtered_muids(**filters) -> List[str]:
    ctx = cfg.get_current_context()
    sources = api.get_sources(*ctx.get_api_data())
    sources = filt.filter_sources(sources, **filters)
    muids = [s["uid"] for s in sources]
    return muids


def get_filtered_pol_uids(**filters) -> List[str]:
    ctx = cfg.get_current_context()
    policies = api.get_policies(*ctx.get_api_data())
    policy_filters = filters.get(lib.POLICIES_FIELD)
    if policy_filters:
        policies = [
            p
            for p in filt.filter_obj(
                policies,
                [
                    [lib.METADATA_FIELD, lib.METADATA_NAME_FIELD],
                    [lib.METADATA_FIELD, lib.METADATA_UID_FIELD],
                ],
                policy_filters,
            )
        ]
    policy_uids = [
        p[lib.METADATA_FIELD][lib.METADATA_UID_FIELD] for p in policies
    ]
    return policy_uids


class API_Filter:
    property_map = (
        {}
    )  # property -> field name on object (. notation for nested fields)
    name_or_uid_props: []  # properties in the property_map that are related to name_or_id filtering
    values_helper = {
        lib.CLUSTER_FIELD: get_filtered_cluids,
        lib.MACHINE_SELECTOR_FIELD: get_filtered_muids,
    }  # property -> callable that takes the filter value and turns it into something more useable. Ex. cluster name to cluster uid
    source_type = SOURCE_TYPE_MUID
    alternate_source_type = None

    @classmethod
    def generate_pipeline(
        cls, schema, name_or_uid=None, latest_model=True, filters={}
    ) -> List:
        pipeline_items = []
        pipeline_items.append(
            cls.__generate_fprint_api_filters(schema, name_or_uid, **filters)
        )
        if latest_model:
            pipeline_items.append({"latest_model": {}})
        return pipeline_items

    @classmethod
    def __generate_fprint_api_filters(
        cls,
        schema,
        name_or_uid: Union[str, List],
        **filters,
    ) -> Dict:
        and_items = [{"schema": schema}]
        if name_or_uid:
            and_items.append(
                cls.__build_or_block(
                    cls.name_or_uid_props,
                    [name_or_uid],
                )
            )
        for key, values in filters.items():
            if isinstance(values, list) and len(values) > 1:
                and_items.append(cls.__build_or_block([key], values))
            else:
                if isinstance(values, list):
                    value = values[0]
                else:
                    value = values
                property = cls.__build_property(key)
                if not property:
                    continue
                if isinstance(value, int) or isinstance(value, float):
                    and_items.append({"property": property, "equals": value})
                elif "*" in value or "?" in value:
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
    def __build_or_block(cls, keys: List[str], values: List[str]):
        or_items = []
        for key in keys:
            for value in values:
                if "*" in value or "?" in value:
                    value = lib.simple_glob_to_regex(value)
                    or_items.append(
                        {
                            "property": cls.__build_property(key),
                            "re_match": value,
                        }
                    )
                else:
                    or_items.append(
                        {
                            "property": cls.__build_property(key),
                            "equals": value,
                        }
                    )
        return {"or": or_items}

    @classmethod
    def __build_property(cls, key: str):
        return cls.property_map[key]

    @classmethod
    def build_sources_and_filters(cls, **filters) -> Tuple[List[str], Dict]:
        ctx = cfg.get_current_context()
        ctx_filters = deepcopy(ctx.get_filters())
        sources = cls.__get_sources(ctx_filters, filters)
        filters = cls.__get_filters(ctx_filters, filters)
        return sources, filters

    @classmethod
    def __get_sources(cls, ctx_filters: Dict, filters: Dict):
        ctx = cfg.get_current_context()
        sources = []
        if cls.source_type == SOURCE_TYPE_GLOBAL:
            sources.append(ctx.global_source)
            if cls.alternate_source_type == SOURCE_TYPE_MUID and (
                lib.MACHINES_FIELD in ctx_filters
                or lib.MACHINES_FIELD in filters
            ):
                muids = get_filtered_muids(**filters)
                cls.__pop_muid_filters(ctx_filters, filters)
                if muids:
                    sources = muids
        elif cls.source_type == SOURCE_TYPE_CLUID:
            cluids = get_filtered_cluids(**filters)
            cls.__pop_cluid_filters(ctx_filters, filters)
            sources = cluids
        elif cls.source_type == SOURCE_TYPE_CLUID_BASE:
            cluids = get_filtered_cluids(**filters)
            cls.__pop_cluid_filters(ctx_filters, filters)
            sources = [cluid + "_base" for cluid in cluids]
        elif cls.source_type == SOURCE_TYPE_CLUID_POCO:
            cluids = get_filtered_cluids(**filters)
            cls.__pop_cluid_filters(ctx_filters, filters)
            sources = [cluid + "_poco" for cluid in cluids]
        elif cls.source_type == SOURCE_TYPE_POL:
            pol_uids = get_filtered_pol_uids(**filters)
            sources = pol_uids
        else:  # muids is the default
            if cls.alternate_source_type in CLUSTER_SOURCES and (
                lib.CLUSTER_FIELD in ctx_filters
                or lib.CLUSTER_FIELD in filters
            ):
                cluids = get_filtered_cluids(**filters)
                cls.__pop_cluid_filters(ctx_filters, filters)
                if cls.alternate_source_type == SOURCE_TYPE_CLUID_CBUN:
                    sources = [cluid + "_cbun" for cluid in cluids]
                elif cls.alternate_source_type == SOURCE_TYPE_CLUID_FLAG:
                    sources = [cluid + "_flag" for cluid in cluids]
                elif cls.alternate_source_type == SOURCE_TYPE_CLUID_POCO:
                    sources = [cluid + "_poco" for cluid in cluids]
                else:
                    sources = cluids
            else:
                muids = get_filtered_muids(**filters)
                cls.__pop_muid_filters(ctx_filters, filters)
                sources = muids
        return sources

    @classmethod
    def __get_filters(cls, ctx_filters: Dict, filters: Dict):
        rv_filters = {}
        for key, value in ctx_filters.items():
            if key in cls.property_map:
                rv_filters[key] = value
        for key, value in filters.items():
            if key in cls.property_map:
                rv_filters[key] = value
        for key, value in rv_filters.items():
            if key in cls.values_helper:
                value = cls.values_helper[key](**{key: value})
                rv_filters[key] = value
        return rv_filters

    @staticmethod
    def __pop_cluid_filters(ctx_filters: Dict, cmdline_filters: Dict):
        ctx_filters.pop(lib.CLUSTER_FIELD, None)
        cmdline_filters.pop(lib.CLUSTER_FIELD, None)

    @staticmethod
    def __pop_muid_filters(ctx_filters: Dict, cmdline_filters: Dict):
        ctx_filters.pop(lib.MACHINES_FIELD, None)
        cmdline_filters.pop(lib.MACHINES_FIELD, None)


class Agents(API_Filter):
    property_map = {
        lib.MACHINES_FIELD: "muid",
        lib.AGENT_ID: "id",
        lib.AGENT_HOSTNAME: "hostname",
        lib.STATUS_FIELD: lib.STATUS_FIELD,
    }
    name_or_uid_props = [lib.AGENT_ID, lib.AGENT_HOSTNAME, lib.MACHINES_FIELD]
    source_type = SOURCE_TYPE_GLOBAL
    alternate_source_type = SOURCE_TYPE_MUID

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


class AgentMetrics(API_Filter):
    property_map = {lib.ID_FIELD: lib.ID_FIELD}
    name_or_uid_props = [lib.ID_FIELD]
    source_type = SOURCE_TYPE_MUID

    @classmethod
    def generate_pipeline(
        cls, name_or_uid=None, type=None, latest_model=True, filters={}
    ) -> List:
        schema = lib.EVENT_AGENT_METRICS_PREFIX
        return super(AgentMetrics, cls).generate_pipeline(
            schema, name_or_uid, latest_model, filters
        )


class Connections(API_Filter):
    property_map = {
        lib.ID_FIELD: lib.ID_FIELD,
        lib.PROC_NAME_FIELD: lib.PROC_NAME_FIELD,
        lib.REMOTE_HOSTNAME_FIELD: lib.REMOTE_HOSTNAME_FIELD,
        lib.PROTOCOL_FIELD: "proto",
        lib.STATUS_FIELD: lib.STATUS_FIELD,
        lib.LOCAL_PORT: lib.LOCAL_PORT,
        lib.REMOTE_PORT: lib.REMOTE_PORT,
    }
    name_or_uid_props = [
        lib.ID_FIELD,
        lib.REMOTE_HOSTNAME_FIELD,
        lib.PROC_NAME_FIELD,
    ]
    source_type = SOURCE_TYPE_MUID

    @classmethod
    def generate_pipeline(
        cls, name_or_uid=None, latest_model=True, filters={}
    ) -> List:
        schema = lib.MODEL_CONNECTION_PREFIX
        return super(Connections, cls).generate_pipeline(
            schema, name_or_uid, latest_model, filters
        )


class ConnectionBundles(API_Filter):
    property_map = {
        lib.ID_FIELD: lib.ID_FIELD,
        lib.PROTOCOL_FIELD: "proto",
        lib.CLIENT_PORT: lib.CLIENT_PORT,
        lib.SERVER_PORT: lib.SERVER_PORT,
    }
    name_or_uid_props = [
        lib.ID_FIELD,
    ]
    source_type = SOURCE_TYPE_MUID
    alternate_source_type = SOURCE_TYPE_CLUID_CBUN

    @classmethod
    def generate_pipeline(
        cls, name_or_uid=None, latest_model=True, filters={}
    ) -> List:
        schema = lib.MODEL_CONN_BUN_PREFIX
        return super(ConnectionBundles, cls).generate_pipeline(
            schema, name_or_uid, latest_model, filters
        )


class Containers(API_Filter):
    property_map = {
        lib.ID_FIELD: lib.ID_FIELD,
        lib.CONTAINER_ID_FIELD: lib.BE_CONTAINER_ID,
        lib.IMAGE_FIELD: lib.BE_CONTAINER_IMAGE,
        lib.CONTAINER_NAME_FIELD: lib.BE_CONTAINER_NAME,
        lib.IMAGEID_FIELD: lib.BE_CONTAINER_IMAGE_ID,
        lib.STATUS_FIELD: lib.STATUS_FIELD,
        lib.NAMESPACE_FIELD: "pod_namespace",
    }
    name_or_uid_prop_names = [
        lib.ID_FIELD,
        lib.BE_CONTAINER_ID,
        lib.BE_CONTAINER_IMAGE,
        lib.BE_CONTAINER_NAME,
        lib.BE_CONTAINER_IMAGE_ID,
    ]
    source_type = SOURCE_TYPE_MUID
    alternate_source_type = SOURCE_TYPE_CLUID_POCO

    @classmethod
    def generate_pipeline(
        cls, name_or_uid=None, latest_model=True, filters={}
    ) -> List:
        schema = lib.MODEL_CONTAINER_PREFIX
        return super(Containers, cls).generate_pipeline(
            schema, name_or_uid, latest_model, filters
        )


class Deployments(API_Filter):
    property_map = {
        lib.ID_FIELD: lib.ID_FIELD,
        lib.BE_KUID_FIELD: lib.BE_KUID_FIELD,
        lib.NAME_FIELD: f"{lib.METADATA_FIELD}.{lib.METADATA_NAME_FIELD}",
        lib.NAMESPACE_FIELD: f"{lib.METADATA_FIELD}.{lib.METADATA_NAMESPACE_FIELD}",
    }
    name_or_uid_props = [lib.ID_FIELD, lib.NAME_FIELD, lib.BE_KUID_FIELD]
    source_type = SOURCE_TYPE_CLUID_BASE

    @classmethod
    def generate_pipeline(
        cls, name_or_uid=None, latest_model=True, filters={}
    ) -> List:
        schema = lib.MODEL_DEPLOYMENT_PREFIX
        return super(Deployments, cls).generate_pipeline(
            schema, name_or_uid, latest_model, filters
        )


class Fingerprints(API_Filter):
    property_map = {
        lib.MACHINES_FIELD: "muid",
        lib.POD_FIELD: "pod_uid",
        lib.CLUSTER_FIELD: "cluster_uid",
        lib.NAMESPACE_FIELD: f"{lib.METADATA_FIELD}.{lib.METADATA_NAMESPACE_FIELD}",
        lib.CGROUP_FIELD: "cgroup",
        lib.IMAGE_FIELD: "image",
        lib.IMAGEID_FIELD: "image_id",
        lib.CONTAINER_ID_FIELD: "container_id",
        lib.CONTAINER_NAME_FIELD: "container_name",
        lib.STATUS_FIELD: lib.STATUS_FIELD,
        lib.ID_FIELD: lib.ID_FIELD,
    }
    source_type = SOURCE_TYPE_GLOBAL
    alternate_source_type = SOURCE_TYPE_MUID

    name_or_uid_props = [
        lib.IMAGE_FIELD,
        lib.IMAGEID_FIELD,
        lib.CGROUP_FIELD,
        lib.ID_FIELD,
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


class Machines(API_Filter):
    property_map = {lib.ID_FIELD: lib.ID_FIELD}
    name_or_uid_props = [lib.ID_FIELD]
    source_type = SOURCE_TYPE_MUID

    @classmethod
    def generate_pipeline(
        cls, name_or_uid=None, latest_model=True, filters={}
    ) -> List:
        schema = lib.MODEL_MACHINE_PREFIX
        return super(Machines, cls).generate_pipeline(
            schema, name_or_uid, latest_model, filters
        )


class Namespaces(API_Filter):
    property_map = {
        lib.ID_FIELD: lib.ID_FIELD,
        lib.BE_KUID_FIELD: f"{lib.METADATA_FIELD}.{lib.METADATA_UID_FIELD}",
        lib.NAME_FIELD: f"{lib.METADATA_FIELD}.{lib.METADATA_NAME_FIELD}",
        lib.NAMESPACE_FIELD: f"{lib.METADATA_FIELD}.{lib.METADATA_NAMESPACE_FIELD}",
    }
    # Namespaces aren't filtered by name at the API Level
    name_or_uid_props = [lib.ID_FIELD, lib.NAME_FIELD, lib.BE_KUID_FIELD]
    source_type = SOURCE_TYPE_CLUID_BASE

    @classmethod
    def generate_pipeline(cls, latest_model=True, filters={}) -> List:
        # Namespace objects don't exist in spyderbat's backend. Clusters
        # track the metadata of namespaces though.
        schema = lib.MODEL_CLUSTER_PREFIX
        return super(Namespaces, cls).generate_pipeline(
            schema, None, latest_model, filters
        )

    @classmethod
    def get_name_or_uid_fields(cls):
        rv = []
        for prop in cls.name_or_uid_props:
            rv.append(cls.property_map[prop])
        return rv


class Nodes(API_Filter):
    property_map = {
        lib.ID_FIELD: lib.ID_FIELD,
        lib.BE_KUID_FIELD: lib.BE_KUID_FIELD,
        lib.NAME_FIELD: f"{lib.METADATA_FIELD}.{lib.METADATA_NAME_FIELD}",
        lib.NAMESPACE_FIELD: f"{lib.METADATA_FIELD}.{lib.METADATA_NAMESPACE_FIELD}",
    }
    name_or_uid_props = [lib.ID_FIELD, lib.NAME_FIELD, lib.BE_KUID_FIELD]
    source_type = SOURCE_TYPE_CLUID_BASE

    @classmethod
    def generate_pipeline(
        cls, name_or_uid=None, latest_model=True, filters={}
    ) -> List:
        schema = lib.MODEL_NODE_PREFIX
        return super(Nodes, cls).generate_pipeline(
            schema, name_or_uid, latest_model, filters
        )


class OpsFlags(API_Filter):
    property_map = {lib.ID_FIELD: lib.ID_FIELD}
    name_or_uid_props = [lib.ID_FIELD]
    source_type = SOURCE_TYPE_MUID
    alternate_source_type = SOURCE_TYPE_CLUID_FLAG

    @classmethod
    def generate_pipeline(
        cls, name_or_uid=None, latest_model=True, filters={}
    ) -> List:
        schema = lib.EVENT_OPSFLAG_PREFIX
        return super(OpsFlags, cls).generate_pipeline(
            schema, name_or_uid, latest_model, filters
        )


class Pods(API_Filter):
    property_map = {
        lib.ID_FIELD: lib.ID_FIELD,
        lib.BE_KUID_FIELD: lib.BE_KUID_FIELD,
        lib.NAME_FIELD: f"{lib.METADATA_FIELD}.{lib.METADATA_NAME_FIELD}",
        lib.NAMESPACE_FIELD: f"{lib.METADATA_FIELD}.{lib.METADATA_NAMESPACE_FIELD}",
    }
    name_or_uid_props = [lib.ID_FIELD, lib.METADATA_NAME_FIELD]
    source_type = SOURCE_TYPE_CLUID_POCO

    @classmethod
    def generate_pipeline(
        cls, name_or_uid=None, latest_model=True, filters={}
    ) -> List:
        schema = lib.MODEL_POD_PREFIX
        return super(Pods, cls).generate_pipeline(
            schema, name_or_uid, latest_model, filters
        )


class Processes(API_Filter):
    property_map = {
        lib.ID_FIELD: lib.ID_FIELD,
        lib.CONTAINER_ID_FIELD: "container",
        "user": "euser",
        lib.CGROUP_FIELD: lib.CGROUP_FIELD,
        lib.EXE_FIELD: lib.EXE_FIELD,
        lib.NAME_FIELD: lib.NAME_FIELD,
    }
    name_or_uid_prop_names = [
        lib.NAME_FIELD,
        lib.ID_FIELD,
    ]
    source_type = SOURCE_TYPE_MUID

    @classmethod
    def generate_pipeline(
        cls, name_or_uid=None, latest_model=True, filters={}
    ) -> List:
        schema = lib.MODEL_PROCESS_PREFIX
        return super(Processes, cls).generate_pipeline(
            schema, name_or_uid, latest_model, filters
        )


class RedFlags(API_Filter):
    property_map = {
        lib.ID_FIELD: lib.ID_FIELD,
        "short_name": "short_name",
        lib.CLUSTER_FIELD: "cluster_uid",
    }
    name_or_uid_props = [lib.ID_FIELD, "short_name"]
    source_type = SOURCE_TYPE_MUID
    alternate_source_type = SOURCE_TYPE_CLUID_FLAG

    @classmethod
    def generate_pipeline(
        cls, name_or_uid=None, latest_model=True, filters={}
    ) -> List:
        schema = lib.EVENT_REDFLAG_PREFIX
        return super(RedFlags, cls).generate_pipeline(
            schema, name_or_uid, latest_model, filters
        )


class Spydertraces(API_Filter):
    property_map = {
        lib.ID_FIELD: lib.ID_FIELD,
        lib.MACHINES_FIELD: "muid",
        lib.POD_FIELD: "pod_uid",
        lib.CLUSTER_FIELD: "cluster_uid",
        lib.CGROUP_FIELD: "trigger_cgroup",
        lib.IMAGE_FIELD: "image",
        lib.IMAGEID_FIELD: "image_id",
        lib.CONTAINER_ID_FIELD: "container",
        lib.BE_SCORE: lib.BE_SCORE,
        lib.BE_SUPPRESSED: lib.BE_SUPPRESSED,
        lib.STATUS_FIELD: lib.STATUS_FIELD,
        lib.BE_ROOT_PROC_NAME: lib.BE_ROOT_PROC_NAME,
        lib.BE_TRIGGER_NAME: lib.BE_TRIGGER_NAME,
    }
    name_or_uid_prop_names = [
        lib.BE_ROOT_PROC_NAME,
        lib.BE_TRIGGER_NAME,
        lib.ID_FIELD,
    ]
    source_type = SOURCE_TYPE_MUID

    @classmethod
    def generate_pipeline(
        cls, name_or_uid=None, latest_model=True, filters={}
    ) -> List:
        schema = lib.MODEL_SPYDERTRACE_PREFIX
        return super(Spydertraces, cls).generate_pipeline(
            schema, name_or_uid, latest_model, filters
        )


class SpydertraceSummaries(API_Filter):
    property_map = {lib.ID_FIELD: lib.ID_FIELD}
    name_or_uid_props = [lib.ID_FIELD]
    source_type = SOURCE_TYPE_MUID

    @classmethod
    def generate_pipeline(
        cls, name_or_uid=None, latest_model=True, filters={}
    ) -> List:
        schema = f"{lib.MODEL_FINGERPRINT_PREFIX}:{lib.POL_TYPE_TRACE}"
        return super(SpydertraceSummaries, cls).generate_pipeline(
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
