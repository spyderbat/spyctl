"""Handles generation of filters for use by the API instead of doing local
filtering.
"""

from copy import deepcopy
from typing import Dict, List, Tuple, Union, Iterable

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

POLICIES_CACHE = None


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
    global POLICIES_CACHE
    ctx = cfg.get_current_context()
    if not POLICIES_CACHE:
        policies = api.get_policies(*ctx.get_api_data())
        POLICIES_CACHE = policies
    else:
        policies = POLICIES_CACHE
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


def get_default_time_window(resource: str) -> str:
    if resource == lib.FINGERPRINTS_RESOURCE:
        return "90m"
    return "24h"


def add_and_to_pipeline_filter(pipeline: List[Dict], filter: Dict):
    for item in pipeline:
        if "filter" in item:
            filter_clause = item["filter"]
            if "and" not in filter_clause:
                return
            filter_clause["and"].append(filter)
            return


def generate_not_clause(properties: Iterable, values: Iterable) -> Dict:
    not_clause = {"not": {"and": []}}
    for property, value in zip(properties, values):
        not_clause["not"]["and"].append(generate_filter_value(property, value))
    return not_clause


def generate_filter_value(property, value: str) -> Dict:
    if isinstance(value, int) or isinstance(value, float):
        rv = {"property": property, "equals": value}
    elif "*" in value or "?" in value:
        value = lib.simple_glob_to_regex(value)
        rv = {"property": property, "re_match": value}
    else:
        rv = {"property": property, "equals": value}
    return rv


class API_Filter:
    # property -> field name on object
    # (. notation for nested fields)
    property_map = {}

    # for not equals
    # property -> field name on object
    # (. notation for nested fields)
    not_property_map = {}

    # properties in the property_map that are
    # related to name_or_id filtering
    name_or_uid_props = []

    # property -> callable that takes the filter value
    # and turns it into something more useable.
    # Ex. cluster name to cluster uid
    values_helper = {
        lib.CLUSTER_FIELD: get_filtered_cluids,
        lib.MACHINE_SELECTOR_FIELD: get_filtered_muids,
    }

    source_type = SOURCE_TYPE_MUID
    alternate_source_type = None

    @classmethod
    def generate_pipeline(
        cls,
        schema,
        name_or_uid=None,
        latest_model=True,
        filters={},
        count=False,
    ) -> List:
        pipeline_items = []
        if latest_model:
            pipeline_items.append({"latest_model": {}})
        pipeline_items.append(
            cls.__generate_fprint_api_filters(schema, name_or_uid, **filters)
        )
        if count:
            pipeline_items.append(
                {
                    "aggregation": {
                        "aggregations": [{"count": {}, "as": "count"}]
                    }
                }
            )
        return pipeline_items

    @classmethod
    def generate_name_or_uid_expr(
        cls,
        name_or_uid,
    ):
        return cls.__build_or_block(cls.name_or_uid_props, [name_or_uid])

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
            if property := cls.__build_property(key):
                if isinstance(values, list) and len(values) > 1:
                    and_items.append(cls.__build_or_block([key], values))
                else:
                    if isinstance(values, list):
                        value = values[0]
                    else:
                        value = values
                    and_items.append(generate_filter_value(property, value))
            elif property := cls.__build_not_property(key):
                if isinstance(values, str):
                    value = [values]
                for value in values:
                    and_items.append(
                        {"not": generate_filter_value(property, value)}
                    )
            else:
                continue
        rv = {"filter": {"and": and_items}}
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
    def __build_not_property(cls, key: str):
        return cls.not_property_map[key]

    @classmethod
    def build_sources_and_filters(
        cls, use_property_fields=False, **filters
    ) -> Tuple[List[str], Dict]:
        """
        Builds and returns a tuple containing the sources and filters based on the given parameters.

        Args:
            use_property_fields (bool): Flag indicating whether to use property fields in the filters. False when using
                the filters to build a pipeline. True when using the filters standalone.
            **filters: Additional filters to be applied.

        Returns:
            Tuple[List[str], Dict]: A tuple containing the sources (list of strings) and filters (dictionary).

        """
        ctx = cfg.get_current_context()
        ctx_filters = deepcopy(ctx.get_filters())
        sources = cls.__get_sources(ctx_filters, filters)
        filters = cls.__get_filters(ctx_filters, filters)
        if use_property_fields:
            filters = {cls.__build_property(k): v for k, v in filters.items()}
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
            cls.__pop_pol_filters(ctx_filters, filters)
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

    @staticmethod
    def __pop_pol_filters(ctx_filters: Dict, cmdline_filters: Dict):
        ctx_filters.pop(lib.POLICIES_FIELD, None)
        cmdline_filters.pop(lib.POLICIES_FIELD, None)


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


class AgentMetrics(API_Filter):
    property_map = {lib.ID_FIELD: lib.ID_FIELD}
    name_or_uid_props = [lib.ID_FIELD]
    source_type = SOURCE_TYPE_MUID

    @classmethod
    def generate_pipeline(
        cls, name_or_uid=None, type=None, latest_model=True, filters={}
    ) -> List:
        schema = (
            f"{lib.EVENT_METRICS_PREFIX}:"
            f"{lib.EVENT_METRIC_SUBTYPE_MAP['agent']}"
        )
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
    name_or_uid_props = [
        lib.ID_FIELD,
        lib.CONTAINER_ID_FIELD,
        lib.IMAGE_FIELD,
        lib.CONTAINER_NAME_FIELD,
        lib.IMAGEID_FIELD,
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
        lib.NAMESPACE_FIELD: (
            f"{lib.METADATA_FIELD}.{lib.METADATA_NAMESPACE_FIELD}",
        ),
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


class Deviations(API_Filter):
    property_map = {
        lib.ID_FIELD: lib.ID_FIELD,
        lib.POLICIES_FIELD: lib.BE_POL_UID_FIELD,
    }
    not_property_map = {
        f"not_{lib.CHECKSUM_FIELD}": lib.CHECKSUM_FIELD,
    }
    name_or_uid_props = [lib.ID_FIELD]
    source_type = SOURCE_TYPE_POL

    @classmethod
    def generate_pipeline(
        cls, name_or_uid=None, latest_model=True, filters={}
    ) -> List:
        schema = (
            f"{lib.EVENT_AUDIT_PREFIX}:"
            f"{lib.EVENT_AUDIT_SUBTYPE_MAP['deviation']}"
        )
        return super(Deviations, cls).generate_pipeline(
            schema, name_or_uid, latest_model, filters
        )

    @classmethod
    def generate_count_pipeline(cls, name_or_uid, filters={}):
        schema = (
            f"{lib.EVENT_AUDIT_PREFIX}:"
            f"{lib.EVENT_AUDIT_SUBTYPE_MAP['deviation']}"
        )
        pipeline_items = super(Deviations, cls).generate_pipeline(
            schema,
            name_or_uid,
            True,
            filters,
        )
        pipeline_items.append(
            {
                "aggregation": {
                    "aggregations": [
                        {
                            "uniq_count": {"property": "checksum"},
                            "as": "counts",
                        },
                    ],
                    "by": [{"property": "policy_uid"}],
                },
            }
        )
        return pipeline_items


class Fingerprints(API_Filter):
    # property_map = {
    #     lib.MACHINES_FIELD: "muid",
    #     lib.POD_FIELD: "pod_uid",
    #     lib.CLUSTER_FIELD: "cluster_uid",
    #     lib.NAMESPACE_FIELD: (
    #       f"{lib.METADATA_FIELD}.{lib.METADATA_NAMESPACE_FIELD}"
    # ),
    #     lib.CGROUP_FIELD: "cgroup",
    #     lib.IMAGE_FIELD: "image",
    #     lib.IMAGEID_FIELD: "image_id",
    #     lib.CONTAINER_ID_FIELD: "container_id",
    #     lib.CONTAINER_NAME_FIELD: "container_name",
    #     lib.STATUS_FIELD: lib.STATUS_FIELD,
    #     lib.ID_FIELD: lib.ID_FIELD,
    # }
    property_map = {
        lib.CLUSTER_FIELD: "cluster_uid",
        lib.NAMESPACE_FIELD: lib.METADATA_NAMESPACE_FIELD,
        lib.CGROUP_FIELD: "cgroup",
        lib.IMAGE_FIELD: "image_name",
        lib.IMAGEID_FIELD: "image_id",
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
        lib.NAMESPACE_FIELD: (
            f"{lib.METADATA_FIELD}.{lib.METADATA_NAMESPACE_FIELD}"
        ),
    }
    name_or_uid_props = [lib.ID_FIELD, lib.NAME_FIELD, lib.BE_KUID_FIELD]
    source_type = SOURCE_TYPE_CLUID_BASE

    @classmethod
    def generate_pipeline(
        cls, name_or_uid=None, latest_model=True, filters={}
    ) -> List:
        schema = lib.MODEL_NAMESPACE_PREFIX
        return super(Namespaces, cls).generate_pipeline(
            schema, name_or_uid, latest_model, filters
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
        lib.NAMESPACE_FIELD: (
            f"{lib.METADATA_FIELD}.{lib.METADATA_NAMESPACE_FIELD}"
        ),
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
        lib.NAMESPACE_FIELD: (
            f"{lib.METADATA_FIELD}.{lib.METADATA_NAMESPACE_FIELD}"
        ),
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


class ReplicaSet(API_Filter):
    property_map = {
        lib.ID_FIELD: lib.ID_FIELD,
        lib.BE_KUID_FIELD: lib.BE_KUID_FIELD,
        lib.NAME_FIELD: f"{lib.METADATA_FIELD}.{lib.METADATA_NAME_FIELD}",
        lib.NAMESPACE_FIELD: (
            f"{lib.METADATA_FIELD}.{lib.METADATA_NAMESPACE_FIELD}"
        ),
    }
    name_or_uid_props = [lib.ID_FIELD, lib.METADATA_NAME_FIELD]
    source_type = SOURCE_TYPE_CLUID_BASE

    @classmethod
    def generate_pipeline(
        cls, name_or_uid=None, latest_model=True, filters={}
    ) -> List:
        schema = lib.MODEL_REPLICASET_PREFIX
        return super(ReplicaSet, cls).generate_pipeline(
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
    name_or_uid_props = [
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


class Daemonsets(API_Filter):
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
        schema = lib.MODEL_DAEMONSET_PREFIX
        return super(Daemonsets, cls).generate_pipeline(
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
    name_or_uid_props = [
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
