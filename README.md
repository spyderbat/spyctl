<p align="center">
  <a href="" rel="noopener">
 <img width=200px height=200px src="https://i.imgur.com/nkMr2fl.png" alt="Project logo"></a>
</p>

<h3 align="center">Spyctl</h3>

<div align="center">

[![Status](https://img.shields.io/badge/status-active-success.svg)]()
[![GitHub Issues](https://img.shields.io/github/issues/kylelobo/The-Documentation-Compendium.svg)](https://github.com/spyderbat/policy_manager/issues)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/kylelobo/The-Documentation-Compendium.svg)](https://github.com/spyderbat/policy_manager/pulls)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](/LICENSE)

</div>

---

<p align="center"> A command-line utility for viewing and managing Spyderbat resources
    <br> 
</p>

## 📝 Table of Contents

- [About](#about)
- [Getting Started](#getting_started)
- [Usage](#usage)
- [TODO](../TODO.md)
- [Contributing](../CONTRIBUTING.md)
- [Authors](#authors)

## 🧐 About <a name = "about"></a>

Write about 1-2 paragraphs describing the purpose of your project.

## 🏁 Getting Started <a name = "getting_started"></a>

These instructions will get spyctl up and running on your local machine.

### Prerequisites

```
- Python3.7 or newer
- Spyderbat Account and API key
- Spyderbat Nano Agent installed on 1 or more systems
```

### Installation & Setup

Install spyctl using pip

```
pip install spyctl
```

In order to use spyctl effectively, some user configuration is required.

First create a secret in order to access your data -- ```api_secret.yml```
```
apiVersion: spyderbat/v1
kind: Secret
metadata:
  name: api_secret
type: Opaque
data:
  # Keys can be generated when logged into app.spyderbat.com
  apiKey: <key>
  apiUrl: https://api.prod.spyderbat.com
```

Then run the following command to apply the secret:
```
spyctl apply -f api_secret.yml
```
You can now delete api_secret.yml if desired, spyctl saves the secret in `$HOME/.spyctl/secrets`

The next step is to configure a context. This will let spyctl know where to look for data. The broadest possible context is organization-wide, but you may set more specific contexts by `machine group` (sets of machines that have the spyderbat nano agent installed) and, if you are using Kubernetes, by `cluster` and `namespace`.

Contexts can be even more granular by specifying specific Linux service `cgroups` or for containers `containerName`, `image`, or `imageID`.

#### Organization Context (Beginner)
This is the simplest context, but is great for getting a better understanding of your environment:
```
spyctl config set-context spyderbat_org_context --org "Spyderbat" --secret api_secret
```
#### Machine Group Context (Intermediate)
You can use Machine Group Contexts to get data from a targeted subset of your Spyderbat fleet.

The first step is to create a machine group -- ```dev_group.yml```
```
apiVersion: spyderbat/v1
kind: MachineGroup
metadata:
  name: dev_group
data:
  machines:
  - muid: mach:XXXXX
  - hostname: i_analytics_professional
  - hostname: s_analytics*
```

Then run the following command to apply the machine group:
```
spyctl apply -f dev_group.yml
```

Finally, create the context:
```
spyctl config set-context dev_group_context --org "Spyderbat" --secret api_secret --mach-group dev_group
```
to specify a specific container image:
```
spyctl config set-context dev_group_context --org "Spyderbat" --secret api_secret --mach-group dev_group --image "*/analytic-ingest:latest"
```
#### Cluster Context (Advanced)
This assumes you have a Kubernetes cluster and have installed a Spyderbat Clustermonitor and Spyderbat Nano Agents on each of your nodes in the cluster
```
spyctl config set-context integration_cluster_context --org "Spyderbat" --secret api_secret --cluster "integration1c"
```
To be even more specific you may specify a namespace
```
spyctl config set-context integration_cluster_context --org "Spyderbat" --secret api_secret --cluster "integration1c --namespace "rsvp_web"
```
#### Other Configuration Commands
If you have completed the steps above you now have one or more contexts, and are ready to start viewing and manipulating spyderbat objects.

To view your configuration, simply execute:
```
spyctl config view
```
And you will see something like this:
```
apiVersion: spyderbat/v1
kind: Config
contexts:
- context:
    organization: Spyderbat
    secret: api_secret
  name: spyderbat_org_context
- context:
    organization: Spyderbat
    secret: api_secret
    machineGroup: dev_group
    image: "*/analytic-ingest:latest"
  name: dev_group_context
- context:
    organization: Spyderbat
    secret: api_secret
    cluster: integration1c
    namespace: rsvp_web
  name: integration_cluster_context
current-context: spyderbat_org_context
```
The configuration file is saved in `$HOME/.spyctl/config`

To select a different current context execute:
```
spyctl config use-context integration_cluster_context
```

There may be cases where you are working on a project and would like a specific directory to always use a specific context other than the global default. Running the following command will prompt you through the setup process:
```
spyctl init
```

## 🎈 Usage <a name="usage"></a>
### Explore your Spyderbat environment
From within a configured context, you can use spyctl to view and manage spyderbat resources.

`spyctl get` is the command to view said resources. It will either download artifacts using Spyderbat's API or display documents stored locally, but it is the primary tool for exploring your environment.

To retrieve a list of machines with the spyderbat `Nano Agent` installed issue the following command:
```
spyctl get machines
```
*note: this will only retrieve machines within the current context*

Kubernetes users can also use spyctl like kubectl to `get` certain K8s objects within your Spyderbat fleet such as `clusters`, `namespaces`, and `pods`.

Another key component of Spyderbat is the `Spyderbat Fingerprints` feature. Spyderbat will automatically generate a "fingerprint" of activity for containers and Linux services. This means that you can get a summarized view of what is going on inside a particular container or service including processes, connections, and listening sockets.

These `Spyderbat Fingerprints` can then be used to baseline your containers and services. Ultimately, the baselines can be converted into `Spyderbat Policies` which are effective at both reducing noise and notifying you when deviations from the baseline occur.

To get all `Spyderbat Fingerprints` within the current context you can issue the command:
```
spyctl get fingerprints
```
By default this will return a `Fingerprints Group` object of all fingerprints since the beginning of time, this object can contain a rather large list so it is generally more useful to `get` fingerprints for a specific container or Linux service and for a specific time range. Using `get linux-services` or `get images` will show you what is currently running in your environment, then you can issue the following command to get more specific fingerprints:

```
spyctl get fingerprints --image "*/analytics-ingest:latest" --start-time 2h
```

This will get you all of the fingerprints for containers running an image matching the wildcarded string "`*/analytic-ingest:latest`" for the last two hours.

K8s users can even specify pod and namespace labels
```
spyctl get fingerprints --image "*/analytic-ingest:latest" --namespace-labels "app.kubernetes.io/name=analytics" --pod-labels "env in (prod, dev)"
```

Example of a `Fingerprint Group`:
```
apiVersion: spyderbat/v1
kind: FingerprintGroup
metadata:
  startTime: 1670000035
  endTime: 1670001133
data:
  fingerprints:
  - apiVersion: spyderbat/v1
    kind: SpyderbatFingerprint
    metadata:
      ...
    spec:
      containerSelector:
        image: 42985722144.plm.aws.com/analytics-ingest:latest
        imageID: sha256:6e2e1bce440ec41f53e849e56d5c6716ed7f1e1fa614d8dca2bbda49e5cde29e
        containerName: /ingest_container_83147472713
      podSelector:
        matchLabels:
          env: prod
      namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: analytics
      processPolicy:
      - name: sh
        exe:
        - /bin/dash
        id: sh_0
        euser:
        - root
        children:
        - name: python
          exe:
          - /usr/local/bin/python3.7
          id: python_0
      networkPolicy:
        ingress: []
        egress:
        - to:
          - dnsSelector:
            - mongodb.my_app.svc.cluster.local
          processes:
          - python_0
          ports:
          - protocol: TCP
            port: 27018
  - apiVersion: spyderbat/v1
    kind: SpyderbatFingerprint
    metadata:
    - ...
    spec:
      containerSelector:
        image: 42985722144.plm.aws.com/analytics-ingest:latest
        imageID: sha256:6e2e1bce440ec41f53e849e56d5c6716ed7f1e1fa614d8dca2bbda49e5cde29e
        containerName: /ingest_container_1273684113
      podSelector:
        matchLabels:
          env: dev
      namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: analytics
      processPolicy:
      - ...
      networkPolicy:
        ingress:
        - from:
          - ipBlock:
              cidr: 192.168.1.10/32
          processes:
          - python_0
          ports:
          - protocol: TCP
            port: 8080
        egress: []
```
### Baselining Workflow
With spyctl you can create a compact baseline of activity for any Linux service or container running in your environment. `Spyderbat Baselines` are built from `Fingerprints Groups` from a singular source (e.g. containers that are all running the same image). To create a baseline you may supply a `Fingerprint Group`:
```
spyctl create baseline --f analytics_fingerprint_group.yml > analytics_ingest_baseline.yml
```

It is common practice to edit the baseline so it can be generalized:
```
vim new_baseline.yml
```

Some ways to generalize baselines are to:
- add wildcards to certain fields (e.g. `*/analytic-ingest:latest`)
- expand an ip block's cidr range (e.g. `cidr: 192.168.0.0/16`)

Example `Spyderbat Baseline`:
```
apiVersion: spyderbat/v1
kind: SpyderbatBaseline
metadata:
  name: analytics_ingest_baseline
  type: container
  lastTimestamp: 1670001133
spec:
  containerSelector:
    image: "*/analytic-ingest:latest"
  processPolicy:
  - name: sh
    exe:
    - /bin/dash
    id: sh_0
    euser:
    - root
    children:
    - name: python
      exe:
      - /usr/local/bin/python3.7
      id: python_0
  networkPolicy:
    ingress:
    - from:
      - ipBlock:
          cidr: 192.168.0.0/16
      processes:
      - python_0
      ports:
      - protocol: TCP
        port: 8080
    egress:
    - to:
      - dnsSelector:
        - mongodb.my_app.svc.cluster.local
      processes:
      - python_0
      ports:
      - protocol: TCP
        port: 27017
```

Now that we have an initial baseline its probably best to let the system run for a time. Spyderbat will continue to automatically build and update fingerprints for your deployed Linux services and containers.

After some time passes you may want to verify that the latest fingerprints haven't deviated from the baseline. To do this, issue the following command:
```
spyctl diff -f analytics_ingest_baseline.yml --latest
```
This will get a `Fingerprint Group` from the baseline's `lastTimestamp` to now and display any processes, connections, or listening sockets that do not fit within the baseline. You may also compare a `Spyderbat Baseline` to fingerprints from a specific time range.

If these changes should be part of the baseline the following command will merge them in:
```
spyctl merge -f analytics_ingest_baseline.yml --latest > updated_analytics_baseline.yml
```

Best practice is to continue these steps of generalizing and merging deviations until the baseline has stabilized.

### Policy Workflow

Once you have a stable baseline the next step is to create a `Spyderbat Policy`

Benefits of a `Spyderbat Policy` include:
- reduce redflag noise by excluding all flags within a policy
- generate new redflags whenever a deviations from policy occur
- response actions such as webhook notifications or even automatically killing a pod
- security as policy

`Spyderbat Policies` can be created from `Fingerprint Groups` or `Spyderbat Baselines` as follows:
```
spyctl create policy -f updated_analytics_baseline.yml > analytics_policy.yml
```

This will create a local `Spyderbat Policy` object that can be edited and merged with `Fingerprints Groups` just like a `Spyderbat Baseline`, however policies have a `response` section in the `spec` and can be applied to the Spyderbat backend.

for example:
```
apiVersion: spyderbat/v1
kind: SpyderbatPolicy
metadata:
  name: analyics_ingest_policy
  type: container
  uid: <uuid>
  lastTimestamp: 1670001133
spec:
  containerSelector:
    image: */analytic-ingest:latest
  processPolicy:
  - ...
  networkPolicy:
    ingress:
    - ...
    egress:
    - ...
  response:
    default:
      severity: high
    actions: []
```

Here's an example response action -- A `webhook` that sends a message to a specified Slack channel when a container in the dev environment deviates from the policy
```
response:
    default:
      severity: high
    actions:
    - podSelector:
        matchLabels:
          env: dev
      actionName: webhook
      url: https://hooks.slack.com/services/XXXXXXX/XXXXXXX/XXXXXXXXX
      template: slack
      severity: low
```
What this means is that when a container running an image matching `*/analytic-ingest:latest` deviates from `analytics_ingest_policy` from a K8s Pod in the `dev` environment, Spyderbat will generate a low severity flag, and send a message with information about the deviation to the specified url.

Local `Spyderbat Policies` have not been `applied` so they will not generate flags or take response actions for deviations yet. In order to enable the policy you may issue the command:
```
spyctl apply -f analytics_policy.yml
```
To see a list of `Spyderbat Policies` that have been applied, issue the following command:
```
spyctl get policies
```
the output looks like this:
```
$ spyctl get policies
ID        Type          Name                       Processes   Ingress   Egress
<uuid>    container     analytics_ingest_policy     4           1         1
```
At this point you now have an applied policy that will reduce noise, generate flags on deviations, and take response actions.

Should deviations occur there are a few steps you can take to update the policy. The first option is to merge in the latest `Fingerprint Group` similar to the Baseline Workflow:
```
spyctl get analyics_ingest_policy -o yaml > analytics_policy.yml
```
```
spyctl diff -f analytics_policy.yml --latest
```
if there are deviations:
```
spyctl merge -f analytics_policy.yml --latest > updated_analytics_policy.yml
```
This performs a `merge` on the local file, then the final step is to apply the changes:

```
spyctl apply -f updated_analytics_policy.yml
```

Since policies can be running for a while without a deviation, merging `Fingerprint Groups` with the `--latest` flag can be time consuming. In this case you can specify a time range or, alternatively, use the deviation `redflags` to get the right fingerprints.
```
spyctl get deviations analytics_ingest_policy --latest > deviations.yml
```
This will display the deviations specific to the applied policy since its lastTimestamp. If the deviations are normal activity, issue the following to merge them into the policy:

To merge the deviations into the policy:

```
spyctl merge -f analytics_policy.yml --with-file deviations.yml > updated_analytics_policy.yml
```

Again, the final step is to apply the changes:

```
spyctl apply -f updated_analytics_policy.yml
```

## ✍️ Authors <a name = "authors"></a>

- [@brent-spyder](\https://github.com/brent-spyder) - Developer
- [@spyder-kyle](https://github.com/spyder-kyle) - Developer
