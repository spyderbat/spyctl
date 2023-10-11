import json

from tabulate import tabulate

# step 1: spyctl get connections -o json --ndjson --remote-port 53 > connections53.json and
# spyctl get containers -o json --ndjson > containers53.json


# load connection data and add it to the conn dictionary
# if any field is not present default is " "
conn_dict = {}
with open("connections53.json", "r") as file:
    for connections in file:
        connection = json.loads(connections)
        containerUID = connection.get("container_uid", " ")
        payload = connection.get("payload", " ")
        conn_dict[containerUID] = {"payload": payload}


container_dict = {}

# load container data and add it to the container dict with
# containerUID as the key
with open("containers53.json", "r") as file:
    for containers in file:
        containerInfo = json.loads(containers)
        containerUID = containerInfo.get("id", " ")
        containerName = containerInfo.get("container_name_k8s", " ")
        # print(containerName)
        cluster = containerInfo.get("clustername", " ")
        pod = containerInfo.get("pod_name", " ")
        namespace = containerInfo.get("pod_namespace", " ")

        container_dict[containerUID] = {
            "containerUID": containerUID,
            "cluster": cluster,
            "pod": pod,
            "namespace": namespace,
        }

# match the container--> connection data based on connection key.
matched_data = []
for connection_key, connection_data in conn_dict.items():
    if connection_key in container_dict:
        matched_data.append(
            {
                "containerUID": connection_key,
                "container_k8s": containerName,
                "pod": pod,
                "cluster": cluster,
                "namespace": namespace,
                "payload": conn_dict[connection_key]["payload"],
            }
        )

# print the data in tabulate manner.
headers = ["containerID", "container_k8s", "pod", "cluster", "namespace", "payload"]
table = tabulate(
    [list(d.values()) for d in matched_data], headers=headers, tablefmt="plain"
)

print(table)
