from typing import Dict, List, Optional, Tuple
import zulu
from tabulate import tabulate
import spyctl.spyctl_lib as lib


def spydertraces_output(spytrace: List[Dict]) -> Dict:
    if len(spytrace) == 1:
        return spytrace[0]
    elif len(spytrace) > 1:
        return {
            lib.API_FIELD: lib.API_VERSION,
            lib.ITEMS_FIELD: spytrace,
        }
    else:
        return {}