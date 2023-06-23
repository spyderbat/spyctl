import spyctl.spyctl_lib as lib
from typing import Dict, List
from tabulate import tabulate
import zulu 


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

def client(d):
   if 'client_dns_name'in d:
    return d['client_dns_name']
   else:
    return d['client_ip']
    
def server(d):
    if 'server_dns_name' in d:
        return d['server_dns_name']
    else:
       return d['server_ip']
        
    
def time(epoch):
    return zulu.Zulu.fromtimestamp(epoch).format("YYYY-MM-ddTHH:mm:ss") + "Z"

def connection_bundle_summary_output(connectionb: List[Dict]) -> str:

    table_data = [[client(d), server(d), d["server_port"], d["proto"], d['num_connections'], time(d["valid_from"]), time(d["valid_to"])] for d in connectionb]
    
    bundled_data = {}
    for bundle in table_data: 
      client_ip = bundle[0]
      server_ip = bundle[1]
      server_port = bundle[2]
      proto = bundle[3]
      num_connections = bundle[4]
      valid_from = bundle[5]
      valid_to= bundle[6]
  
      key = (client_ip, server_ip, server_port, proto)
    
      if key in bundled_data:
          data = bundled_data[key]
          data['num_connections'] += num_connections
          if valid_from < data['valid_from']:
              data['valid_from'] = valid_from
          if valid_to < data['valid_to']:
              data['valid_to'] = valid_to
      else:
          data = {
              'num_connections': num_connections,
              'valid_from': valid_from,
              'valid_to': valid_to
          }

          bundled_data[key] = data

    aggregated_table_data = [
       [
          key[0], 
          key[1], 
          key[2], 
          key[3], 
          data['num_connections'], 
          data['valid_from'], 
          data['valid_to']
        ] 
        for key, data in bundled_data.items()
    ]
    
    print(
       tabulate(
        aggregated_table_data, 
        headers= [
            "CLIENT",
            "SERVER", 
            "SERVER_PORT", 
            "PROTOCOL",
            "CONNNECTIONS", 
            "VALID_FROM", 
            "VALID_TO"
        ],
        tablefmt= "plain",
    )
)
