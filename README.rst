Juju Git Deploy
===============

Juju Git Deploy is a Juju plugin which allows for easily deploying services
from local charms hosted on Github.
More information about Juju cloud orchestration tool can be found at
https://juju.ubuntu.com/.

This plugin is mostly intended as a development tool, and can be useful for
testing charms which code base lives in Github. For a more comprehensive and
effective experience, take a look at the `Juju GUI`_, which allows managing
Juju environments via a user-friendly Web interface, and supports deploying
local charms by dragging and dropping zip archives.

Also see `Juju Quickstart`_: it is an easy to set up tool that quickly starts
Juju and the GUI, whether you've never installed Juju or you have an existing
Juju environment running.

.. _`Juju GUI`: https://juju.ubuntu.com/resources/juju-gui/
.. _`Juju Quickstart`: https://pypi.python.org/pypi/juju-quickstart/

Requirements
------------

Juju Git Deploy requires Python >= 3.3 and Juju >= 1.17.7.

Python requirements are listed on the ``requirements.pip`` file.

This applications does not require git itself to be installed.

Installation
------------

This plugin is registered on PyPI::

    sudo pip3 install juju-git-deploy

Getting started
---------------

Bootstrap your Juju environment::

    juju bootstrap

Deploy a charm from Github::

    juju git-deploy github.com/hatched/ghost-charm

Done!

The charm above can be deployed also copy/pasting the URL, e.g.::

    juju git-deploy https://github.com/hatched/ghost-charm

Otherwise, it is possible to use the simplified ``{user}/{repo}`` form::

    juju git-deploy hatched/ghost-charm

At this point, the ``juju status`` command shows that a service is being
deployed using the specified local charm.

Deploying a specific git branch
-------------------------------

To deploy a specific git branch or reference, append a colon followed by
the reference identifier, e.g.::

    juju git-deploy frankban/ghost-charm:develop
    juju git-deploy https://github.com/frankban/ghost-charm:develop

If the reference is not specified, the repository's default branch is used
(usually ``master``).

Charm series
------------

To deploy the charm on a specific OS series, provide the ``--series``
(or ``-s``) argument, e.g.::

    juju git-deploy hatched/ghost-charm -s trusty

If ``--series`` is not specified the default environment series is used.

Service name
------------

The service name can be provided as second positional argument::

    juju git-deploy hatched/ghost-charm:develop ghost-develop

If omitted, the service name is derived from the charm name.

Additional options
------------------

Other options include ``-e`` to select the Juju environment, ``--to`` and
``--num-units``. See the plugin help by running::

    juju help git-deploy

TODO
----

Support ``--constraints``.
