from typing import Dict, List

from tabulate import tabulate
import spyctl.spyctl_lib as lib

def agent_summary_output(agents: List[Dict]) -> str:
    header = ["SCHEMA", "STATUS"]
    data = []
    for agent in agents:
        data.append(agent_summary_data(agent))
    return tabulate(data, header, tablefmt="plain")

def agent_summary_data(agent: Dict) -> List:
    rv = [
        agent["schema"],
        agent["status"]
    ]
    return rv


def agents_output(agents: List[Dict]) -> Dict:
    if len(agents) == 1:
        return agents[0]
    elif len(agents) > 1:
        return {
            lib.AGENT_SCHEMA: lib.AGENT_SCHEMA
            # lib.ITEMS_FIELD: agents,
        }
    else:
        return {}