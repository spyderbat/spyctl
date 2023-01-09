======================
Spyctl Basics Tutorial
======================

This tutorial will teach you how to configure Spyctl. It will also provide
basic instructions for viewing your Spyderbat resources and baselining your
services & containers.

Prerequisites
=============

.. If you haven't already done so, follow the instructions for installing Spyctl:

.. .. toctree::
..    :maxdepth: 1

..    /getting_started/install

In order to properly utilize Spyctl you must:
* Have a Spyderbat account
* Have installed at least one Spyderbat Nano Agent installed on a machine of your choosing
* Have generated a key to access the Spyderbat API

Initial Configuration
=====================

Create a Secret
---------------

Creating at least one secret is required for Spyctl to get your data via the
Spyderbat API.

#. Base64 encode the api key you generated from the Spyderbat Console:::

    echo -n <apikey> | base64 -w 1000

#. Use the base64 encoded key to create a secret:::

    spyctl create secret apicfg -k <base64 encoded apikey> NAME

For example:::

    spyctl create secret apicfg -k ZXlKaGJHY2lPaUpJVXpJMU5pSXNJbXRwWkNJNkluTmlJaXdpZ
    Ehsd0lqb2lTbGRVSW4wLmV5SmFaWZRLk9EbGxuSEdlb1picnVzajhPUnZ1amZWTk1VS2pfTTctV3FCMl
    pUc2J5NXM= staging_secret

**Spyctl saves secrets in** *$HOME/.spyctl/.secrets/secrets*

Configure a Context
-------------------

Contexts will let Spyctl know where to look for data. The broadest possible Context
is organization-wide. This means that when you run Spyctl commands, the Spyderbat API
will return results relevant to your entire organization.::

    spyctl config set-context --org <ORG NAME> --secret <SECRET NAME> NAME

For example:::

    spyctl config set-context --org "John's Org" --secret staging_secret staging_context

You can view your configuration by issuing the following command:::

    spyctl config view

You should see something like this:::

    apiVersion: spyderbat/v1
    kind: Config
    contexts:
    - name: staging_context
      secret: staging_secret
      context:
      organization: John\'s Org
    current-context: staging_context

**The global configuration file located at** *$HOME/.spyctl/config*

**Note:** *It is possible to create more specific contexts, such as a group of machines
or a specific container image. You can think of the fields in your context as filters.

.. Follow this link to learn more about contexts:* :ref:`Contexts`

Basic usage
===========

Now that you have configured a context for your organization you can use Spyctl
to view and manage your Spyderbat Resources.

The 'get' Command
-----------------

`spyctl get <resource>` is the command to retrieve data from the Spyderbat API.

To retrieve the list of machines with the Spyderbat Nano Agent installed issue the
following command:::

    spyctl get machines

By default, this displays a table of information about the resources you retrieved. It is
possible to output these resources in other formats:::

    spyctl get machines -o yaml

This will combine all of the retrieved resources into a single yaml document. If you wish
to retrieve a specific object you may also supply a name or id with the command:::

    spyctl get machines -o yaml NAME_OR_ID


.. **Note:** *A full list of resources can be found here:* :ref:`Resources`

Baselining Workflow
===================

When you install the Spyderbat Nano Agent on a machine


With Spyctl you can create a baseline for the individual containers and Linux services
running on your machines. Baselines are powerful because they give you a compact picture
of what your containers and services are doing. 


From the perspective of Spyctl, as baseline is a compact
representation of a process tree, ingress connections, and egress connections. **Baselines
are important because they are the bu**

For example:::

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

