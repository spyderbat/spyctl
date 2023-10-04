import json


from tabulate import tabulate
import zulu


# helper function
def epoch_to_zulu(epoch):
    try:
        return zulu.Zulu.fromtimestamp(epoch).format("YYYY-MM-ddTHH:mm:ss") + "Z"
    except Exception:
        return epoch


data = {}
writefile = open("connections8126.json", "w")

# step 1: spyctl get connections > connect.json and spyctl get containers > container8126.json
# then filter connection data for port 53 from connnection.json
# and write to connection53.json
with open("connect.json", "r") as file:
    for line in file:
        parsed_json = json.loads(line)
        if parsed_json["remote_port"] == 8126:
            writefile.write(json.dumps(parsed_json) + "\n")

writefile.close()

# load connection data and add it to the conn dictionary
# if any field is not present default is " "
conn_dict = {}
with open("connections8126.json", "r") as file:
    for connections in file:
        connection = json.loads(connections)
        containerUID = connection.get("container_uid", " ")
        cgroup = connection.get("cgroup", " ")
        payload = connection.get("payload", " ")
        conn_dict[containerUID] = {"cgroup": cgroup}
        connectionID = connection.get("id", " ")


# load container data and add it to the container dict with
# containerUID as the key
container_dict = {}
with open("containers8126.json", "r") as file:
    for containers in file:
        containerInfo = json.loads(containers)
        containerUID = containerInfo.get("id", " ")
        containerName = containerInfo.get("container_name", " ")
        container_created = containerInfo.get("created", " ")
        container_created = epoch_to_zulu(container_created)
        cluster = containerInfo.get("clustername", " ")
        pod = containerInfo.get("pod_name", " ")
        image = containerInfo.get("image_runtime", " ")
        state = containerInfo.get("container_state_runtime", " ")
        container_dict[containerUID] = {
            "containerUID": containerUID,
            "containerName": containerName,
            "created": epoch_to_zulu(container_created),
            "state": state,
            "cluster": cluster,
            "pod": pod,
            "image": image,
        }


# match the container--> connection data based on connection key.
matched_data = []

for connection_key, connection_data in conn_dict.items():
    if connection_key in container_dict:
        matched_data.append(
            {
                "containerID": connection_key,
                "container": containerName,
                "containerCreated": container_created,
                "state": state,
                "pod": pod,
                "cluster": cluster,
                "image": image,
                "cgroup": connection_data["cgroup"],
            }
        )


# print the data in tabulate manner.
headers = [
    "containerID",
    "containerName",
    "containerCreated",
    "state",
    "pod",
    "cluster",
    "image",
    "cgroup",
]
table = tabulate(
    [list(d.values()) for d in matched_data], headers=headers, tablefmt="plain"
)

print(table)
