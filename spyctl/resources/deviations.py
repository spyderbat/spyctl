from typing import Dict, List

import spyctl.api as api
import spyctl.config.configs as cfg
import spyctl.resources.api_filters as _af
import spyctl.spyctl_lib as lib


def get_unique_deviations(uid, st, et, full_rec=False) -> List[Dict]:
    pipeline = _af.Deviations.generate_pipeline()
    rv = {}
    ctx = cfg.get_current_context()
    for deviation in api.get_deviations(
        *ctx.get_api_data(), [uid], (st, et), pipeline, True
    ):
        checksum = deviation.get(lib.CHECKSUM_FIELD)
        if not checksum:
            continue
        if checksum not in rv:
            if not full_rec:
                rv[checksum] = deviation["deviation"]
            else:
                rv[checksum] = deviation
    return list(rv.values())


def get_deviations_stream(
    ctx: cfg.Context,
    sources,
    time,
    pipeline,
    limit_mem,
    disable_pbar_on_first,
    unique=False,
    items_list=False,
):
    yv = {}
    dev_list = []
    for deviation in api.get_deviations(
        *ctx.get_api_data(),
        sources,
        time,
        pipeline,
        limit_mem,
        disable_pbar_on_first=disable_pbar_on_first,
    ):
        if unique:
            checksum = deviation.get(lib.CHECKSUM_FIELD)
            if checksum and checksum not in yv:
                yv[checksum] = deviation
        else:
            if items_list:
                dev_list.append(deviation)
            else:
                yield deviation
    if items_list:
        if unique:
            yield __build_items_output(list(yv.values()))
        else:
            yield __build_items_output(dev_list)
    elif unique:
        for deviation in yv.values():
            yield deviation


def __build_items_output(deviations: List[Dict]) -> Dict:
    if len(deviations) == 1:
        return deviations[0]["deviation"]
    elif len(deviations) > 1:
        return {
            lib.API_FIELD: lib.API_VERSION,
            lib.ITEMS_FIELD: [d["deviation"] for d in deviations],
        }
    else:
        return {}
