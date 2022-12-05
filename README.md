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

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See [deployment](#deployment) for notes on how to deploy the project on a live system.

### Prerequisites

```
- Python3.7 or newer
- Spyderbat Account and API key
- Spyderbat Nano Agent installed on 1 or more systems
```

### Installation & Setup

A step by step series of examples that tell you how to get a development env running.

Install spyctl using pip

```
pip install spyctl
```

In order to use spyctl effectively, some user configuration is required.

First create a secret in order to access your data -- ```newsecret.yml```
```
apiVersion: spyderbat/v1
kind: Secret
metadata:
  name: newsecret
type: Opaque
data:
  # Keys can be generated when logged into app.spyderbat.com
  apiKey: <key>
  apiUrl: https://api.prod.spyderbat.com
```

Then run the following command to apply the secret:
```
spyctl apply -f newsecret.yml
```
You can now delete newsecret.yml if desired, spyctl saves the secret in ```/location/of/file```

The next step is to configure a context. This will let spyctl know where to look for data. The broadest possible context is organization-wide, but you may set more specific contexts by ```machine group``` (sets of machines that have the spyderbat nano agent installed) and, if you are using Kubernetes, by ```cluster``` and ```namespace```.

#### Organization Context (Beginner)
This is the simplest context, but is great for getting a better understanding of your environment:
```
spyctl config set-context my_org_context --org "My Organization" --secret newsecret
```
#### Machine Group Context (Intermediate)
You can use Machine Group Contexts to get data from a targeted subset of your Spyderbat fleet.

The first step is to create a machine group -- ```mgroup.yml```
```
apiVersion: spyderbat/v1
kind: MachineGroup
metadata:
  name: newgroup
data:
  machines:
  - mach:XXXXX
  - mach:YYYYY
```

Then run the following command to apply the machine group:
```
spyctl apply -f mgroup.yml
```

Finally, create the context:
```
spyctl config set-context my_group_context --org "My Organization" --secret newsecret --mach-group newgroup
```
#### Cluster Context (Advanced)
This assumes you have a Kubernetes cluster and have installed a Spyderbat Clustermonitor and Spyderbat Nano Agents on each of your nodes in the cluster
```
spyctl config set-context my_cluster_context --org "My Organization" --secret newsecret --cluster my_cluster
```
To be even more specific you may specify a namespace
```
spyctl config set-context my_cluster_context --org "My Organization" --secret newsecret --cluster my_cluster --namespace my_namespace
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
    organization: My Organization
    secret: newsecret
  name: my_org_context
- context:
    organization: My Organization
    secret: newsecret
    machineGroup: newgroup
  name: my_group_context
- context:
    organization: My Organization
    secret: newsecret
    cluster: my_cluster
    namespace: my_namespace
  name: my_cluster_context
current-context: my_org_context
```
The configuration file is saved in `$HOME/.config/spyctl/config` for Linux users

To select a different current context execute:
```
spyctl config use-context my_cluster_context
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

To get `Spyderbat Fingerprints` you can issue the command:
```
spyctl get fingerprints
```
By default this will return a `Fingerprints Group` object of all fingerprints generated in the last hour, this object can contain a rather large list so it is generally more useful to `get` fingerprints for a specific container or Linux service. Using `get linux-services` or `get images` will show you what is currently running in your environment, then you can issue the following command to get more specific fingerprints:

```
spyctl get fingerprints --image my/application_image:latest
```

This will get you all of the fingerprints for containers running `my/application_image:latest` for the last hour.

K8s users can even specify pod and namespace labels
```
spyctl get fingerprints --image my/application_image:latest --namespace-labels "app.kubernetes.io/name=my_app" --pod-labels "env in (prod, dev)"
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
        image: my/application_image:latest
        imageID: sha256:6e2e1bce440ec41f53e849e56d5c6716ed7f1e1fa614d8dca2bbda49e5cde29e
        containerName: /my_app_container
      podSelector:
        matchLabels:
          env: prod
      namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: my_app
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
            port: 27017
  - apiVersion: spyderbat/v1
    kind: SpyderbatFingerprint
    metadata:
    - ...
    spec:
      containerSelector:
        image: my/application_image:latest
        imageID: sha256:6e2e1bce440ec41f53e849e56d5c6716ed7f1e1fa614d8dca2bbda49e5cde29e
        containerName: /my_app_container
      podSelector:
        matchLabels:
          env: dev
      namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: my_app
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
spyctl create baseline --from-file my_fingerprint_group.yml
```

or you may directly create a `Spyderbat Baseline` like this:
```
spyctl create baseline --image my/application_image:latest
```
*Internally, this command will build a `Fingerprint Group` from the last hour and immediately create a baseline*

To view the baseline you just created you can run the command:
```
spyctl get baselines
```
example output:
```
$ spyctl get baselines
ID                Type          Name                            Processes   Ingress   Egress
base:XXXXXXXXX    container     my_application_image_baseline   4           1         1
```

To view the baseline's yaml:
```
spyctl get baseline my_application_image_baseline -o yaml
```

It is common practice to edit the baseline so it can be generalized:
```
spyctl edit my_application_image_baseline
```

Some ways to generalize baselines are to:
- add wildcards to certain fields (e.g. `image: my/application_image*`)
- expand an ip block's cidr range (e.g. `cidr: 192.168.0.0/16`)

Example `Spyderbat Baseline`:
```
apiVersion: spyderbat/v1
kind: SpyderbatBaseline
metadata:
  name: my_application_image_baseline
  type: container
  lastTimestamp: 1670001133
spec:
  containerSelector:
    image: my/application_image*
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
spyctl diff --baseline my_application_image_baseline --latest
```
This will get a `Fingerprint Group` from the baseline's `lastTimestamp` to now and display any processes, connections, or listening sockets that do not fit within the baseline. You may also compare a `Spyderbat Baseline` to fingerprints from a specific time range.

If these changes should be part of the baseline the following command will merge them in:
```
spyctl merge --baseline my_application_image_baseline --latest
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
spyctl create policy --from-baseline my_application_image_baseline
```

This will create a local `Spyderbat Policy` object that can be edited and merged with `Fingerprints Groups` just like a `Spyderbat Baseline`, however policies have a `response` section in the `spec`

for example:
```
apiVersion: spyderbat/v1
kind: SpyderbatPolicy
metadata:
  name: my_application_image_policy
  type: container
  uid: null
  lastTimestamp: 1670001133
spec:
  containerSelector:
    image: my/application_image*
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
To see a list of `Spyderbat Policies` you have created issue the following command:
```
spyctl get policies
```
the output looks like this:
```
$ spyctl get policies
LOCAL:
ID           Type          Name                          Processes   Ingress   Egress
XXXXXXXXX    container     my_application_image_policy   4           1         1

REMOTE:
ID           Type          Name                          Processes   Ingress   Egress
```

To add response actions issue the command:
```
spyctl edit my_application_image_policy
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
What this means is that when a container running the `my/application_image*` image deviates from `my_application_image_policy` from a K8s Pod in the `dev` environment spyderbat will generate a low severity flag, and send a message with information about the deviation to the specified url.

Local `Spyderbat Policies` have not been `applied` so they will not generate flags or take response actions for deviations yet. In order to enable the policy you may issue the command:
```
spyctl apply my_application_image_policy
```
Now running `get policies` will show this:
```
$ spyctl get policies
LOCAL:
ID           Type          Name                          Processes   Ingress   Egress
XXXXXXXXX    container     my_application_image_policy   4           1         1

REMOTE:
ID           Type          Name                                  Processes   Ingress   Egress
YYYYYYYYY    container     my_application_image_policy:applied   4           1         1
```
At this point you now have an applied policy that will reduce noise, generate flags on deviations, and take response actions.

Should deviations occur there are a few steps you can take to update the policy. The first option is to merge in the latest `Fingerprint Group` similar to the Baseline Workflow:
```
spyctl diff my_application_image_policy:applied --latest
```
if there are deviations:
```
spyctl merge my_application_image_policy:applied --latest --apply
```
This performs a `merge` and the `--apply` flag will automatically apply the changes. 

If the `--apply` flag is not provided, this will create a new local policy with the same ID as the remote policy:
```
LOCAL:
ID           Type          Name                          Processes   Ingress   Egress
XXXXXXXXX    container     my_application_image_policy   4           1         1
YYYYYYYYY    container     my_application_image_policy   4           1         1

REMOTE:
ID           Type          Name                                  Processes   Ingress   Egress
YYYYYYYYY    container     my_application_image_policy:applied   4           1         1
```

This new local policy can then be applied and update the remote policy with the same id
```
spyctl apply YYYYYYYYY
```

Since policies can be running for a while without a deviation, `merging` with the `--latest` flag can be time consuming and may outright fail. In this case you can specify a time range or use the deviation `redflags` to get the right fingerprints.
```
spyctl get deviations YYYYYYYYY
```
This will simply display the deviations, issue the following to generate a `Fingerprint Group` from the deviations:
```
spyctl get deviations YYYYYYYYY -o fingerprint-group > deviations.yml
```
To merge the deviations into the policy:
```
spyctl merge YYYYYYYYY --from-file deviations.yml --apply
```

## ✍️ Authors <a name = "authors"></a>

- [@brent-spyder](\https://github.com/brent-spyder) - Developer
- [@spyder-kyle](https://github.com/spyder-kyle) - Developer
