import json
import os

from fastapi.testclient import TestClient

from .main import app

client = TestClient(app)

API_KEY = os.environ.get("API_KEY", "test_key")
API_URL = os.environ.get("API_URL", "https://test.url.local")
ORG = os.environ.get("ORG", "test_org")

# cspell:disable
TEST_POLICY = '{\n  "apiVersion": "spyderbat/v1",\n  "kind": "SpyderbatPolicy",\n  "metadata": {\n    "name": "docker.io/guyduchatelet/spyderbat-demo:1",\n    "type": "container",\n    "latestTimestamp": 1686229419.97803\n  },\n  "spec": {\n    "containerSelector": {\n      "image": "docker.io/guyduchatelet/spyderbat-demo:1",\n      "imageID": "sha256:ce6595c9e9c3ed9faf8b7af095473d1d223c8cc4efa453c771767252d357c4af"\n    },\n    "podSelector": {\n      "matchLabels": {\n        "app": "rsvp",\n        "env": "prod",\n        "name": "rsvp-web",\n        "pod-template-hash": "5b4d5c9499",\n        "tier": "frontend"\n      }\n    },\n    "namespaceSelector": {\n      "matchLabels": {\n        "env": "prod",\n        "kubernetes.io/metadata.name": "rsvp-svc-prod"\n      }\n    },\n    "mode": "audit",\n    "processPolicy": [\n      {\n        "name": "python",\n        "exe": [\n          "/usr/local/bin/python3.7"\n        ],\n        "id": "python_0",\n        "euser": [\n          "root"\n        ],\n        "children": [\n          {\n            "name": "sh",\n            "exe": [\n              "/bin/dash"\n            ],\n            "id": "sh_0",\n            "children": [\n              {\n                "name": "uname",\n                "exe": [\n                  "/bin/uname"\n                ],\n                "id": "uname_0"\n              }\n            ]\n          }\n        ]\n      },\n      {\n        "name": "sh",\n        "exe": [\n          "/bin/dash"\n        ],\n        "id": "sh_1",\n        "euser": [\n          "root"\n        ],\n        "children": [\n          {\n            "name": "python",\n            "exe": [\n              "/usr/local/bin/python3.7"\n            ],\n            "id": "python_1",\n            "children": [\n              {\n                "name": "python",\n                "exe": [\n                  "/usr/local/bin/python3.7"\n                ],\n                "id": "python_2",\n                "children": [\n                  {\n                    "name": "sh",\n                    "exe": [\n                      "/bin/dash"\n                    ],\n                    "id": "sh_2",\n                    "children": [\n                      {\n                        "name": "uname",\n                        "exe": [\n                          "/bin/uname"\n                        ],\n                        "id": "uname_1"\n                      }\n                    ]\n                  }\n                ]\n              }\n            ]\n          }\n        ]\n      }\n    ],\n    "networkPolicy": {\n      "ingress": [],\n      "egress": [\n        {\n          "to": [\n            {\n              "dnsSelector": [\n                "mongodb.rsvp-svc-prod.svc.cluster.local"\n              ]\n            }\n          ],\n          "processes": [\n            "python_0",\n            "python_1",\n            "python_2"\n          ],\n          "ports": [\n            {\n              "protocol": "TCP",\n              "port": 27017\n            }\n          ]\n        }\n      ]\n    },\n    "response": {\n      "default": [\n        {\n          "makeRedFlag": {\n            "severity": "high"\n          }\n        }\n      ],\n      "actions": []\n    }\n  }\n}'  # noqa: E501
TEST_FINGERPRINT_LIST = '[\n  {\n    "apiVersion": "spyderbat/v1",\n    "kind": "SpyderbatFingerprint",\n    "metadata": {\n      "name": "docker.io/guyduchatelet/spyderbat-demo:1",\n      "id": "fprint:k8s-container:tTfnASZWRaY:ZIHFIg:559d01be326f",\n      "type": "container",\n      "checksum": "6faa5df4c3b452c4f13d77bdcb4021c9",\n      "org_uid": "KNUJF8M43WcT2o1qgEts",\n      "muid": "mach:tTfnASZWRaY",\n      "root": "proc:tTfnASZWRaY:ZIHFHw:2179798",\n      "containerID": "559d01be326f93d14f99fee190054a80e0f42f055be70ffd2d9e2f47c717fa4b",\n      "containerName": "docker.io/guyduchatelet/spyderbat-demo:1",\n      "firstTimestamp": 1686226210.5056648,\n      "latestTimestamp": 1686229419.97803,\n      "pod-uid": "pod:mupQ8S67xUo:vQi7hxaGf6",\n      "namespace": "rsvp-svc-prod",\n      "cluster-uid": "clus:mupQ8S67xUo",\n      "version": 1686229197\n    },\n    "spec": {\n      "containerSelector": {\n        "image": "docker.io/guyduchatelet/spyderbat-demo:1",\n        "imageID": "sha256:ce6595c9e9c3ed9faf8b7af095473d1d223c8cc4efa453c771767252d357c4af"\n      },\n      "podSelector": {\n        "matchLabels": {\n          "app": "rsvp",\n          "env": "prod",\n          "name": "rsvp-web",\n          "pod-template-hash": "5b4d5c9499",\n          "tier": "frontend"\n        }\n      },\n      "namespaceSelector": {\n        "matchLabels": {\n          "env": "prod",\n          "kubernetes.io/metadata.name": "rsvp-svc-prod"\n        }\n      },\n      "processPolicy": [\n        {\n          "name": "python",\n          "exe": [\n            "/usr/local/bin/python3.7"\n          ],\n          "id": "python_0",\n          "euser": [\n            "root"\n          ],\n          "children": [\n            {\n              "name": "sh",\n              "exe": [\n                "/bin/dash"\n              ],\n              "id": "sh_0",\n              "children": [\n                {\n                  "name": "uname",\n                  "exe": [\n                    "/bin/uname"\n                  ],\n                  "id": "uname_0"\n                }\n              ]\n            }\n          ]\n        },\n        {\n          "name": "sh",\n          "exe": [\n            "/bin/dash"\n          ],\n          "id": "sh_1",\n          "euser": [\n            "root"\n          ],\n          "children": [\n            {\n              "name": "python",\n              "exe": [\n                "/usr/local/bin/python3.7"\n              ],\n              "id": "python_1",\n              "children": [\n                {\n                  "name": "python",\n                  "exe": [\n                    "/usr/local/bin/python3.7"\n                  ],\n                  "id": "python_2",\n                  "children": [\n                    {\n                      "name": "sh",\n                      "exe": [\n                        "/bin/dash"\n                      ],\n                      "id": "sh_2"\n                    }\n                  ]\n                }\n              ]\n            }\n          ]\n        }\n      ],\n      "networkPolicy": {\n        "ingress": [],\n        "egress": [\n          {\n            "to": [\n              {\n                "dnsSelector": [\n                  "mongodb.rsvp-svc-prod.svc.cluster.local"\n                ]\n              }\n            ],\n            "processes": [\n              "python_0",\n              "python_1",\n              "python_2"\n            ],\n            "ports": [\n              {\n                "protocol": "TCP",\n                "port": 27017\n              }\n            ]\n          }\n        ]\n      }\n    }\n  },\n  {\n    "apiVersion": "spyderbat/v1",\n    "kind": "SpyderbatFingerprint",\n    "metadata": {\n      "name": "docker.io/guyduchatelet/spyderbat-demo:1",\n      "id": "fprint:k8s-container:tTfnASZWRaY:ZIHJ0g:6aa40d09d566",\n      "type": "container",\n      "checksum": "6faa5df4c3b452c4f13d77bdcb4021c9",\n      "org_uid": "KNUJF8M43WcT2o1qgEts",\n      "muid": "mach:tTfnASZWRaY",\n      "root": "proc:tTfnASZWRaY:ZIHJzg:2199996",\n      "containerID": "6aa40d09d566b64e5c230eb273ad946ee4df3fa147b8c70931333b25593ea64b",\n      "containerName": "docker.io/guyduchatelet/spyderbat-demo:1",\n      "firstTimestamp": 1686227410.6981585,\n      "latestTimestamp": 1686229419.97803,\n      "pod-uid": "pod:mupQ8S67xUo:FCOJMUldGw",\n      "namespace": "rsvp-svc-prod",\n      "cluster-uid": "clus:mupQ8S67xUo",\n      "version": 1686229197\n    },\n    "spec": {\n      "containerSelector": {\n        "image": "docker.io/guyduchatelet/spyderbat-demo:1",\n        "imageID": "sha256:ce6595c9e9c3ed9faf8b7af095473d1d223c8cc4efa453c771767252d357c4af"\n      },\n      "podSelector": {\n        "matchLabels": {\n          "app": "rsvp",\n          "env": "prod",\n          "name": "rsvp-web",\n          "pod-template-hash": "5b4d5c9499",\n          "tier": "frontend"\n        }\n      },\n      "namespaceSelector": {\n        "matchLabels": {\n          "env": "prod",\n          "kubernetes.io/metadata.name": "rsvp-svc-prod"\n        }\n      },\n      "processPolicy": [\n        {\n          "name": "python",\n          "exe": [\n            "/usr/local/bin/python3.7"\n          ],\n          "id": "python_0",\n          "euser": [\n            "root"\n          ],\n          "children": [\n            {\n              "name": "sh",\n              "exe": [\n                "/bin/dash"\n              ],\n              "id": "sh_0"\n            }\n          ]\n        },\n        {\n          "name": "sh",\n          "exe": [\n            "/bin/dash"\n          ],\n          "id": "sh_1",\n          "euser": [\n            "root"\n          ],\n          "children": [\n            {\n              "name": "python",\n              "exe": [\n                "/usr/local/bin/python3.7"\n              ],\n              "id": "python_1",\n              "children": [\n                {\n                  "name": "python",\n                  "exe": [\n                    "/usr/local/bin/python3.7"\n                  ],\n                  "id": "python_2",\n                  "children": [\n                    {\n                      "name": "sh",\n                      "exe": [\n                        "/bin/dash"\n                      ],\n                      "id": "sh_2",\n                      "children": [\n                        {\n                          "name": "uname",\n                          "exe": [\n                            "/bin/uname"\n                          ],\n                          "id": "uname_1"\n                        }\n                      ]\n                    }\n                  ]\n                }\n              ]\n            }\n          ]\n        }\n      ],\n      "networkPolicy": {\n        "ingress": [],\n        "egress": [\n          {\n            "to": [\n              {\n                "dnsSelector": [\n                  "mongodb.rsvp-svc-prod.svc.cluster.local"\n                ]\n              }\n            ],\n            "processes": [\n              "python_0",\n              "python_1",\n              "python_2"\n            ],\n            "ports": [\n              {\n                "protocol": "TCP",\n                "port": 27017\n              }\n            ]\n          }\n        ]\n      }\n    }\n  }\n]'  # noqa: E501
TEST_UID_LIST = '[{"apiVersion": "spyderbat/v1", "kind": "UidList", "metadata": {"startTime": 1690819253.8597443, "endTime": 1690820447.0023878}, "data": {"uniqueIdentifiers": ["fprint:k8s-container:IamnBjwlTR4:ZK7oaw:599d5eaa9314", "fprint:k8s-container:tTfnASZWRaY:ZK6kaQ:fed3ba83dde3"]}}]'  # noqa: E501
TEST_POLICY2 = '{"apiVersion": "spyderbat/v1", "kind": "SpyderbatPolicy", "metadata": {"name": "spyderbat-test", "type": "container", "latestTimestamp": 1672333396.3253918}, "spec": {"containerSelector": {"image": "spyderbat-test", "imageID": "sha256:6e2e1bce440ec41f53e849e56d5c6716ed7f1e1fa614d8dca2bbda49e5cde29e"}, "podSelector": {"matchLabels": {"app": "test", "env": "prod", "name": "test-web", "pod-template-hash": "8665ffd6c6", "tier": "frontend"}}, "namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": "test"}}, "processPolicy": [{"name": "python", "exe": ["/usr/local/bin/python3.7"], "id": "python_0", "euser": ["root"], "children": [{"name": "sh", "exe": ["/bin/dash"], "id": "sh_0", "children": [{"name": "uname", "exe": ["/bin/uname"], "id": "uname_0"}]}]}, {"name": "sh", "exe": ["/bin/dash"], "id": "sh_1", "euser": ["root"], "children": [{"name": "python", "exe": ["/usr/local/bin/python3.7"], "id": "python_1", "euser": ["web-svc"], "children": [{"name": "sh", "exe": ["/bin/dash"], "id": "sh_2", "children": [{"name": "uname", "exe": ["/bin/uname"], "id": "uname_1"}]}]}]}], "networkPolicy": {"ingress": [{"from": [{"ipBlock": {"cidr": "192.168.6.11/32"}}], "processes": ["python_0", "python_1"], "ports": [{"protocol": "TCP", "port": 22}]}], "egress": [{"to": [{"dnsSelector": ["mongodb.local"]}], "processes": ["python_0", "python_1"], "ports": [{"protocol": "TCP", "port": 27017}]}, {"to": [{"ipBlock": {"cidr": "192.168.5.10/32"}}, {"ipBlock": {"cidr": "192.168.5.11/32"}}, {"ipBlock": {"cidr": "192.168.5.12/32"}}, {"ipBlock": {"cidr": "192.168.5.13/32"}}], "processes": ["python_0", "python_1"], "ports": [{"protocol": "TCP", "port": 443}]}]}, "response": {"default": [{"makeRedFlag": {"severity": "high"}}], "actions": []}}}'  # noqa: E501
TEST_POLICY3 = '{"apiVersion": "spyderbat/v1", "kind": "SpyderbatPolicy", "metadata": {"name": "spyderbat-demo-prod", "type": "container", "latestTimestamp": 1690465318.2703452, "uid": "hEzg8jyCCAGwu6OaG1KI", "creationTimestamp": "2023-07-27T13:46:21Z"}, "spec": {"containerSelector": {"image": "*spyderbat-demo*"}, "podSelector": {"matchLabels": {"app": "rsvp", "env": "prod", "name": "rsvp-web", "tier": "frontend"}}, "namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": "rsvp-svc-prod"}}, "mode": "enforce", "processPolicy": [{"name": "sh", "exe": ["/bin/dash"], "id": "sh_0", "euser": ["root"], "children": [{"name": "python", "exe": ["/usr/local/bin/python3.7"], "id": "python_0", "children": [{"name": "python", "exe": ["/usr/local/bin/python3.7"], "id": "python_1", "children": [{"name": "sh", "exe": ["/bin/dash"], "id": "sh_2", "children": [{"name": "uname", "exe": ["/bin/uname"], "id": "uname_1"}]}]}, {"name": "sh", "exe": ["/bin/dash"], "id": "sh_1", "children": [{"name": "uname", "exe": ["/bin/uname"], "id": "uname_0"}]}]}]}, {"name": "python", "exe": ["/usr/local/bin/python3.7"], "id": "python_2", "euser": ["root"], "children": [{"name": "python", "exe": ["/usr/local/bin/python3.7"], "id": "python_3", "children": [{"name": "sh", "exe": ["/bin/dash"], "id": "sh_3", "children": [{"name": "uname", "exe": ["/bin/uname"], "id": "uname_3"}]}]}, {"name": "sh", "exe": ["/bin/dash"], "id": "sh_4", "children": [{"name": "uname", "exe": ["/bin/uname"], "id": "uname_2"}]}]}], "networkPolicy": {"ingress": [{"from": [{"ipBlock": {"cidr": "192.168.4.229/32"}}, {"ipBlock": {"cidr": "192.168.26.23/32"}}, {"ipBlock": {"cidr": "192.168.35.38/32"}}, {"ipBlock": {"cidr": "192.168.73.218/32"}}, {"ipBlock": {"cidr": "192.168.78.61/32"}}], "processes": ["python_1"], "ports": [{"protocol": "TCP", "port": 5000}]}, {"from": [{"ipBlock": {"cidr": "192.168.4.229/32"}}, {"ipBlock": {"cidr": "192.168.26.23/32"}}, {"ipBlock": {"cidr": "192.168.35.38/32"}}, {"ipBlock": {"cidr": "192.168.73.218/32"}}, {"ipBlock": {"cidr": "192.168.78.61/32"}}], "processes": ["python_3"], "ports": [{"protocol": "TCP", "port": 5000}]}], "egress": [{"to": [{"dnsSelector": ["mongodb.rsvp-svc-prod.svc.cluster.local"]}, {"ipBlock": {"cidr": "10.100.66.198/32"}}], "processes": ["python_0", "python_1"], "ports": [{"protocol": "TCP", "port": 27017}]}, {"to": [{"dnsSelector": ["mongodb.rsvp-svc-prod.svc.cluster.local"]}], "processes": ["python_3", "python_2"], "ports": [{"protocol": "TCP", "port": 27017}]}]}, "response": {"default": [{"makeRedFlag": {"severity": "high"}}], "actions": []}}}'  # noqa: E501
TEST_DEVIATIONS = '[{"apiVersion": "spyderbat/v1", "kind": "GuardianDeviation", "metadata": {"type": "ingress", "policy_uid": "hEzg8jyCCAGwu6OaG1KI", "checksum": "123456789ABC", "uid": "audit:123456789"}, "spec": {"processPolicy": [{"policyNode": {"id": "python_1"}}], "networkPolicy": {"ingress": [{"from": [{"ipBlock": {"cidr": "192.168.47.160/32"}}], "ports": [{"protocol": "TCP", "port": 5000}], "processes": ["python_1"]}]}}}, {"apiVersion": "spyderbat/v1", "kind": "GuardianDeviation", "metadata": {"type": "ingress", "policy_uid": "hEzg8jyCCAGwu6OaG1KI", "checksum": "123456789B", "uid": "audit:1234567891"}, "spec": {"processPolicy": [{"policyNode": {"id": "python_1"}}], "networkPolicy": {"ingress": [{"from": [{"ipBlock": {"cidr": "192.168.31.148/32"}}], "ports": [{"protocol": "TCP", "port": 5000}], "processes": ["python_1"]}]}}}, {"apiVersion": "spyderbat/v1", "kind": "GuardianDeviation", "metadata": {"type": "ingress", "policy_uid": "hEzg8jyCCAGwu6OaG1KI", "checksum": "123456789C", "uid": "audit:1234567892"}, "spec": {"processPolicy": [{"policyNode": {"id": "python_1"}}], "networkPolicy": {"ingress": [{"from": [{"ipBlock": {"cidr": "192.168.33.128/32"}}], "ports": [{"protocol": "TCP", "port": 5000}], "processes": ["python_1"]}]}}}, {"apiVersion": "spyderbat/v1", "kind": "GuardianDeviation", "metadata": {"type": "ingress", "policy_uid": "hEzg8jyCCAGwu6OaG1KI", "checksum": "123456789D", "uid": "audit:1234567893"}, "spec": {"processPolicy": [{"policyNode": {"id": "python_1"}}], "networkPolicy": {"ingress": [{"from": [{"ipBlock": {"cidr": "192.168.78.0/24"}}], "ports": [{"protocol": "TCP", "port": 5000}], "processes": ["python_1"]}]}}}, {"apiVersion": "spyderbat/v1", "kind": "GuardianDeviation", "metadata": {"type": "ingress", "policy_uid": "hEzg8jyCCAGwu6OaG1KI", "checksum": "123456789E", "uid": "audit:1234567894"}, "spec": {"processPolicy": [{"policyNode": {"id": "python_1"}}], "networkPolicy": {"ingress": [{"from": [{"ipBlock": {"cidr": "192.168.95.203/32"}}], "ports": [{"protocol": "TCP", "port": 5000}], "processes": ["python_1"]}]}}}, {"apiVersion": "spyderbat/v1", "kind": "GuardianDeviation", "metadata": {"type": "ingress", "policy_uid": "hEzg8jyCCAGwu6OaG1KI", "checksum": "123456789F", "uid": "audit:1234567896"}, "spec": {"processPolicy": [{"policyNode": {"id": "python_1"}}], "networkPolicy": {"ingress": [{"from": [{"ipBlock": {"cidr": "192.168.47.160/32"}}], "ports": [{"protocol": "TCP", "port": 5000}], "processes": ["python_1"]}]}}}]'  # noqa: E501
TEST_POLICY4 = '{"apiVersion": "spyderbat/v1", "kind": "SpyderbatPolicy", "metadata": {"name": "kubelet-service-policy", "type": "linux-service", "creationTimestamp": "2023-08-08T19:05:40Z", "latestTimestamp": 1691517640, "uid": "prMdv07tf2RbHsfjhBBf"}, "spec": {"serviceSelector": {"cgroup": "systemd:/system.slice/kubelet.service"}, "machineSelector": {"hostname": "*.us-west-2.compute.internal"}, "mode": "audit", "enabled": true, "processPolicy": [{"name": "kubelet", "exe": ["/usr/bin/kubelet"], "id": "kubelet_0", "euser": ["root"], "children": [{"name": "*tables", "exe": ["/usr/sbin/xtables-legacy-multi"], "id": "ip6tables_0"}, {"name": "aws-cni", "exe": ["/opt/cni/bin/aws-cni"], "id": "aws-cni_0"}, {"name": "aws-iam-authent", "exe": ["/usr/bin/aws-iam-authenticator"], "id": "aws-iam-authent_0"}, {"name": "egress-v4-cni", "exe": ["/opt/cni/bin/egress-v4-cni"], "id": "egress-v4-cni_0"}, {"name": "ip", "exe": ["/usr/sbin/ip"], "id": "ip_0"}, {"name": "ip", "exe": ["/usr/bin/nsenter"], "id": "ip_1"}, {"name": "iptables", "exe": ["/usr/sbin/xtables-legacy-multi"], "id": "iptables_0"}, {"name": "loopback", "exe": ["/opt/cni/bin/loopback"], "id": "loopback_0"}, {"name": "mount", "exe": ["/usr/bin/mount"], "id": "mount_0"}, {"name": "nsenter", "exe": ["/usr/bin/nsenter"], "id": "nsenter_0"}, {"name": "portmap", "exe": ["/opt/cni/bin/portmap"], "id": "portmap_0"}, {"name": "umount", "exe": ["/usr/bin/umount"], "id": "umount_0"}]}, {"name": "umount", "exe": ["/usr/bin/umount"], "id": "umount_1", "euser": ["root"]}], "networkPolicy": {"ingress": [{"from": [{"ipBlock": {"cidr": "192.168.23.209/32"}}, {"ipBlock": {"cidr": "192.168.92.50/32"}}, {"ipBlock": {"cidr": "192.168.104.223/32"}}, {"ipBlock": {"cidr": "192.168.145.127/32"}}, {"ipBlock": {"cidr": "192.168.174.16/32"}}, {"ipBlock": {"cidr": "192.168.191.225/32"}}], "processes": ["kubelet_0"], "ports": [{"protocol": "TCP", "port": 10250}]}, {"from": [{"ipBlock": {"cidr": "127.0.0.1/32"}}], "processes": ["kubelet_0"], "ports": [{"protocol": "TCP", "port": 35445}]}, {"from": [{"ipBlock": {"cidr": "192.168.31.148/32"}}, {"ipBlock": {"cidr": "192.168.33.128/32"}}, {"ipBlock": {"cidr": "192.168.47.160/32"}}, {"ipBlock": {"cidr": "192.168.65.19/32"}}, {"ipBlock": {"cidr": "192.168.95.203/32"}}], "processes": ["loopback_0"], "ports": [{"protocol": "TCP", "port": 22}]}, {"from": [{"ipBlock": {"cidr": "192.168.47.160/32"}}], "processes": ["ip_0"], "ports": [{"protocol": "TCP", "port": 22}]}, {"from": [{"ipBlock": {"cidr": "192.168.31.148/32"}}, {"ipBlock": {"cidr": "192.168.65.19/32"}}], "processes": ["aws-cni_0"], "ports": [{"protocol": "TCP", "port": 22}]}, {"from": [{"ipBlock": {"cidr": "127.0.0.1/32"}}], "processes": ["kubelet_0"], "ports": [{"protocol": "TCP", "port": 39741}]}, {"from": [{"ipBlock": {"cidr": "127.0.0.1/32"}}], "processes": ["kubelet_0"], "ports": [{"protocol": "TCP", "port": 43833}]}], "egress": [{"to": [{"ipBlock": {"cidr": "169.254.169.254/32"}}], "processes": ["aws-iam-authent_0", "kubelet_0"], "ports": [{"protocol": "TCP", "port": 80}]}, {"to": [{"ipBlock": {"cidr": "35.81.145.33/32"}}, {"ipBlock": {"cidr": "44.213.78.181/32"}}, {"ipBlock": {"cidr": "44.213.79.10/32"}}, {"ipBlock": {"cidr": "44.213.79.86/32"}}, {"ipBlock": {"cidr": "44.213.79.104/32"}}, {"ipBlock": {"cidr": "44.213.79.114/32"}}, {"ipBlock": {"cidr": "44.225.127.230/32"}}, {"ipBlock": {"cidr": "100.21.163.189/32"}}, {"ipBlock": {"cidr": "209.54.180.122/32"}}], "processes": ["kubelet_0"], "ports": [{"protocol": "TCP", "port": 443}]}, {"to": [{"ipBlock": {"cidr": "192.168.2.31/32"}}, {"ipBlock": {"cidr": "192.168.60.58/32"}}, {"ipBlock": {"cidr": "192.168.79.124/32"}}, {"ipBlock": {"cidr": "192.168.85.25/32"}}], "processes": ["kubelet_0"], "ports": [{"protocol": "TCP", "port": 8765}]}, {"to": [{"ipBlock": {"cidr": "192.168.22.154/32"}}, {"ipBlock": {"cidr": "192.168.30.134/32"}}, {"ipBlock": {"cidr": "192.168.32.157/32"}}, {"ipBlock": {"cidr": "192.168.52.88/32"}}, {"ipBlock": {"cidr": "192.168.65.91/32"}}, {"ipBlock": {"cidr": "192.168.68.44/32"}}, {"ipBlock": {"cidr": "192.168.88.198/32"}}, {"ipBlock": {"cidr": "192.168.89.11/32"}}, {"ipBlock": {"cidr": "192.168.93.182/32"}}], "processes": ["kubelet_0"], "ports": [{"protocol": "TCP", "port": 9808}]}, {"to": [{"ipBlock": {"cidr": "127.0.0.1/32"}}], "processes": ["kubelet_0"], "ports": [{"protocol": "TCP", "port": 35445}]}, {"to": [{"dnsSelector": ["localhost"]}, {"ipBlock": {"cidr": "127.0.0.1/32"}}], "processes": ["aws-cni_0"], "ports": [{"protocol": "TCP", "port": 50051}]}, {"to": [{"ipBlock": {"cidr": "192.168.1.26/32"}}], "processes": ["kubelet_0"], "ports": [{"protocol": "TCP", "port": 61779}]}, {"to": [{"ipBlock": {"cidr": "192.168.83.0/32"}}, {"ipBlock": {"cidr": "192.168.94.9/32"}}], "processes": ["kubelet_0"], "ports": [{"protocol": "TCP", "port": 2801}]}, {"to": [{"ipBlock": {"cidr": "192.168.65.252/32"}}], "processes": ["kubelet_0"], "ports": [{"protocol": "TCP", "port": 9445}]}, {"to": [{"ipBlock": {"cidr": "192.168.83.146/32"}}], "processes": ["kubelet_0"], "ports": [{"protocol": "TCP", "port": 20300}]}, {"to": [{"ipBlock": {"cidr": "192.168.72.150/32"}}], "processes": ["kubelet_0"], "ports": [{"protocol": "TCP", "port": 8443}]}, {"to": [{"dnsSelector": ["localhost"]}], "processes": ["kubelet_0"], "ports": [{"protocol": "TCP", "port": 39741}]}, {"to": [{"ipBlock": {"cidr": "127.0.0.1/32"}}], "processes": ["kubelet_0"], "ports": [{"protocol": "TCP", "port": 43833}]}, {"to": [{"ipBlock": {"cidr": "192.168.54.148/32"}}], "processes": ["kubelet_0"], "ports": [{"protocol": "TCP", "port": 8081}]}]}, "response": {"default": [{"makeRedFlag": {"severity": "high"}}], "actions": []}}}'
TEST_DEVIATIONS2 = '[{"apiVersion": "spyderbat/v1", "kind": "GuardianDeviation", "metadata": {"type": "egress", "policy_uid": "prMdv07tf2RbHsfjhBBf", "checksum": "9da20faa9256749a126e45184125d83b", "uid": "audit:prMdv07tf2RbHsfjhBBf:AAYOBtdhxIY:0"}, "spec": {"processPolicy": [{"policyNode": {"id": "kubelet_0"}}], "networkPolicy": {"egress": [{"to": [{"ipBlock": {"cidr": "192.168.54.148/32"}}], "processes": ["kubelet_0"], "ports": [{"protocol": "TCP", "port": 8081}]}]}}}, {"apiVersion": "spyderbat/v1", "kind": "GuardianDeviation", "metadata": {"type": "ingress", "policy_uid": "prMdv07tf2RbHsfjhBBf", "checksum": "57bc0548fbb090a9b59bb97b4ea58ed7", "uid": "audit:prMdv07tf2RbHsfjhBBf:AAYN_1p8zIg:4"}, "spec": {"processPolicy": [{"policyNode": {"id": "kubelet_0"}}], "networkPolicy": {"ingress": [{"from": [{"ipBlock": {"cidr": "127.0.0.1/32"}}], "ports": [{"protocol": "TCP", "port": 43833}], "processes": ["kubelet_0"]}]}}}, {"apiVersion": "spyderbat/v1", "kind": "GuardianDeviation", "metadata": {"type": "ingress", "policy_uid": "prMdv07tf2RbHsfjhBBf", "checksum": "d5d080159b8c8dbdd0a6bd4f850e7d49", "uid": "audit:prMdv07tf2RbHsfjhBBf:AAYOA-Wtlr8:2"}, "spec": {"processPolicy": [{"policyNode": {"id": "kubelet_0"}}], "networkPolicy": {"ingress": [{"from": [{"ipBlock": {"cidr": "192.168.145.127/32"}}], "ports": [{"protocol": "TCP", "port": 10250}], "processes": ["kubelet_0"]}]}}}]'
# cspell:enable


def test_create_suppression_policy():
    data = {
        "type": "trace",
        "name": "Test Suppression Policy",
        "selectors": {
            "trigger-ancestors": ["systemd/foo/bar/baz"],
            "trigger-class": ["this/is/a/test/class"],
            "non-interactive-users": ["root"],
            "interactive_users": ["dev_*", "robert"],
        },
        "org_uid": ORG,
        "api_key": API_KEY,
        "api_url": API_URL,
    }
    print(data)
    response = client.post("/api/v1/create/suppressionpolicy", json=data)
    assert response.status_code == 200


def test_create_guardian_policy():
    data = {
        "input_objects": TEST_FINGERPRINT_LIST,
        "name": "Test Policy",
        "mode": "enforce",
        "org_uid": ORG,
        "api_key": API_KEY,
        "api_url": API_URL,
    }
    response = client.post("/api/v1/create/guardianpolicy", json=data)
    assert response.status_code == 200


def test_merge():
    data = {
        "object": TEST_POLICY,
        "merge_objects": TEST_FINGERPRINT_LIST,
        "org_uid": ORG,
        "api_key": API_KEY,
        "api_url": API_URL,
    }
    response = client.post("/api/v1/merge", json=data)
    assert response.status_code == 200


def test_diff():
    data = {
        "object": TEST_POLICY3,
        "diff_objects": TEST_DEVIATIONS,
        "org_uid": ORG,
        "api_key": API_KEY,
        "api_url": API_URL,
        "full_diff": True,
    }
    response = client.post("/api/v1/diff", json=data)
    data = {
        "object": TEST_POLICY3,
        "diff_objects": TEST_DEVIATIONS,
        "org_uid": ORG,
        "api_key": API_KEY,
        "api_url": API_URL,
        "content_type": "json",
        "include_irrelevant": True,
    }
    response = client.post("/api/v1/diff", json=data)
    assert response.status_code == 200
    data = {
        "object": TEST_POLICY4,
        "diff_objects": TEST_DEVIATIONS2,
        "org_uid": ORG,
        "api_key": API_KEY,
        "api_url": API_URL,
        "content_type": "json",
        "include_irrelevant": True,
    }
    response = client.post("/api/v1/diff", json=data)
    assert response.status_code == 200


def test_validate():
    data = {"object": TEST_POLICY}
    response = client.post("/api/v1/validate", json=data)
    assert response.status_code == 200
    invalid_message = response.json()["invalid_message"]
    assert not invalid_message
    data = {"object": json.dumps(TEST_POLICY2)}
    response = client.post("/api/v1/validate", json=data)
    assert response.status_code == 200
    invalid_message = response.json()["invalid_message"]
    assert not invalid_message


TEST_POLICY2 = {
    "apiVersion": "spyderbat/v1",
    "kind": "SpyderbatPolicy",
    "metadata": {
        "name": "spyderbat-test",
        "type": "container",
        "latestTimestamp": 1672333396.3253918,
    },
    "spec": {
        "containerSelector": {
            "image": "spyderbat-test",
            "imageID": "sha256:6e2e1bce440ec41f53e849e56d5c6716ed7f1e1fa614d8dca2bbda49e5cde29e",  # noqa: E501
        },
        "machineSelector": {
            "hostname": ["spyderbat-test"],
            "machineUID": "mach:12345678",
        },
        "mode": "audit",
        "processPolicy": [
            {
                "name": "python",
                "exe": ["/usr/local/bin/python3.7"],
                "id": "python_0",
                "euser": ["root"],
                "children": [
                    {
                        "name": "sh",
                        "exe": ["/bin/dash"],
                        "id": "sh_0",
                        "children": [
                            {
                                "name": "uname",
                                "exe": ["/bin/uname"],
                                "id": "uname_0",
                            }
                        ],
                    }
                ],
            },
            {
                "name": "sh",
                "exe": ["/bin/dash"],
                "id": "sh_1",
                "euser": ["root"],
                "children": [
                    {
                        "name": "python",
                        "exe": ["/usr/local/bin/python3.7"],
                        "id": "python_1",
                        "euser": ["web-svc"],
                        "children": [
                            {
                                "name": "sh",
                                "exe": ["/bin/dash"],
                                "id": "sh_2",
                                "children": [
                                    {
                                        "name": "uname",
                                        "exe": ["/bin/uname"],
                                        "id": "uname_1",
                                    }
                                ],
                            }
                        ],
                    }
                ],
            },
        ],
        "networkPolicy": {
            "ingress": [
                {
                    "from": [{"ipBlock": {"cidr": "192.168.6.11/32"}}],
                    "processes": ["python_0", "python_1"],
                    "ports": [{"protocol": "TCP", "port": 22}],
                }
            ],
            "egress": [
                {
                    "to": [{"dnsSelector": ["mongodb.local"]}],
                    "processes": ["python_0", "python_1"],
                    "ports": [{"protocol": "TCP", "port": 27017}],
                },
                {
                    "to": [
                        {"ipBlock": {"cidr": "192.168.5.10/32"}},
                        {"ipBlock": {"cidr": "192.168.5.11/32"}},
                        {"ipBlock": {"cidr": "192.168.5.12/32"}},
                        {"ipBlock": {"cidr": "192.168.5.13/32"}},
                    ],
                    "processes": ["python_0", "python_1"],
                    "ports": [{"protocol": "TCP", "port": 443}],
                },
            ],
        },
        "response": {
            "default": [{"makeRedFlag": {"severity": "high"}}],
            "actions": [],
        },
    },
}
