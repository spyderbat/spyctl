.. _install:

======================
Installation of Spyctl
======================

This part of the documentation covers the installation of Spyctl.
The first step to using any software package is getting it properly installed.

Prerequisites
=============

* Python 3.7 or newer

$ pip install spyctl
==============================

To install Spyctl, simply run this command in your terminal of choice

.. code-block:: console

    $ pip install spyctl

To verify the installation:

.. code-block:: console

    $ spyctl --version

Enabling Shell Completion
=========================

To enable shell completion, follow these steps:

.. tabs::

    .. group-tab:: Bash

        .. note::
            The default version of Bash for Mac OS X users does not support programmable shell completion.
            Guides like `this <https://kizu514.com/blog/install-upgraded-gnu-bash-on-a-macbook-pro/>`_ will help
            you install a newer version of Bash.

        Create the Spyctl directory if you haven't already.

        .. code-block:: bash

            $ mkdir -p ~/.spyctl

        Generate the shell completion script.

        .. code-block:: bash

            $ _SPYCTL_COMPLETE=bash_source spyctl > ~/.spyctl/.spyctl-complete.bash

        Source the file in ``~/.bashrc``. Add the following line to the end of ``~/.bashrc``.

        .. code-block:: console

            . ~/.spyctl/spyctl-complete.bash
    
    .. group-tab:: Fish
        
        Generate and save the shell completion script.

        .. code-block:: fish

            $ _SPYCTL_COMPLETE=fish_source spyctl > ~/.config/fish/completions/spyctl-complete.fish
    
    .. group-tab:: Zsh

        Create the Spyctl directory if you haven't already.
        
        .. code-block:: zsh
            
            $ mkdir -p ~/.spyctl

        Generate the shell completion script.

        .. code-block:: zsh

            $ _SPYCTL_COMPLETE=zsh_source spyctl > ~/.spyctl/spyctl-complete.zsh

        Source the file in ``~/.zshrc``. Add the following line to the end of ``~/.zshrc``.

        .. code-block:: console

            . ~/.spyctl/spyctl-complete.zsh

After modifying the shell config, you need to start a new shell in order for the changes to be loaded.

What's Next
-----------

.. toctree::
   :maxdepth: 1

   /tutorials/spyctl_basics