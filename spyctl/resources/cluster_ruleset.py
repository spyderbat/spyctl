from typing import Dict, List, Tuple, Optional

import spyctl.api as api
import spyctl.config.configs as cfg
import spyctl.resources.api_filters as af
import spyctl.spyctl_lib as lib

CLUSTER_RULESET_RULE_TYPE_CONT = "container"
CLUSTER_RULESET_RULE_TYPES = [CLUSTER_RULESET_RULE_TYPE_CONT]

NS_LABEL = "kubernetes.io/metadata.name"


class RulesObject:
    def __init__(self, verb: str) -> None:
        self.verb = verb


class NamespaceLabels:
    def __init__(self, namespace_labels: List[str] = []):
        self.namespace_labels = namespace_labels

    def as_dict(self):
        rv = {
            lib.NAMESPACE_SELECTOR_FIELD: {
                lib.MATCH_LABELS_FIELD: {NS_LABEL: self.namespace_labels}
            }
        }
        return rv

    def add_namespace(self, namespace: str):
        self.namespace_labels.append(namespace)

    @property
    def first_namespace(self) -> Optional[str]:
        if len(self.namespace_labels) == 0:
            return None
        return self.namespace_labels[0]

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, __class__):
            return False
        return set(self.namespace_labels) == set(__value.namespace_labels)


class DetectedImage:
    def __init__(self, image: str):
        self.image = image
        self.namespaces = set()

    def add_namespace(self, namespace: Optional[str]):
        self.namespaces.add(namespace)

    def namespaces_match(self, other_namespaces: set) -> bool:
        return self.namespaces == other_namespaces


class ContainerRules(RulesObject):
    def __init__(self, verb="allow", include_namespaces=False):
        super().__init__(verb)
        self.images: Dict[str, DetectedImage] = {}
        self.include_namespaces = include_namespaces

    def add_container(self, container: Dict):
        image = container["image"]
        namespaces_labels: Dict = container.get("pod_namespace_labels", {})
        namespace = namespaces_labels.get(NS_LABEL, container.get("namespace"))
        if not namespace:
            lib.try_log(
                f"Container {container['container_name']} with from {image} has no namespace.. skipping",  # noqa: E501
                is_warning=True,
            )
            return
        self.__add_image(image, namespace)

    def as_list(self):
        rv = self.__aggregate_images()
        return rv

    def __aggregate_images(self):
        if self.include_namespaces:
            rv = self.__agg_images_by_ns()
        else:
            rv = [
                {
                    "verb": self.verb,
                    lib.IMAGE_FIELD: sorted(
                        sorted([image.image for image in self.images.values()])
                    ),
                }
            ]
        return rv

    def __agg_images_by_ns(self):
        rv = []
        agg: Dict[Tuple, List[str]] = {}
        for image in self.images.values():
            namespaces = tuple(sorted(image.namespaces))
            agg.setdefault(namespaces, [])
            agg[namespaces].append(image.image)
        for namespaces, images in agg.items():
            rv.append(
                {
                    lib.NAMESPACE_SELECTOR_FIELD: {
                        lib.MATCH_LABELS_FIELD: {
                            "kubernetes.io/metadata.name": namespaces[0]
                            if len(namespaces) == 1
                            else list(sorted(namespaces))
                        }
                    },
                    "verb": self.verb,
                    lib.IMAGE_FIELD: sorted(images),
                }
            )

        def sort_key(item: Dict):
            namespaces = item[lib.NAMESPACE_SELECTOR_FIELD][
                lib.MATCH_LABELS_FIELD
            ][NS_LABEL]
            return namespaces if isinstance(namespaces, str) else namespaces[0]

        rv.sort(key=sort_key)
        return rv

    def __add_image(self, image, namespace):
        dti = self.images.setdefault(image, DetectedImage(image))
        dti.add_namespace(namespace)


class ClusterRuleset:
    def __init__(self, name: str, cluster: str = None):
        self.name = name
        self.rules: Dict[str, Dict] = {}  # verb -> type -> RulesObject
        self.cluster = cluster

    def add_rules(
        self, verb: str, rules_type: str, include_namespaces: bool
    ) -> RulesObject:
        rules = self.rules.get(verb, {}).get(rules_type)
        if rules:
            return rules
        if rules_type == CLUSTER_RULESET_RULE_TYPE_CONT:
            rules = ContainerRules(verb, include_namespaces)
            self.rules.setdefault(verb, {})[rules_type] = rules
            return rules
        else:
            lib.err_exit(f"Unknown rules type: {rules_type}")

    def as_dict(self):
        return self.__as_cluster_ruleset_dict()

    def __as_cluster_ruleset_dict(self):
        if not self.cluster:
            lib.err_exit("Cluster name or UID is required for cluster ruleset")
        rv = {
            lib.API_FIELD: lib.API_VERSION,
            lib.KIND_FIELD: lib.CLUSTER_RULESET_RESOURCE.kind,
            lib.METADATA_FIELD: {
                lib.NAME_FIELD: self.name,
            },
            lib.SPEC_FIELD: {
                lib.RULES_FIELD: self.__compile_rules(),
            },
        }
        return rv

    def __compile_rules(self) -> Dict:
        rv = {}
        for _, rules in self.rules.items():
            for rules_type, rules_obj in rules.items():
                rv.setdefault(rules_type, []).extend(rules_obj.as_list())
        rv = {k: rv[k] for k in sorted(rv) if rv[k] != []}
        return rv


def create_blank_ruleset(name: str):
    pass


def create_ruleset(
    name: str, generate_rules, time, **filters
) -> ClusterRuleset:
    ruleset = ClusterRuleset(name)
    if generate_rules:
        generate_cluster_ruleset(
            ruleset, CLUSTER_RULESET_RULE_TYPES, time, **filters
        )
    return ruleset


def generate_cluster_ruleset(
    ruleset: ClusterRuleset, rule_types, time, **filters
):
    cluster = filters.get(lib.CLUSTER_OPTION)
    if not cluster:
        lib.err_exit("Cluster name or UID is required for cluster ruleset")
    ruleset.cluster = cluster
    if not rule_types:
        rule_types = CLUSTER_RULESET_RULE_TYPES
    for rule_type in rule_types:
        if rule_type == CLUSTER_RULESET_RULE_TYPE_CONT:
            generate_container_rules(ruleset, time, **filters)
    return ruleset


def generate_container_rules(ruleset: ClusterRuleset, time, **filters):
    filters = filters.copy()
    include_namespaces = False
    if namespaces := filters.get(lib.NAMESPACE_OPTION, []):
        include_namespaces = True
        if "__all__" in namespaces:
            # We don't need to filter for specific namespaces at this point
            filters.pop(lib.NAMESPACE_OPTION)
    ctx = cfg.get_current_context()
    sources, filters = af.Containers.build_sources_and_filters(**filters)
    pipeline = af.Containers.generate_pipeline(filters=filters)
    lib.try_log("Generating container rules...")
    container_rules: ContainerRules = ruleset.add_rules(
        "allow", CLUSTER_RULESET_RULE_TYPE_CONT, include_namespaces
    )
    for container in api.get_containers(
        *ctx.get_api_data(), sources, time, pipeline, limit_mem=True
    ):
        container_rules.add_container(container)
