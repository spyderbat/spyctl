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
    raw_data=False,
    include_irrelevant=False,
    policies={},
):
    import spyctl.commands.merge as merge

    policy_uids = {
        policy[lib.METADATA_FIELD].get(
            lib.METADATA_UID_FIELD
        ): merge.get_merge_object(
            lib.POL_KIND, policy, True, "check_deviations"
        )
        for policy in policies
    }  # policy uid -> merge object
    emit_processed = {}  # tracks if we should emit a deviation
    unique_deviations = {}  # For unique deviations (not raw)
    dev_list = []  # For all deviations (not raw)
    for deviation in api.get_deviations(
        *ctx.get_api_data(),
        sources,
        time,
        pipeline,
        limit_mem,
        disable_pbar_on_first=disable_pbar_on_first,
    ):
        __set_checksum(deviation)
        checksum = deviation.get(lib.CHECKSUM_FIELD)
        pol_uid = deviation["policy_uid"]
        key = (checksum, pol_uid)
        if unique and include_irrelevant:
            # We want all unique deviations, including irrelevant ones
            if key not in unique_deviations and key not in emit_processed:
                if raw_data:
                    emit_processed[key] = True
                    yield deviation
                else:
                    unique_deviations[key] = deviation
        elif unique:
            # We want only unique relevant deviations
            if key not in emit_processed:
                m_obj = policy_uids[pol_uid]
                m_obj.asymmetric_merge(
                    deviation[lib.DEVIATION_FIELD], check_irrelevant=True
                )
                if m_obj.is_relevant_obj(lib.DEVIATION_KIND, checksum):
                    emit_processed[key] = True
                    unique_deviations[key] = deviation
                else:
                    emit_processed[key] = False
        elif include_irrelevant:
            # We want all deviations
            if raw_data:
                yield deviation
            else:
                dev_list.append(deviation)
        else:
            # We want all relevant deviations
            if key not in emit_processed:
                m_obj = policy_uids[pol_uid]
                m_obj.asymmetric_merge(
                    deviation[lib.DEVIATION_FIELD], check_irrelevant=True
                )
                if m_obj.is_relevant_obj(lib.DEVIATION_KIND, checksum):
                    emit_processed[key] = True
                else:
                    emit_processed[key] = False
            if emit_processed[key]:
                if raw_data:
                    yield deviation
                else:
                    dev_list.append(deviation)

    # If we got to this point we want unique relevant deviations
    # or all deviations in a format suitable for merging/diffing
    if unique and unique_deviations:
        if raw_data:
            for deviation in unique_deviations.values():
                yield deviation
        else:
            yield __build_items_output(list(unique_deviations.values()))
    elif dev_list:
        yield __build_items_output(dev_list)


def __set_checksum(deviation: Dict) -> Dict:
    deviation[lib.DEVIATION_FIELD][lib.METADATA_FIELD][
        lib.CHECKSUM_FIELD
    ] = deviation.get(lib.CHECKSUM_FIELD)


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
