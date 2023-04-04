import spyctl.spyctl_lib as lib
from typing import Dict, List

NOT_AVAILABLE = lib.NOT_AVAILABLE

def connection_bundles_output(connectionb: List[Dict]) -> Dict:
    if len(connectionb) == 1:
        return connectionb[0]
    elif len(connectionb) > 1:
        return {
    lib.API_FIELD: lib.API_VERSION,
    lib.ITEMS_FIELD: connectionb,
    }
    else:
        return {}