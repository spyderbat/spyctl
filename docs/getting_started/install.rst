.. _install:

======================
Installation of Spyctl
======================

This part of the documentation covers the installation of Spyctl.
The first step to using any software package is getting it properly installed.

Prerequisites
=============

* Python 3.7 or newer

$ python -m pip install spyctl
==============================

To install Spyctl, simply run this command in your terminal of choice

.. code-block:: console

    $ python -m pip install spyctl

To verify the installation:

.. code-block:: console

    $ spyctl --version

Enabling Shell Completion
=========================

.. note:: 
    Spyctl currently supports shell completion for ``Bash``

To enable shell completion, follow these steps:

1. Create the Spyctl directory if you haven't already

.. code-block:: console

    $ mkdir -p ~/.spyctl

2. generate the shell completion script

.. code-block:: console

    $ _SPYCTL_COMPLETE=bash_source spyctl > ~/.spyctl/.spyctl-complete.bash

3. Add the following line to ~/.bashrc

.. code-block:: none

    . ~/.spyctl/.spyctl-complete.bash

.. code-block:: console

    $ vim ~/.bashrc

What's Next
-----------

.. toctree::
   :maxdepth: 1

   /tutorials/spyctl_basics