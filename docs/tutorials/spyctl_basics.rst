======================
Spyctl Basics Tutorial
======================

This tutorial will teach you how to configure |spyctl|. It will also provide
basic instructions for viewing your Spyderbat |Resources| and baselining your
services & containers.

Prerequisites
=============

If you haven't already done so, follow the instructions
for installing Spyctl: :ref:`Install<install>`

In order to properly utilize Spyctl you must:
* Have a Spyderbat account
* Have installed at least one |s_na| installed on a machine of your choosing
* Have generated a key to access the `Spyderbat API`

Initial Configuration
=====================

In this section you will learn how to configure Spyctl to 

Create a Secret
---------------

Creating at least one |secret| is required for Spyctl to get your data via the
Spyderbat API.

#. Base64 encode the api key you generated from the `Spyderbat Console`:

.. code-block:: none

    echo -n <apikey> | base64 -w 1000

#. Use the base64 encoded key to create a |secret|:

.. code-block:: none

    spyctl create secret apicfg -k <base64 encoded apikey> NAME

For example:

    spyctl create secret apicfg -k ZXlKaGJHY2lPaUpJVXpJMU5pSXNJbXRwWkNJNkluTmlJaXdpZ
    Ehsd0lqb2lTbGRVSW4wLmV5SmFaWZRLk9EbGxuSEdlb1picnVzajhPUnZ1amZWTk1VS2pfTTctV3FCMl
    pUc2J5NXM= staging_secret

**Spyctl saves secrets in** *$HOME/.spyctl/.secrets/secrets*

Configure a Context
-------------------

|contexts| will let Spyctl know where to look for data. The broadest possible |context|
is organization-wide. This means that when you run Spyctl commands, the Spyderbat API
will return results relevant to your entire organization.::

    spyctl config set-context --org <ORG NAME> --secret <SECRET NAME> NAME

For example:

.. code-block:: none

    spyctl config set-context --org "John's Org" --secret staging_secret staging_context

You can view your configuration by issuing the following command:

.. code-block:: none

    spyctl config view

You should see something like this:

.. code-block:: yaml

    apiVersion: spyderbat/v1
    kind: Config
    contexts:
    - name: staging_context
      secret: staging_secret
      context:
      organization: John's Org
    current-context: staging_context

**The global configuration file located at** *$HOME/.spyctl/config*

**Note:** *It is possible to create more specific contexts, such as a group of machines
or a specific container image. You can think of the fields in your context as filters.
Follow this link to learn more about contexts:* :ref:`Contexts`

Basic Usage
===========

Now that you have configured a |context| for your organization you can use Spyctl
to view and manage your Spyderbat |resources|.

The 'get' Command
-----------------

`spyctl get <resource>` is the command to retrieve data from the Spyderbat API.

To retrieve the list of |machs| with the |s_na| installed issue the
following command:

.. code-block:: none

    spyctl get machines

By default, this displays a table of information about the resources you retrieved. It is
possible to output these resources in other formats:

.. code-block:: none

    spyctl get machines -o yaml

This will combine all of the retrieved resources into a single yaml document. If you wish
to retrieve a specific object you may also supply a name or id with the command:

.. code-block:: none

    spyctl get machines -o yaml NAME_OR_ID


**Note:** *A full list of resources can be found here:* :ref:`Resources`

Baselining Workflow
===================

Fingerprints
------------

When you install the |s_na|, Spyderbat immediately starts building up
|fprints| for the services and containers running on the machine. |fprints| are the foundation
of what baselines are created from. |fprints| are a compact representation of process
and network activity for a given instance of a service or container,
and can update over time.

To see a tabular summary of the fingerprints in your current |context| issue the command:

.. code-block:: none

    spyctl get fingerprints

When you retrieve |fprints| from the Spyderbat API, you are actually retrieving are
|fprint_grps|. Container |fprints| are grouped by image ID, and Linux Service |fprints| are
grouped by cgroup. This means that if the same service is running on multiple machines, all
of the fingerprints across those machines get grouped together. The reason for this will become
clear you move through the baselining process. 

Here is an example of a |fprint_grp|:

.. code-block:: yaml

    apiVersion: spyderbat/v1
    kind: FingerprintGroup
    metadata:
      firstTimestamp: 1670000035
      lastTimestamp: 1670001133
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

Baselines
---------

With Spyctl you can create a |baseline| for the individual containers and Linux services
running on your machines. Baselines are powerful because they give you a compact picture
of what your containers and services are doing. 


From the perspective of Spyctl, as baseline is a compact
representation of a process tree, ingress connections, and egress connections. **Baselines
are important because they are the bu**

For example:

.. code-block:: yaml

    apiVersion: spyderbat/v1
    kind: SpyderbatBaseline
    metadata:
      name: webserver_baseline
      type: container
      latestTimestamp: 1670001133
    spec:
      containerSelector:
        image: "python_webserver:latest"
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

In this example the root process of the container is `sh` run as `root` with a child `python`
process. The `ingress` traffic is coming from `192.168.0.0/16` and the only `egress` traffic
is going to a database with the dns name `mongodb.my_app.svc.cluster.local`.

.. |context| replace:: :ref:`Context<Contexts>`
.. |contexts| replace:: :ref:`Contexts<Contexts>`
.. |baselines| replace:: `Baselines`
.. |baseline| replace:: `Baseline`
.. |fprints| replace:: :ref:`Fingerprints<Fingerprints>`
.. |fprint| replace:: :ref:`Fingerprint<Fingerprints>`
.. |fprint_grp| replace:: :ref:`Fingerprint Group<Fingerprint_Groups>`
.. |fprint_grps| replace:: :ref:`Fingerprint Groups<Fingerprint_Groups>`
.. |mach| replace:: :ref:`Machine<Machines>`
.. |machs| replace:: :ref:`Machines<Machines>`
.. |na| replace:: `Nano Agent`
.. |policies| replace:: :ref:`Policies<Policies>`
.. |policy| replace:: :ref:`Policy<Policies>`
.. |resource| replace:: :ref:`Resource<Resources>`
.. |resources| replace:: :ref:`Resources<Resources>`
.. |spyctl| replace:: `Spyctl:`
.. |secret| replace:: :ref:`Secret<Secrets>`

.. |s_na| replace:: `Spyderbat Nano Agent`
.. |s_baselines| replace:: `Spyderbat Baselines`
.. |s_baseline| replace:: `Spyderbat Baseline`
.. |s_fprints| replace:: :ref:`Spyderbat Fingerprints<Fingerprints>`
.. |s_fprint| replace:: :ref:`Spyderbat Fingerprint<Fingerprints>`
.. |s_policies| replace:: :ref:`Spyderbat Policies<Policies>`
.. |s_policy| replace:: :ref:`Spyderbat Policy<Policies>`