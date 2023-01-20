.. _Policy_Management:

==========================
Policy Management Tutorial
==========================

This tutorial will teach you about |s_policies|. It will explain what they are,
how to create them, how to apply them, and how to manage them.

Prerequisites
=============

If you haven't already done so, it is highly recommended to go through the
:ref:`Basics Tutorial<Basics_Tutorial>` before completing this tutorial.

What is a Spyderbat Policy
==========================

A |s_policy| is the logical next step after you have crafted a stable |s_baseline|. It is both a
way to tune out known |redflags| and also to generate new |redflags| should a |policy| be violated.
|Policies| have four fields, ``apiVersion``, ``kind``, ``metadata`` and ``spec``. 

|Policies| can also be used to take |responses|, such as killing a process, or sending a webhook notification.

The main difference between a |s_policy| and a |s_baseline| is the inclusion of the ``response`` section
within the ``spec``.

Creating a Policy
=================

|policies| can be created from a |baseline| or from a |fprint_grp|. In the
:ref:`Basics Tutorial<Baselining_Workflow>` we downloaded a |fprint_grp|, created a
|baseline| and learned how to generalize and stabilize the |baseline|. We were left
with a file called ``python_srv_merged_baseline.yaml``. We now want to turn this |baseline|
into a |policy|.

To do so, issue the following command:

.. code-block:: console

    $ spyctl create policy --from-file FILENAME > policy.yaml

For example:

.. code-block:: console

    $ spyctl create policy --from-file python_srv_merged_baseline.yaml > python_srv_policy.yaml

.. note:: 
    Running this command does not make any changes to your Spyderbat Environment. It is not until
    you have |applied| a |policy|, that enforcement takes effect.

The |policy| file we just created ``python_srv_policy.yaml`` now has a new ``kind`` "SpyderbatPolicy"
and a ``response`` field in its ``spec``:

.. code-block:: yaml

    response:
      default:
        severity: high
      actions: []

If necessary, update the name in the |policy|'s metadata field.

.. code-block:: console

    $ vim python_srv_policy.yaml

For the example |policy| we will change the name from:

.. code-block:: yaml

    apiVersion: spyderbat/v1
    kind: SpyderbatPolicy
    metadata:
      name: webserver_baseline
    ...

To:

.. code-block:: yaml

    apiVersion: spyderbat/v1
    kind: SpyderbatPolicy
    metadata:
      name: webserver_policy
    ...

Adding Response Actions
------------------------------

When a new |policy| is created it will have a ``default`` |action| and an empty list of ``actions``. The
``severity`` field in the default action indicates the severity that is applied to a |redflag| when
this |policy| is violated. A full list of redflag severities can be found :ref:`here<Redflag_Severities>`.
The |policy| violation |redflag| will be labeled with the highest severity of any taken |actions|,
otherwise, if no actions are taken, the |redflag| will be labeled with the ``default`` severity.

.. code-block:: yaml

    response:
      default:
        severity: high
      actions: []

An example |action| is to receive a Slack notification via webhook when a
|policy| is violated:

.. code-block:: yaml

    actionName: webhook
    url: <url>
    template: slack
    severity: medium

.. note:: 
    Adding |responses| is completely optional. When a |policy| is enforcing,
    Spyderbat will automatically except |redflags| within the |policy|, and generate
    new |redflags| with the default severity when a |policy| is violated. The full
    |responses| documentation can be found :ref:`here<Response_Actions>`.

For example, to add an action, edit your policy file:

.. code-block:: console

    $ vim python_srv_policy.yaml

And add a webhook |action| to the ``actions`` list.

.. code-block:: yaml

    response:
      default:
        severity: high
      actions:
      - actionName: webhook
        url: https://hooks.slack.com/services/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s
        template: slack
        severity: medium


Our |policy| now looks like this:

.. code-block:: yaml

    apiVersion: spyderbat/v1
    kind: SpyderbatPolicy
    metadata:
      name: webserver_policy
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
      response:
        default:
          severity: high
        actions:
        - actionName: webhook
          url: https://hooks.slack.com/services/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s
          template: slack
          severity: medium

Managing A Policy
=================

|policies| can be managed in a similar way to |baselines|. Your services and containers will continue
to generate updated |fprints| which may contain activity that deviates from the |policy|. Other than
viewing the |policy| violation |redflags| in the |console|, you may view these deviations
is with the ``diff`` command:

.. code-block:: console

    $ spyctl diff -f POLICY_FILE --latest

For example:

.. code-block:: console

    $ spyctl diff -f python_srv_policy.yaml --latest

The output of the diff command will display all activity that doesn't match the |policy|.
If there are deviations, and those deviations should be added to the |policy|, you can
use the ``merge`` command to add them to the |policy|:

.. code-block:: console

    $ spyctl merge -f POLICY_FILE --latest > merged_policy.yaml

For example:

.. code-block:: console

    $ spyctl merge -f python_srv_policy.yaml --latest > python_srv_merged_policy.yaml

.. warning:: 
    Never redirect output to the same file you are using as input, the file will be wiped
    before spyctl can read it.

At this point you may want to edit the |policy| file to |generalize| any new fields. Repeat these
management steps until you're satisfied with your |policy| then |apply| it to make the
change to your Spyderbat Environment.

.. _Applying_A_Policy:

Applying a Policy
=================

To apply a |policy| you must use the ``apply`` command:

.. code-block:: console

    $ spyctl apply -f FILENAME

The apply command will recognize the ``kind`` of the file, perform validation, and attempt
to apply the resource to the Spyderbat Environment for the organization in your current |context|
(for |policies|) via the |api|.

For example, to apply the |policy| we created above:

.. code-block:: console

    $ spyctl apply -f python_srv_policy.yaml

This will apply the |policy| to the Spyderbat Environment for the organization in your current |context|.

.. warning:: 
    Policies are enabled by default, so they will start enforcing as soon as you apply them. This means
    that any |redflags| normally generated by a container or service will be excepted so long as they
    fall within the |policy|. An any deviations from the |policy| will generate a |policy| violation |redflag|
    and take response actions you have defined.

To view the applied |policies| for the organization in your current |context| you can use the ``get`` command:

.. code-block:: console

    $ spyctl get RESOURCE [OPTIONS] [NAME_OR_ID]

For example, to see the tabular summary of |policies| for the organization in your current |context|,
issue the command:

.. code-block:: console

    $ spyctl get policies
    UID                   NAME              STATUS     TYPE       CREATE_TIME
    CB1fSLq4wpkFG5kWsQ2r  webserver_policy  Enforcing  container  2023-01-06T22:54:28Z

To view the |policy| you just applied, issue the command:

.. code-block:: console

    $ spyctl get policies -o yaml CB1fSLq4wpkFG5kWsQ2r


The |policy| will look something like this:

.. code-block:: yaml

    apiVersion: spyderbat/v1
    kind: SpyderbatPolicy
    metadata:
      name: webserver_policy
      type: container
      uid: CB1fSLq4wpkFG5kWsQ2r
      creationTimestamp: 1673477668
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
      response:
        default:
          severity: high
        actions:
        - actionName: webhook
          url: https://hooks.slack.com/services/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s
          template: slack
          severity: medium

Disabling and Re-enabling a Policy
==================================

If you notice that a |policy| is too noisy, or you want to temporarily disable it, follow the
following steps:

1. Retrieve the |policy| via the |api| and save it to a file:

.. code-block:: console

    $ spyctl get policies -o yaml POLICY_UID > policy.yaml

For example:

.. code-block:: console

    $ spyctl get policies -o yaml CB1fSLq4wpkFG5kWsQ2r > python_srv_policy.yaml

2. Edit the file and add ``enabled: False`` to the ``spec``

.. code-block:: console

    $ vim python_srv_policy.yaml

.. code-block:: yaml

    enabled: False

In the ``spec`` it will look something like this:

.. code-block:: yaml

    ...
    spec:
      enabled: False
      containerSelector:
        image: "python_webserver:*"
    ...

3. ``apply`` the file you just edited

.. note:: 
    The ``uid`` field in the |policy|'s ``metadata`` indicates the target |policy| you wish
    to update.

.. code-block:: console

    $ spyctl apply -f python_srv_policy.yaml
    Successfully updated policy CB1fSLq4wpkFG5kWsQ2r

4. To see that the |policy| is indeed disabled, issue the command:

.. code-block:: console

    $ spyctl get policies CB1fSLq4wpkFG5kWsQ2r
    UID                   NAME              STATUS    TYPE       CREATE_TIME
    CB1fSLq4wpkFG5kWsQ2r  webserver_policy  Disabled  container  2023-01-06T22:54:28Z

To re-enable a |policy| you just can simply remove the ``enabled`` field in the ``spec`` or change
*False* to *True* and then ``apply`` the |policy| file again.

To see that the action was successful, issue the ``get`` command again:

.. code-block:: console

    $ spyctl get policies CB1fSLq4wpkFG5kWsQ2r
    UID                   NAME              STATUS      TYPE       CREATE_TIME
    CB1fSLq4wpkFG5kWsQ2r  webserver_policy  Enforcing   container  2023-01-06T22:54:28Z

Deleting a Policy
=================

If you wish to completely remove a |policy| from the Spyderbat Environment of the organization in your
current |context| you can use the ``delete`` command:

.. code-block:: console

    $ spyctl delete RESOURCE [OPTIONS] NAME_OR_ID

For example:

.. code-block:: console

    $ spyctl delete policy CB1fSLq4wpkFG5kWsQ2r
    Successfully deleted policy CB1fSLq4wpkFG5kWsQ2r

What's Next
===========

* :ref:`Commands<Commands>`
* :ref:`Spyderbat Concepts<Spyderbat_Concepts>`

.. |api| replace:: :ref:`Spyderbat API<Spyderbat_API>`
.. |action| replace:: :ref:`Action<Response_Actions>`
.. |actions| replace:: :ref:`Actions<Response_Actions>`
.. |applied| replace:: :ref:`applied<Applying_A_Policy>`
.. |apply| replace:: :ref:`apply<Applying_A_Policy>`
.. |console| replace:: :ref:`Spyderbat Console<Spyderbat_Console>`
.. |context| replace:: :ref:`Context<Contexts>`
.. |contexts| replace:: :ref:`Contexts<Contexts>`
.. |baselines| replace:: :ref:`Baselines<Baselines>`
.. |baseline| replace:: :ref:`Baseline<Baselines>`
.. |fprints| replace:: :ref:`Fingerprints<Fingerprints>`
.. |fprint| replace:: :ref:`Fingerprint<Fingerprints>`
.. |fprint_grp| replace:: :ref:`Fingerprint Group<Fingerprint_Groups>`
.. |fprint_grps| replace:: :ref:`Fingerprint Groups<Fingerprint_Groups>`
.. |generalize| replace:: :ref:`generalize<Generalizing_A_Baseline>`
.. |mach| replace:: :ref:`Machine<Machines>`
.. |machs| replace:: :ref:`Machines<Machines>`
.. |na| replace:: :ref:`Nano Agent<Nano_Agent>`
.. |policies| replace:: :ref:`Policies<Policies>`
.. |policy| replace:: :ref:`Policy<Policies>`
.. |redflag| replace:: :ref:`Redflag<Redflags>`
.. |redflags| replace:: :ref:`Redflags<Redflags>`
.. |resource| replace:: :ref:`Resource<Resources>`
.. |resources| replace:: :ref:`Resources<Resources>`
.. |responses| replace:: :ref:`Response Actions<Response_Actions>`
.. |secret| replace:: :ref:`APISecret<Secrets>`
.. |secrets| replace:: :ref:`APISecrets<Secrets>`

.. |s_na| replace:: :ref:`Spyderbat Nano Agent<Nano_Agent>`
.. |s_baselines| replace:: :ref:`Spyderbat Baselines<Baselines>`
.. |s_baseline| replace:: :ref:`Spyderbat Baseline<Baselines>`
.. |s_fprints| replace:: :ref:`Spyderbat Fingerprints<Fingerprints>`
.. |s_fprint| replace:: :ref:`Spyderbat Fingerprint<Fingerprints>`
.. |s_policies| replace:: :ref:`Spyderbat Policies<Policies>`
.. |s_policy| replace:: :ref:`Spyderbat Policy<Policies>`
