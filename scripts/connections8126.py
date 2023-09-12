import json

data_dict = {}

# Test: cluster, namespace, image_name, image_id that talk to TCP 8126
# note comparison key for the test is cluster.

# get the cluster from connections and increase the count by 1 everytime you find it again
with open("conn8126.json", "r") as file:
    for connections in file:
        connection = json.loads(connections)
        # if not present the default value is " "
        cluster = connection.get("cluster_uid", "none")
        key = cluster
        if key in data_dict:
            data_dict[key] += 1
        else:
            data_dict[key] = 1

# get the cluster, namespace and image name for the pods and append in pod list
pod_list = []
with open("pods8126.json", "r") as file:
    for pods in file:
        pod = json.loads(pods)
        namespace = pod.get("metadata", {}).get("namespace", "not found")
        cluster_uid = pod.get("cluster_uid", " ")
        container = pod.get("spec", {}).get("containers", [])
        if "image" in container[0]:
            image = container[0]["image"]
        pods_data = {"cluster_uid": cluster_uid, "image": image, "namespace": namespace}
        pod_list.append(pods_data)


# if the cluster is present in pods list append it
# to the new_keys_to_update (update here is to get namespace and image for it)

new_keys_to_update = []

for key in data_dict.keys():
    cluster = key
    if cluster == "none":
        continue
    else:
        for pods in pod_list:
            if cluster == pods.get("cluster_uid"):
                new_keys_to_update.append(key)
                namespace = pods.get("namespace")
                image = pods.get("image")
                break

for key in new_keys_to_update:
    value = data_dict.pop(key)
    new_key = (key, image, namespace)
    data_dict[new_key] = value

for k, v in data_dict.items():
    print(k, v)
