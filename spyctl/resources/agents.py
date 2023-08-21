from typing import Dict, List

from tabulate import tabulate

import spyctl.spyctl_lib as lib
import zulu



def agents_output(agents: List[Dict]) -> Dict:
    if len(agents) == 1:
        return agents[0]
    elif len(agents) > 1:
        return {
            lib.API_FIELD: lib.API_VERSION,
            lib.ITEMS_FIELD: agents,
        }
    else:
        return {}