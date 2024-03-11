"""
Contains the ClusterPolicy class, which is used to define a policy for a
kubernetes cluster.
"""

from typing import Dict, List

import spyctl.resources.cluster_rulesets as crs
import spyctl.resources.clusters as c
import spyctl.schemas_v2 as schemas
import spyctl.spyctl_lib as lib


def create_cluster_policy(
    name: str,
    mode: str,
    st: float,
    et: float,
    no_rs_gen: bool,
    clusters: List[str] = None,
    namespace: List[str] = None,
) -> Dict:
    """
    Create a cluster policy and output it to stdout in the desired format.

    Args:
        name (str): The name of the cluster policy.
        mode (str): The mode of the cluster policy.
        st (str): The start time of the cluster policy.
        et (str): The end time of the cluster policy.
        no_rs_gen (bool): Whether or not to generate rulesets.
        cluster (str, optional): The cluster name. Defaults to None.
        namespace (List[str], optional): Scope ruleset rules to namespace(s).
    """
    metadata = schemas.GuardianMetadataModel(name=name, type=lib.POL_TYPE_CLUS)
    rulesets: List[crs.ClusterRuleset] = []
    spec = schemas.ClusterPolicySpecModel(
        clusterSelector=schemas.ClusterSelectorModel(
            cluster="PROVIDE_CLUSTER_NAME"
        ),
        mode=mode,
        enabled=True,
        rulesets=[],
    )
    if clusters:
        lib.try_log("Validating cluster(s) exist within the system.")
        spec.cluster_selector.cluster = (
            clusters[0] if len(clusters) == 1 else clusters
        )
        for clus in clusters:
            if not c.cluster_exists(clus):
                lib.err_exit(f"Cluster {clus} does not exist")
            if no_rs_gen:
                continue
            filters = {
                "cluster": clus,
            }
            if namespace:
                filters["namespace"] = namespace
            rulesets.append(
                crs.create_ruleset(
                    f"{clus}_ruleset", True, (st, et), **filters
                )
            )
    policy = schemas.ClusterPolicyModel(
        apiVersion=lib.API_VERSION,
        kind=lib.POL_KIND,
        metadata=metadata,
        spec=spec,
    )
    if not rulesets:
        rv = policy.dict(by_alias=True, exclude_unset=True)
    else:
        items = []
        for ruleset in rulesets:
            rs_name = ruleset.name
            spec.rulesets.append(rs_name)
            items.append(ruleset.as_dict())
        pol_dict = policy.dict(by_alias=True, exclude_unset=True)
        items.append(pol_dict)
        rv = {
            lib.API_FIELD: lib.API_VERSION,
            lib.ITEMS_FIELD: items,
        }
    return rv
