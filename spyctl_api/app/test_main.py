from fastapi.testclient import TestClient
import os

from .main import app

client = TestClient(app)

API_KEY = os.environ.get("API_KEY")
API_URL = os.environ.get("API_URL")
ORG = os.environ.get("ORG")

# cspell:disable
TEST_POLICY = '{\n  "apiVersion": "spyderbat/v1",\n  "kind": "SpyderbatPolicy",\n  "metadata": {\n    "name": "docker.io/guyduchatelet/spyderbat-demo:1",\n    "type": "container",\n    "latestTimestamp": 1686229419.97803\n  },\n  "spec": {\n    "containerSelector": {\n      "image": "docker.io/guyduchatelet/spyderbat-demo:1",\n      "imageID": "sha256:ce6595c9e9c3ed9faf8b7af095473d1d223c8cc4efa453c771767252d357c4af"\n    },\n    "podSelector": {\n      "matchLabels": {\n        "app": "rsvp",\n        "env": "prod",\n        "name": "rsvp-web",\n        "pod-template-hash": "5b4d5c9499",\n        "tier": "frontend"\n      }\n    },\n    "namespaceSelector": {\n      "matchLabels": {\n        "env": "prod",\n        "kubernetes.io/metadata.name": "rsvp-svc-prod"\n      }\n    },\n    "processPolicy": [\n      {\n        "name": "python",\n        "exe": [\n          "/usr/local/bin/python3.7"\n        ],\n        "id": "python_0",\n        "euser": [\n          "root"\n        ],\n        "children": [\n          {\n            "name": "sh",\n            "exe": [\n              "/bin/dash"\n            ],\n            "id": "sh_0",\n            "children": [\n              {\n                "name": "uname",\n                "exe": [\n                  "/bin/uname"\n                ],\n                "id": "uname_0"\n              }\n            ]\n          }\n        ]\n      },\n      {\n        "name": "sh",\n        "exe": [\n          "/bin/dash"\n        ],\n        "id": "sh_1",\n        "euser": [\n          "root"\n        ],\n        "children": [\n          {\n            "name": "python",\n            "exe": [\n              "/usr/local/bin/python3.7"\n            ],\n            "id": "python_1",\n            "children": [\n              {\n                "name": "python",\n                "exe": [\n                  "/usr/local/bin/python3.7"\n                ],\n                "id": "python_2",\n                "children": [\n                  {\n                    "name": "sh",\n                    "exe": [\n                      "/bin/dash"\n                    ],\n                    "id": "sh_2",\n                    "children": [\n                      {\n                        "name": "uname",\n                        "exe": [\n                          "/bin/uname"\n                        ],\n                        "id": "uname_1"\n                      }\n                    ]\n                  }\n                ]\n              }\n            ]\n          }\n        ]\n      }\n    ],\n    "networkPolicy": {\n      "ingress": [],\n      "egress": [\n        {\n          "to": [\n            {\n              "dnsSelector": [\n                "mongodb.rsvp-svc-prod.svc.cluster.local"\n              ]\n            }\n          ],\n          "processes": [\n            "python_0",\n            "python_1",\n            "python_2"\n          ],\n          "ports": [\n            {\n              "protocol": "TCP",\n              "port": 27017\n            }\n          ]\n        }\n      ]\n    },\n    "response": {\n      "default": [\n        {\n          "makeRedFlag": {\n            "severity": "high"\n          }\n        }\n      ],\n      "actions": []\n    }\n  }\n}'  # noqa: E501
TEST_FINGERPRINT_LIST = '[\n  {\n    "apiVersion": "spyderbat/v1",\n    "kind": "SpyderbatFingerprint",\n    "metadata": {\n      "name": "docker.io/guyduchatelet/spyderbat-demo:1",\n      "id": "fprint:k8s-container:tTfnASZWRaY:ZIHFIg:559d01be326f",\n      "type": "container",\n      "checksum": "6faa5df4c3b452c4f13d77bdcb4021c9",\n      "org_uid": "KNUJF8M43WcT2o1qgEts",\n      "muid": "mach:tTfnASZWRaY",\n      "root": "proc:tTfnASZWRaY:ZIHFHw:2179798",\n      "containerID": "559d01be326f93d14f99fee190054a80e0f42f055be70ffd2d9e2f47c717fa4b",\n      "containerName": "docker.io/guyduchatelet/spyderbat-demo:1",\n      "firstTimestamp": 1686226210.5056648,\n      "latestTimestamp": 1686229419.97803,\n      "pod-uid": "pod:mupQ8S67xUo:vQi7hxaGf6",\n      "namespace": "rsvp-svc-prod",\n      "cluster-uid": "clus:mupQ8S67xUo",\n      "version": 1686229197\n    },\n    "spec": {\n      "containerSelector": {\n        "image": "docker.io/guyduchatelet/spyderbat-demo:1",\n        "imageID": "sha256:ce6595c9e9c3ed9faf8b7af095473d1d223c8cc4efa453c771767252d357c4af"\n      },\n      "podSelector": {\n        "matchLabels": {\n          "app": "rsvp",\n          "env": "prod",\n          "name": "rsvp-web",\n          "pod-template-hash": "5b4d5c9499",\n          "tier": "frontend"\n        }\n      },\n      "namespaceSelector": {\n        "matchLabels": {\n          "env": "prod",\n          "kubernetes.io/metadata.name": "rsvp-svc-prod"\n        }\n      },\n      "processPolicy": [\n        {\n          "name": "python",\n          "exe": [\n            "/usr/local/bin/python3.7"\n          ],\n          "id": "python_0",\n          "euser": [\n            "root"\n          ],\n          "children": [\n            {\n              "name": "sh",\n              "exe": [\n                "/bin/dash"\n              ],\n              "id": "sh_0",\n              "children": [\n                {\n                  "name": "uname",\n                  "exe": [\n                    "/bin/uname"\n                  ],\n                  "id": "uname_0"\n                }\n              ]\n            }\n          ]\n        },\n        {\n          "name": "sh",\n          "exe": [\n            "/bin/dash"\n          ],\n          "id": "sh_1",\n          "euser": [\n            "root"\n          ],\n          "children": [\n            {\n              "name": "python",\n              "exe": [\n                "/usr/local/bin/python3.7"\n              ],\n              "id": "python_1",\n              "children": [\n                {\n                  "name": "python",\n                  "exe": [\n                    "/usr/local/bin/python3.7"\n                  ],\n                  "id": "python_2",\n                  "children": [\n                    {\n                      "name": "sh",\n                      "exe": [\n                        "/bin/dash"\n                      ],\n                      "id": "sh_2"\n                    }\n                  ]\n                }\n              ]\n            }\n          ]\n        }\n      ],\n      "networkPolicy": {\n        "ingress": [],\n        "egress": [\n          {\n            "to": [\n              {\n                "dnsSelector": [\n                  "mongodb.rsvp-svc-prod.svc.cluster.local"\n                ]\n              }\n            ],\n            "processes": [\n              "python_0",\n              "python_1",\n              "python_2"\n            ],\n            "ports": [\n              {\n                "protocol": "TCP",\n                "port": 27017\n              }\n            ]\n          }\n        ]\n      }\n    }\n  },\n  {\n    "apiVersion": "spyderbat/v1",\n    "kind": "SpyderbatFingerprint",\n    "metadata": {\n      "name": "docker.io/guyduchatelet/spyderbat-demo:1",\n      "id": "fprint:k8s-container:tTfnASZWRaY:ZIHJ0g:6aa40d09d566",\n      "type": "container",\n      "checksum": "6faa5df4c3b452c4f13d77bdcb4021c9",\n      "org_uid": "KNUJF8M43WcT2o1qgEts",\n      "muid": "mach:tTfnASZWRaY",\n      "root": "proc:tTfnASZWRaY:ZIHJzg:2199996",\n      "containerID": "6aa40d09d566b64e5c230eb273ad946ee4df3fa147b8c70931333b25593ea64b",\n      "containerName": "docker.io/guyduchatelet/spyderbat-demo:1",\n      "firstTimestamp": 1686227410.6981585,\n      "latestTimestamp": 1686229419.97803,\n      "pod-uid": "pod:mupQ8S67xUo:FCOJMUldGw",\n      "namespace": "rsvp-svc-prod",\n      "cluster-uid": "clus:mupQ8S67xUo",\n      "version": 1686229197\n    },\n    "spec": {\n      "containerSelector": {\n        "image": "docker.io/guyduchatelet/spyderbat-demo:1",\n        "imageID": "sha256:ce6595c9e9c3ed9faf8b7af095473d1d223c8cc4efa453c771767252d357c4af"\n      },\n      "podSelector": {\n        "matchLabels": {\n          "app": "rsvp",\n          "env": "prod",\n          "name": "rsvp-web",\n          "pod-template-hash": "5b4d5c9499",\n          "tier": "frontend"\n        }\n      },\n      "namespaceSelector": {\n        "matchLabels": {\n          "env": "prod",\n          "kubernetes.io/metadata.name": "rsvp-svc-prod"\n        }\n      },\n      "processPolicy": [\n        {\n          "name": "python",\n          "exe": [\n            "/usr/local/bin/python3.7"\n          ],\n          "id": "python_0",\n          "euser": [\n            "root"\n          ],\n          "children": [\n            {\n              "name": "sh",\n              "exe": [\n                "/bin/dash"\n              ],\n              "id": "sh_0"\n            }\n          ]\n        },\n        {\n          "name": "sh",\n          "exe": [\n            "/bin/dash"\n          ],\n          "id": "sh_1",\n          "euser": [\n            "root"\n          ],\n          "children": [\n            {\n              "name": "python",\n              "exe": [\n                "/usr/local/bin/python3.7"\n              ],\n              "id": "python_1",\n              "children": [\n                {\n                  "name": "python",\n                  "exe": [\n                    "/usr/local/bin/python3.7"\n                  ],\n                  "id": "python_2",\n                  "children": [\n                    {\n                      "name": "sh",\n                      "exe": [\n                        "/bin/dash"\n                      ],\n                      "id": "sh_2",\n                      "children": [\n                        {\n                          "name": "uname",\n                          "exe": [\n                            "/bin/uname"\n                          ],\n                          "id": "uname_1"\n                        }\n                      ]\n                    }\n                  ]\n                }\n              ]\n            }\n          ]\n        }\n      ],\n      "networkPolicy": {\n        "ingress": [],\n        "egress": [\n          {\n            "to": [\n              {\n                "dnsSelector": [\n                  "mongodb.rsvp-svc-prod.svc.cluster.local"\n                ]\n              }\n            ],\n            "processes": [\n              "python_0",\n              "python_1",\n              "python_2"\n            ],\n            "ports": [\n              {\n                "protocol": "TCP",\n                "port": 27017\n              }\n            ]\n          }\n        ]\n      }\n    }\n  }\n]'  # noqa: E501
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
    response = client.post("/api/v1/create/suppressionpolicy", json=data)
    assert response.status_code == 200


def test_create_guardian_policy():
    data = {
        "input_objects": TEST_FINGERPRINT_LIST,
        "name": "Test Policy",
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
