from typing import Dict, List
import spyctl.spyctl_lib as lib


def generate_pipeline(uid_list: Dict) -> List:
    pipeline_items = [{"latest_model": {}}]
    or_items = []
    for uid in uid_list[lib.DATA_FIELD][lib.UIDS_FIELD]:
        or_items.append({"property": lib.ID_FIELD, "equals": uid})
    filter = {"filter": {"or": or_items}}
    pipeline_items.append(filter)
    return pipeline_items
