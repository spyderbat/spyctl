from fastapi.testclient import TestClient
import os

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
        "object": TEST_POLICY,
        "diff_objects": TEST_FINGERPRINT_LIST,
        "org_uid": ORG,
        "api_key": API_KEY,
        "api_url": API_URL,
    }
    response = client.post("/api/v1/diff", json=data)
    assert response.status_code == 200


def test_validate():
    data = {"object": TEST_POLICY}
    response = client.post("/api/v1/validate", json=data)
    assert response.status_code == 200
