.. _Spyderbat_Concepts:

==================
Spyderbat Concepts
==================

This page has definitions and details relating to various Spyderbat-specific concepts

.. _Opsflags:

Opsflag
========

.. _Redflags:

Redflag
========

Redflags are indicators of security-related activity. They range in severity from "info" to "critical".
In isolation, redflags are generally not a direct indicator of a threat, however if a number of flags
are causally grouped together in a high-scoring |trace|, they are more likely to indicate a threat.

.. _Redflag_Severities:

Severities
----------

The severity labels that can be applied to a redflag are listed here in increasing severity:

* info
* low
* medium
* high
* critical

.. _Selectors:

Selectors
=========

containerSelector
-----------------

machineSelector
---------------

namespaceSelector
-----------------

podSelector
-----------

serviceSelector
---------------

.. _Spydertrace:

Spydertrace
===========

*a.k.a. Trace*

.. _sba:

Spyderbat Analytics Engine
==========================

*a.k.a SBA*

.. _Spyderbat_API:

Spyderbat API
=============

.. _Spyderbat_Console:

Spyderbat Console
=================

.. _Nano_Agent:

Spyderbat Nano Agent
====================

*a.k.a. Nano Agent*

.. |trace| replace:: :ref:`Spydertrace<Spydertrace>`