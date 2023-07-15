# Mocking API Functionality
def mock_get_machines(api_url, api_key, org_uid):
    mock_machine = {
        "uid": "mach:xxxXXxxxX",
        "name": "spyderbat-dev",
        "org_uid": "spyderbatuid",
        "runtime_description": "spyderbat-dev",
        "runtime_details": {
            "agent_registration_uid": "",
            "src_uid": "mach:-Y4VTygrRj8",
            "ip_addresses": [
                "172.17.0.1",
            ],
            "mac_addresses": [
                "ff:ff:ff:ff:ff:ff",
            ],
            "request_ip": "1.1.1.1",
            "hostname": "spyderbat-dev",
            "agent_arch": "x86_64",
            "agent_version": "v1.1.71",
            "uname": "5.4.0-153-generic",
            "os_name": "linux",
            "os_pretty_name": "Ubuntu 20.04.6 LTS",
            "boot_time": 1689379897.2830372,
            "cpu_make": "GenuineIntel",
            "cpu_model": "Intel(R) Core(TM) i9-9980HK CPU @ 2.40GHz",
            "cpu_cores": 4,
            "memory_total_gb": 15.622344970703125,
            "agent_status": "Agent Running",
            "agent_type": 0,
        },
        "valid_from": "2023-07-11T17:34:23Z",
        "valid_to": "0001-01-01T00:00:00Z",
        "resource_name": "srn:agent::xxxxxxxxx:xxxxxxxxxxxxxxxx",
        "last_data": "2023-07-15T12:17:44Z",
        "last_ingest_chunk_end_time": "2023-07-15T12:17:39Z",
        "last_stored_chunk_end_time": "2023-07-15T12:17:39Z",
        "agent_registration_uid": "xxxxxxxxxxxxxxxxxxxxx",
        "agent_type": 0,
    }
    return [mock_machine]


def mock_get_clusters(api_url, api_key, org_uid):
    mock_cluster = {
        "uid": "clus:xxxxxxxxxxx",
        "name": "mock_cluster",
        "org_uid": "spyderbatuid",
        "cluster_details": {
            "cluster_uid": "xxxxxxxxxxxxxxxxxxxxxxxx",
            "cluster_name": "mock_cluster",
            "agent_uid": "mach:xxxxxxxxxxxxx",
            "src_uid": "xxxxxxxxxxxxxxxxxxxx",
            "cluid": "clus:xxxxxxxxxxx",
            "spyder_tags": {
                "CLUSTER_NAME": "mock_cluster",
                "baz": "bat",
                "foobar": "true",
            },
        },
        "valid_from": "2022-11-22T15:08:28Z",
        "valid_to": "0001-01-01T00:00:00Z",
        "resource_name": "srn:cluster::xxxxxxxxxxxx:clus:xxxxxxxxxxxxxx",
        "last_data": "2022-11-22T18:11:35Z",
    }
    return [mock_cluster]


def mock_get_deployments(api_url, api_key, org_uid, clusters, time):
    mock_deployment = {
        "schema": "model_k8s_deployment::1.0.0",
        "id": "deployment:xxxxxxxxxxxxxxxxxxxxxx",
        "status": "active",
        "version": 1689418766,
        "time": 1689422416.837507,
        "valid_from": 1689166499.9791923,
        "expire_at": 1689425999.999999,
        "cluster_uid": "clus:xxxxxxxxxxx",
        "clusterid": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "cluster_name": "",
        "kind": "Deployment",
        "metadata": {
            "annotations": {
                "deployment.kubernetes.io/revision": "10",
                "meta.helm.sh/release-name": "elastic-svc",
                "meta.helm.sh/release-namespace": "default",
            },
            "creationTimestamp": "2023-04-12T18:42:08Z",
            "generation": 10,
            "labels": {
                "app.kubernetes.io/instance": "elastic-svc",
                "app.kubernetes.io/managed-by": "Helm",
            },
            "name": "elastic-svc",
            "namespace": "default",
            "resourceVersion": "34970156",
            "uid": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        },
        "kuid": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "spec": {"replicas": 1},
        "k8s_status": {},
    }
    return [mock_deployment]


def mock_get_namespaces(api_url, api_key, org_uid, clusters, time):
    mock_namespace = {
        "cluster_name": "mock_cluster",
        "cluster_uid": "clus:xxxxxxxxxxx",
        "namespaces": {
            "default",
            "mock",
        },
    }
    return [mock_namespace]


def mock_get_nodes(api_url, api_key, org_uid, clusters, time):
    mock_node = {
        "schema": "model_k8s_node::1.0.0",
        "id": "node:xxxxxxxxxxxxxxxxxxxxxx",
        "status": "active",
        "version": 1689425045,
        "time": 1689425066.5426638,
        "valid_from": 1689166499.9791923,
        "expire_at": 1689425999.999999,
        "cluster_uid": "clus:xxxxxxxxxxx",
        "clusterid": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "cluster_name": "mock_cluster",
        "kind": "Node",
        "metadata": {
            "annotations": {},
            "creationTimestamp": "2023-02-08T18:01:53Z",
            "labels": {
                "app": "mock",
            },
            "name": "mock_node",
            "resourceVersion": "45556759",
            "uid": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        },
        "kuid": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "spec": {},
        "k8s_status": {
            "addresses": [],
            "allocatable": {},
            "capacity": {},
            "conditions": [],
            "daemonEndpoints": {},
            "images": [],
            "nodeInfo": {},
            "volumesAttached": [],
            "volumesInUse": [],
        },
        "muid": "mach:FomNj5G1TJc",
    }
    return [mock_node]


def mock_get_pods(api_url, api_key, org_uid, clusters, time):
    mock_pod = {
        "schema": "model_k8s_pod::1.0.0",
        "id": "pod:xxxxxxxxxxx:xxxxxxxxxx",
        "status": "active",
        "version": 1689422366,
        "time": 1689422464.61505,
        "valid_from": 1689166501.0163338,
        "expire_at": 1689425999.999999,
        "cluster_uid": "clus:xxxxxxxxxxx",
        "clusterid": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "cluster_name": "mock_cluster",
        "kind": "Pod",
        "metadata": {
            "annotations": {},
            "creationTimestamp": "2023-06-30T15:29:49Z",
            "generateName": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "labels": {
                "app": "mock",
            },
            "name": "mock_pod",
            "namespace": "mock",
            "ownerReferences": [],
            "resourceVersion": "21281954",
            "uid": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        },
        "kuid": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "spec": {
            "containers": [],
            "dnsPolicy": "ClusterFirst",
            "enableServiceLinks": True,
            "nodeName": "mock_node",
            "preemptionPolicy": "PreemptLowerPriority",
            "priority": 0,
            "restartPolicy": "Always",
            "schedulerName": "default-scheduler",
            "securityContext": {},
            "serviceAccount": "xxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "serviceAccountName": "xxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "terminationGracePeriodSeconds": 30,
            "tolerations": [],
            "volumes": [],
        },
        "k8s_status": {"phase": "Running"},
        "owner_uid": "replicaset:xxxxxxxxxxxxxxxxxxxxxx",
        "owner_kind": "ReplicaSet",
        "owner_name": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "deployment_uid": "deployment:xxxxxxxxxxxxxxxxxxxxxx",
        "deployment_name": "mock_deployment",
        "node_uid": "node:xxxxxxxxxxx:xxxxxxxxxx",
        "muid": "mach:xxxxxxxxxxx",
    }
    return [mock_pod]


def mock_get_redflags(api_url, api_key, org_uid, time):
    mock_redflag = {
        "id": "event_alert:xxxxxxxxxxx:xxxxxx:xxxxx:curl",
        "schema": "event_redflag:suspicious_command:1.1.0",
        "description": "SYSTEM as UID 100 ran curl with suspicious command /usr/bin/curl http://mock.mock",
        "ref": "proc:xxxxxxxxxxx:xxxxxx:xxxxx",
        "short_name": "command_curl",
        "class": [
            "redflag",
            "proc",
            "command",
            "high_severity",
            "suspicious",
            "curl",
        ],
        "severity": "high",
        "time": 1689424074.0437524,
        "routing": "customer",
        "version": 2,
        "linkback": "https://mock.com",
        "muid": "mach:xxxxxxxxxxx",
        "container": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "container_uid": "cont:xxxxxxxxxxapi_url, api_key, org_uid, timex:xxxxxxxxxxx:xxxxxxxxxxxx",
        "cluster_uid": "clus:xxxxxxxxxxx",
        "pod_uid": "pod:xxxxxxxxxxx:xxxxxxxxxx",
        "mitre_mapping": [
            {
                "technique": "T1105",
                "technique_name": "Ingress Tool Transfer",
                "url": "https://attack.mitre.org/techniques/T1105",
                "created": "2017-05-31T21:31:16.408Z",
                "modified": "2020-03-20T15:42:48.595Z",
                "stix": "attack-pattern--e6919abc-99f9-4c6c-95a5-14761e7b2add",
                "tactic": "TA0011",
                "tactic_name": "Command and Control",
                "platform": "Linux",
            }
        ],
        "auid": 4294967295,
        "name": "curl",
        "args": ["/usr/bin/curl", "http://mock.mock"],
        "auser": "SYSTEM",
        "euser": "UID 100",
        "ancestors": ["sh", "5", "runc", "containerd-shim", "systemd"],
        "false_positive": False,
        "uptime": 5498575.702408075,
        "traces": ["trace:xxxxxxxxxxx:xxxxxxxxxxx:xxxxx:suspicious_command"],
        "traces_suppressed": False,
    }
    return [mock_redflag]


def mock_get_opsflags(api_url, api_key, org_uid, time):
    mock_opsflag = {
        "id": "event_alert:xxxxxxxxxxx",
        "schema": "event_opsflag:memoryleak:1.1.0",
        "description": "Memory leaking over time",
        "ref": "mach:xxxxxxxxxxx",
        "short_name": "memory_leak",
        "class": ["opsflag", "mach", "memory_leak", "medium_severity"],
        "severity": "medium",
        "time": 1689422557.9508052,
        "routing": "customer",
        "version": 1,
        "linkback": "https://mock.mock",
        "muid": "mach:xxxxxxxxxxx",
    }
    return [mock_opsflag]


def mock_get_fingerprints(
    api_url, api_key, org_uid, muids, time, fprint_type=None, pipeline=None
):
    mock_fingerprint = {
        "expire_at": 1689425999.999999,
        "id": "fprint:linux-service:xxxxxxxxxxx:update-motd.service:xxxxxx:xxxx",
        "cgroup": "systemd:/system.slice/update-motd.service",
        "muid": "mach:xxxxxxxxxxx",
        "apiVersion": "spyderbat/v1",
        "kind": "SpyderbatFingerprint",
        "metadata": {
            "name": "update-motd.service",
            "id": "fprint:linux-service:xxxxxxxxxxx:update-motd.service:xxxxxx:xxxx",
            "type": "linux-service",
            "checksum": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "org_uid": "spyderbatuid",
            "muid": "mach:xxxxxxxxxxx",
            "root": "proc:xxxxxxxxxxx:xxxxxx:9785",
            "firstTimestamp": 1689423122.9874985,
            "latestTimestamp": 1689423288.2522442,
            "version": 1689423128,
        },
        "spec": {
            "serviceSelector": {
                "cgroup": "systemd:/system.slice/update-motd.service"
            },
            "machineSelector": {"hostname": "mock_machine"},
            "processPolicy": [
                {
                    "name": "update-motd",
                    "exe": ["/usr/bin/bash"],
                    "id": "update-motd_0",
                    "euser": ["root"],
                }
            ],
            "networkPolicy": {
                "ingress": [],
                "egress": [
                    {
                        "to": [{"ipBlock": {"cidr": "1.1.1.1/32"}}],
                        "processes": ["yum_0"],
                        "ports": [{"protocol": "TCP", "port": 80}],
                    },
                ],
            },
        },
        "root_puid": "proc:xxxxxxxxxxx:xxxxxx:9785",
        "service_name": "update-motd.service",
        "proc_fprint_len": 18,
        "ingress_len": 0,
        "egress_len": 3,
        "schema": "model_fingerprint:linux_svc:1.0.0",
        "status": "closed",
        "time": 1689423288.2522442,
        "valid_from": 1689423122.9874985,
        "last_seen": 1689423126.8817828,
        "version": 1689423128,
        "checksum": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "valid_to": 1689423288.2522442,
    }
    return [mock_fingerprint]
