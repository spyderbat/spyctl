from typing import Dict, List

import spyctl.spyctl_lib as lib

NOT_AVAILABLE = lib.NOT_AVAILABLE

def container_output(cont: List[Dict]) -> Dict:
    if len(cont) == 1:
        return cont[0]
    elif len(cont) > 1:
        return {
            lib.API_FIELD: lib.API_VERSION,
            lib.ITEMS_FIELD: cont,
        }
    else:
        return {}
