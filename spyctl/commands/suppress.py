import spyctl.api as api
import spyctl.cli as cli
import spyctl.config.configs as cfg
import spyctl.spyctl_lib as lib
import spyctl.filter_resource as filt


def handle_suppress_traces():
    id = "trace:LRt5-6EHSAc:AAX6aOn8DxE:16400:policy_violation"
    vf = 1682703391.6660333
    vt = 1682705417.839697
    dt = "spydergraph"
    rv = api.get_object_by_id(
        *cfg.get_current_context().get_api_data(),
        id,
        "model_spydertrace",
        (vf, vt),
        dt,
    )
    print(rv)
