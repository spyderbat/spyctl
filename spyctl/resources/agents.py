from typing import Dict, List

from tabulate import tabulate
import spyctl.spyctl_lib as lib


def agent_summary_output(agents: List[Dict]) -> str:
    header = ["STATUS", "HOSTNAME", "ID"]
    data = []
    for agent in agents:
        data.append(agent_summary_data(agent))
    return tabulate(data, header, tablefmt="plain")


def agent_summary_data(agent: Dict) -> List:
    rv = [agent["status"], agent["hostname"], agent["id"]]
    return rv


def agents_output(agents: List[Dict]) -> Dict:
    if len(agents) == 1:
        return agents[0]
    elif len(agents) > 1:
        return {
            lib.AGENT_ID: lib.AGENT_ID
        }
    else:
        return {}
