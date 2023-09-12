import json

data_dict = {}

# Test: container, cluster, pod,payload, namespace that talk to port 53
# note pod is comparison key for the test.


# get the first 4 fields  from connections and increase the count if you find it again
with open("connections.json", "r") as file:
    for connections in file:
        connection = json.loads(connections)
        container = connection.get("container_uid", "cont:not present")
        cluster = connection.get("cluster_uid", "clust:not present")
        pod = connection.get("pod_uid", "pod:not present")
        payload = connection.get("payload", " ")

        key = (container, cluster, pod, payload)
        if key in data_dict:
            data_dict[key] += 1
        else:
            data_dict[key] = 1

# get the pod, namespace
pod_list = []
with open("pods.json", "r") as file:
    for pods in file:
        pod = json.loads(pods)
        pod_uid = pod.get("id", " ")
        namespace = pod.get("metadata", {}).get("namespace", "not found")
        pods_data = {"pod_uid": pod_uid, "namespace": namespace}
        pod_list.append(pods_data)


# find if the pod_list has pod, if yes append to new_keys_to_update
# update here is to associate the namespace with the pod.
new_keys_to_update = []
for key in data_dict.keys():
    pod = key[2]
    if key[2] == " ":
        continue
    else:
        for pods in pod_list:
            if pod == pods.get("pod_uid"):
                new_keys_to_update.append(key)
                namespace = pods.get("namespace")
                break


for key in new_keys_to_update:
    value = data_dict.pop(key)
    new_key = (key[0], key[1], key[2], key[3], namespace)
    data_dict[new_key] = value

for k, v in data_dict.items():
    print(k, v)
