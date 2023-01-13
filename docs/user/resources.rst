.. _Resources:

===================
Spyderbat Resources
===================

.. _Clusters:

Clusters
========

.. _Fingerprints:

Spyderbat Fingerprints
======================

*a.k.a. Fingerprints*

.. _Fingerprint_Groups:

Fingerprint Groups
==================

.. _Machines:

Machines
========

.. _Namespaces:

Namespaces
==========

.. _Pods:

Pods
====

.. _Policies:

Spyderbat Policies
==================

*a.k.a. Policies*

.. _Baselines:

Spyderbat Baselines
-------------------

*a.k.a. Baselines*

The step before creating a Policy. Baselines are used to visualize your service and container activity
without fear of making any changes to your spyderbat environment. In other words, baselines do not tune out
redflags, generate new flags, nor take response actions. Policies can be created from baselines, with the only
major difference being the addition of a ``response`` field to the ``spec``.

.. _Response_Actions:

Response Actions
----------------

When something violates a Policy, custom response actions are evaluated and taken so long as the
violation matches any defined Selectors. If no custom actions exist or none are taken, the default
response action is taken.