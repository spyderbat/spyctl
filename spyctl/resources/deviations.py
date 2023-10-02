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
    return rv
