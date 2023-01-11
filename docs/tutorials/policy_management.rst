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
Policies have four fields, ``apiVersion``, ``kind``, ``metadata`` and ``spec``. 

Policies
can also be used to take |responses|, such as killing a process, or sending a webhook notification.

The main difference between a |s_policy| and a |s_baseline| is the inclusion of the ``response`` sections
within the ``spec``. 

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
.. |redflags| replace:: :ref:`Redflags<Redflags>`
.. |resource| replace:: :ref:`Resource<Resources>`
.. |resources| replace:: :ref:`Resources<Resources>`
.. |responses| replace:: :ref:`Response Actions<Response_Actions>`
.. |secret| replace:: :ref:`Secret<Secrets>`

.. |s_na| replace:: :ref:`Spyderbat Nano Agent<Nano_Agent>`
.. |s_baselines| replace:: :ref:`Spyderbat Baselines<Baselines>`
.. |s_baseline| replace:: :ref:`Spyderbat Baseline<Baselines>`
.. |s_fprints| replace:: :ref:`Spyderbat Fingerprints<Fingerprints>`
.. |s_fprint| replace:: :ref:`Spyderbat Fingerprint<Fingerprints>`
.. |s_policies| replace:: :ref:`Spyderbat Policies<Policies>`
.. |s_policy| replace:: :ref:`Spyderbat Policy<Policies>`
