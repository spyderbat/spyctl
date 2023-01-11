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
way to tune out known |redflags| and also to generate new |redflags| if a |policy| is violated. enforces the
``spec`` found in the baseline.

.. |context| replace:: :ref:`Context<Contexts>`
.. |contexts| replace:: :ref:`Contexts<Contexts>`
.. |baselines| replace:: ``Baselines``
.. |baseline| replace:: ``Baseline``
.. |fprints| replace:: :ref:`Fingerprints<Fingerprints>`
.. |fprint| replace:: :ref:`Fingerprint<Fingerprints>`
.. |fprint_grp| replace:: :ref:`Fingerprint Group<Fingerprint_Groups>`
.. |fprint_grps| replace:: :ref:`Fingerprint Groups<Fingerprint_Groups>`
.. |mach| replace:: :ref:`Machine<Machines>`
.. |machs| replace:: :ref:`Machines<Machines>`
.. |na| replace:: ``Nano Agent``
.. |policies| replace:: :ref:`Policies<Policies>`
.. |policy| replace:: :ref:`Policy<Policies>`
.. |redflags| replace:: :ref:`Redflags<Redflags>`
.. |resource| replace:: :ref:`Resource<Resources>`
.. |resources| replace:: :ref:`Resources<Resources>`
.. |spyctl| replace:: ``Spyctl``
.. |secret| replace:: :ref:`Secret<Secrets>`

.. |s_na| replace:: ``Spyderbat Nano Agent``
.. |s_baselines| replace:: ``Spyderbat Baselines``
.. |s_baseline| replace:: ``Spyderbat Baseline``
.. |s_fprints| replace:: :ref:`Spyderbat Fingerprints<Fingerprints>`
.. |s_fprint| replace:: :ref:`Spyderbat Fingerprint<Fingerprints>`
.. |s_policies| replace:: :ref:`Spyderbat Policies<Policies>`
.. |s_policy| replace:: :ref:`Spyderbat Policy<Policies>`
