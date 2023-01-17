.. _Basics_Tutorial:

======================
Basics Tutorial
======================

This tutorial will teach you how to configure Spyctl. It will also provide
basic instructions for viewing your Spyderbat |Resources| and baselining your
services & containers.

Prerequisites
=============

If you haven't already done so, follow the instructions
for installing Spyctl: :ref:`Installation<install>`

In order to properly utilize Spyctl you must:

* Have a Spyderbat account
* Have installed at least one |s_na| installed on a machine of your choosing
* Have generated a key to access the |api|

Initial Configuration
=====================

In this section you will learn how to configure Spyctl to enable data retrieval
from across your entire organization. To do so, you must first
create an |secret| and then use that |secret| to set a |context|. An |secret|
encapsulates your Spyderbat API credentials; the |context| specifies where
Spyctl should look for data when interacting with the |api|
(e.g., organization, cluster, machine, service, or container image).

.. _create_a_secret:

Create an APISecret
-------------------

An |secret| encapsulates your Spyderbat API credentials.  You must create at least one |secret|
in order for Spyctl to access your data via theSpyderbat API.

To create an |secret|, use an api key generated from the |console|:

.. code-block:: console

    $ spyctl config set-apisecret -k <apikey> -u "https://api.spyderbat.com" NAME

For example:

.. code-block:: console

    $ spyctl config set-apisecret -k ZXlKaGJHY2lPaUpJVXpJMU5pSXNJbXRwWkNJNkluTm\
    lJaXdpZEhsd0lqb2lTbGRVSW4wLmV5SmxlSEFpT2pFM01EUTVPVGM1TWpBc0ltbGhkQ0k2TVRZM\
    016UTJNVGt4T1N3aWFYTnpJam9pYTJGdVoyRnliMjlpWVhRdWJtVjBJaXdpYzNWaUlqb2ljSGhX\
    YjBwMlVFeElXakJIY1VJd2RXMTNTMEVpZlEuZGpxWkRCOTNuUnB4RUF0UU4yQ0ZrOU5zblQ5Z2Q\
    tN0tYT081TEZBZC1GSQ== -u "https://api.spyderbat.com" my_secret

    Set new apisecret 'my_secret' in '/home/demouser/.spyctl/.secrets/secrets'

.. note:: 
    Spyctl saves |secrets| in *$HOME/.spyctl/.secrets/secrets*

.. _set_a_context:

Set a Context
-------------------

|contexts| will let Spyctl know where to look for data. The broadest possible |context|
is organization-wide. This means that when you run Spyctl commands, the Spyderbat API
will return results relevant to your entire organization. 

.. note::
    For the ``--org`` field in the following command you may supply the name of your
    organization which can be found in the top right of the |console|
    or the organization UID which can be found in your web browser's url when logged into the
    |console|: https://app.spyderbat.com/app/org/UID/dashboard.

.. code-block:: console

    $ spyctl config set-context --org <ORG NAME or UID> --secret <SECRET NAME> NAME

For example:

.. code-block:: console

    $ spyctl config set-context --org "John's Org" --secret my_secret my_context
    Set new context 'my_context' in configuration file '/home/demouser/.spyctl/config'.

You can view your configuration by issuing the following command:

.. code-block:: console

    $ spyctl config view

You should see something like this:

.. code-block:: yaml

    apiVersion: spyderbat/v1
    kind: Config
    contexts:
    - name: my_context
      secret: my_secret
      context:
        organization: John's Org
    current-context: my_context

.. note::
    The global configuration file is located at *$HOME/.spyctl/config*

.. note::
    It is possible to create more specific contexts, such as a group of machines
    or a specific container image. You can think of the fields in your context as filters
    to limit your scope. Follow this link to learn more about contexts: :ref:`Contexts`

Basic Usage
===========

Now that you have configured a |context| for your organization you can use Spyctl
to view and manage your Spyderbat |resources|. In this section you will learn about the
``get`` command.

The 'get' Command
-----------------

To retrieve data from the Spyderbat API, you can use the ``get`` command:

.. code-block:: console

    $ spyctl get RESOURCE [OPTIONS] [NAME_OR_ID]

To retrieve the list of |machs| with the |s_na| installed, issue the
following command:

.. code-block:: console

    $ spyctl get machines

By default, this displays a table of information about the resources you retrieved. It is
possible to output these resources in other formats:

.. code-block:: console

    $ spyctl get machines -o yaml

This will combine all of the retrieved resources into a single yaml document. If you wish
to retrieve a specific object you may also supply a name or id with the command:

.. code-block:: console

    $ spyctl get machines -o yaml NAME_OR_ID


.. note::
    A full list of resources can be found here: :ref:`Resources`

.. _Baselining_Workflow:

Baselining Workflow
===================

In this section you will learn about how auto-generated |s_fprints| are viewed and how
they are used to |baseline| your services and containers. You will also learn how to
manage |baselines| once you've created them.

Viewing Fingerprints
--------------------

When you install the |s_na|, Spyderbat immediately starts building up
|fprints| for the services and containers running on the machine. |fprints| are used
to create |baselines|. |fprints| are a compact representation of process
and network activity for a given instance of a service or container,
and can update over time.

To see a tabular summary of the |fprints| in your current |context| issue the command:

.. code-block:: console

    $ spyctl get fingerprints

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
            image: python_webserver:latest
            imageID: sha256:6e2e1bce440ec41f53e849e56d5c6716ed7f1e1fa614d8dca2bbda49e5cde29e
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
            image: python_webserver:latest
            imageID: sha256:6e2e1bce440ec41f53e849e56d5c6716ed7f1e1fa614d8dca2bbda49e5cde29e
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

Every |fprint| will have the same four fields, ``apiVersion``, ``kind``, ``metadata``, and
``spec``. The |fprint_grp| shown above is for a specific container image. In the spec of
every |fprint| you will find one or more ``Selector`` fields. For now, just know that the
``containerSelector`` is used to group container |fprints| together and the ``serviceSelector``
is used to group service |fprints| together. In a separate tutorial you will learn how
``Selectors`` are used with |policies|.

Creating a Baseline
-------------------

|baselines| are created from 1 or more |fprint_grps| merged into a single document. The purpose
of a |baseline| is to represent the expected activity of a service or container image.

The first step to create a |baseline| is to retrieve a |fprint_grp| and save it to a file. To
do this, you use the ``get fingerprints`` command mentioned above. This will show you a table
view of the available |fprint_grps|. 

For containers you can use the image or the image ID to retrieve a specific one:

.. code-block:: console

    $ spyctl get fingerprints -o yaml IMAGE_OR_IMAGE_ID > fprint_grp.yaml

For services you can use the cgroup:

.. code-block:: console

    $ spyctl get fingerprints -o yaml CGROUP > fprint_grp.yaml

For example, we want to save the |fprint_grp| for a container image
``python_webserver:latest``:

.. code-block:: console

    $ spyctl get fingerprints -o yaml "python_webserver:latest" > python_srv_fprints.yaml

We just saved the auto-generated |fprints| for all instances of the container image to a
single yaml file.

The next step is to create a |baseline| from that |fprint_grp|. The command to create a
|baseline| is:

.. code-block:: console

    $ spyctl create baseline --from-file FILENAME > baseline.yaml

Continuing the example from above, we would issue this command:

.. code-block:: console

    $ spyctl create baseline --from-file python_srv_fprints.yaml > python_srv_baseline.yaml

The resulting |baseline| would look something like this:

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
              cidr: 192.168.1.10/32
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

In this example the root process of the container is ``sh`` run as ``root`` with
a child ``python`` process. The ``ingress`` traffic is coming from ``192.168.1.10/32``
and the only ``egress`` traffic is going to a database with the dns name
``mongodb.my_app.svc.cluster.local``.

.. _Generalizing_A_Baseline:

Generalizing a Baseline
-----------------------

|fprints| only capture activity that has occurred, so if you want your |baselines|
to include other expected activity, you can take steps to generalize the document.
This can be done by simply editing the baseline document with your favorite text editor.

For example:

.. code-block:: console

    $ vim python_srv_baseline.yaml

Some ways to generalize a |baseline| are to:

- add wildcards to text fields (e.g. updating the image to incorporate all versions):

.. code-block:: none

    image: python_webserver:*

- expand an ip block's cidr range (e.g. say there is a /16 network that we expect traffic from):

.. code-block:: none

    cidr: 192.168.0.0/16

Managing A Baseline
-------------------

We now have a |baseline| ``python_srv_baseline.yaml`` that we have generalized. The goal now is
to stabilize the |baseline|. Your services and containers will continue to generate updated
|fprints| which may contain activity that deviates from the |baseline|. The way to detect this
is with the ``diff`` command:

.. code-block:: console

    $ spyctl diff -f BASELINE_FILE --latest

For example:

.. code-block:: console

    $ spyctl diff -f python_srv_baseline.yaml --latest

The output of the diff command will display all activity that doesn't match the |baseline|.
If there are deviations, and those deviations should be added to the |baseline|, you can
use the ``merge`` command to add them to the |baseline|:

.. code-block:: console

    $ spyctl merge -f BASELINE_FILE --latest > merged_baseline.yaml

For example:

.. code-block:: console

    $ spyctl merge -f python_srv_baseline.yaml --latest > python_srv_merged_baseline.yaml

.. warning:: 
    Never redirect output to the same file you are using as input, the file will be wiped
    before spyctl can read it.

At this point you may want to edit the file again to generalize more fields. Repeat these
management steps until you're satisfied that your |baseline| has stabilized.

Our stable (for now) baseline now looks as follows:

.. code-block:: yaml

    apiVersion: spyderbat/v1
    kind: SpyderbatBaseline
    metadata:
      name: webserver_baseline
      type: container
      latestTimestamp: 1670001133
    spec:
      containerSelector:
        image: "python_webserver:*"
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

What's Next
===========

* :ref:`Policy Management Tutorial<Policy_Management>`

.. |api| replace:: :ref:`Spyderbat API<Spyderbat_API>`
.. |console| replace:: :ref:`Spyderbat Console<Spyderbat_Console>`
.. |context| replace:: :ref:`Context<Contexts>`
.. |contexts| replace:: :ref:`Contexts<Contexts>`
.. |baselines| replace:: :ref:`Baselines<Baselines>`
.. |baseline| replace:: :ref:`Baseline<Baselines>`
.. |fprints| replace:: :ref:`Fingerprints<Fingerprints>`
.. |fprint| replace:: :ref:`Fingerprint<Fingerprints>`
.. |fprint_grp| replace:: :ref:`Fingerprint Group<Fingerprint_Groups>`
.. |fprint_grps| replace:: :ref:`Fingerprint Groups<Fingerprint_Groups>`
.. |mach| replace:: :ref:`Machine<Machines>`
.. |machs| replace:: :ref:`Machines<Machines>`
.. |na| replace:: :ref:`Nano Agent<Nano_Agent>`
.. |policies| replace:: :ref:`Policies<Policies>`
.. |policy| replace:: :ref:`Policy<Policies>`
.. |resource| replace:: :ref:`Resource<Resources>`
.. |resources| replace:: :ref:`Resources<Resources>`
.. |secret| replace:: :ref:`APISecret<Secrets>`
.. |secrets| replace:: :ref:`APISecrets<Secrets>`

.. |s_na| replace:: :ref:`Spyderbat Nano Agent<Nano_Agent>`
.. |s_baselines| replace:: :ref:`Spyderbat Baselines<Baselines>`
.. |s_baseline| replace:: :ref:`Spyderbat Baseline<Baselines>`
.. |s_fprints| replace:: :ref:`Spyderbat Fingerprints<Fingerprints>`
.. |s_fprint| replace:: :ref:`Spyderbat Fingerprint<Fingerprints>`
.. |s_policies| replace:: :ref:`Spyderbat Policies<Policies>`
.. |s_policy| replace:: :ref:`Spyderbat Policy<Policies>`