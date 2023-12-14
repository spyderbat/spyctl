from typing import Dict, List
import spyctl.spyctl_lib as lib
import spyctl.api as api
import spyctl.resources.api_filters as _af
import spyctl.config.configs as cfg


def handle_input_data(data: Dict, ctx: cfg.Context = None) -> List[Dict]:
    obj_kind = data.get(lib.KIND_FIELD)
    schema = data.get(lib.SCHEMA_FIELD)
    rv = []
    if obj_kind == lib.POL_KIND:
        rv.append(data)
    elif obj_kind == lib.BASELINE_KIND:
        rv.append(data)
    elif obj_kind == lib.FPRINT_KIND:
        rv.append(data)
    elif obj_kind == lib.DEVIATION_KIND or (
        schema
        and schema.startswith(
            (
                f"{lib.EVENT_AUDIT_PREFIX}:"
                f"{lib.EVENT_AUDIT_SUBTYPE_MAP['deviation']}"
            )
        )
    ):
        if obj_kind is None:
            rv.append(data["deviation"])
        else:
            rv.append(data)
    elif obj_kind == lib.FPRINT_GROUP_KIND:
        rv.extend(__handle_fprint_group_input(data))
    elif obj_kind == lib.UID_LIST_KIND:
        rv.extend(__handle_uid_list_input(data, ctx))
    elif lib.ITEMS_FIELD in data:
        rv.extend(__handle_spyctl_items_input(data))
    return rv


def __handle_fprint_group_input(data: Dict):
    return data[lib.DATA_FIELD][lib.FPRINT_GRP_FINGERPRINTS_FIELD]


def __handle_uid_list_input(data: Dict, ctx: cfg.Context = None):
    if not ctx:
        ctx = cfg.get_current_context()
    pipeline = _af.UID_List.generate_pipeline(data)
    time = (
        data[lib.METADATA_FIELD][lib.METADATA_START_TIME_FIELD],
        data[lib.METADATA_FIELD][lib.METADATA_END_TIME_FIELD],
    )
    src = ctx.global_source
    fprints = list(
        api.get_fingerprints(
            *ctx.get_api_data(), [src], time, pipeline=pipeline
        )
    )
    return fprints


def __handle_spyctl_items_input(data: Dict):
    rv = []
    for item in data[lib.ITEMS_FIELD]:
        rv.extend(handle_input_data(item))
    return rv
