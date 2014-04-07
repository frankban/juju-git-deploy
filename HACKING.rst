Juju Git Deploy
===============

Juju Git Deploy allows for easily deploying services from local charms hosted
on Github.

Creating a development environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The development environment is created in a virtualenv. The environment
creation requires the *make*, *pip* and *virtualenv* programs to be installed.
To do that, run the following::

    $ make sysdeps

At this point, from the root of this branch, run the command::

    $ make

This command will create a ``.venv`` directory in the branch root, ignored
by DVCSes, containing the development virtual environment with all the
dependencies.

Testing and debugging the application
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run the tests::

    $ make test

Run the tests and lint/pep8 checks::

    $ make check

Display help about all the available make targets, including instructions on
setting up and running the application in the development environment::

    $ make help

Installing the application
~~~~~~~~~~~~~~~~~~~~~~~~~~

To install Juju Git Deploy in your local system, run the following::

    $ sudo make install

This command will take care of installing the requirements and the application
itself.

Running the application
~~~~~~~~~~~~~~~~~~~~~~~

juju-core will recognize Juju Git Deploy as a plugin once the application is
installed by the command above. At this point, the application can be started
by running ``juju git-deploy {GIT BRANCH URL}``.

Run the following for the list of all available options::

    $ juju git-deploy --help

If you have not installed the application using ``sudo make install``, as
described above, you can run it locally using the virtualenv's Python
installation::

    $ .venv/bin/python juju-git-deploy --help

Creating PyPI releases
~~~~~~~~~~~~~~~~~~~~~~

Juju Git Deploy is present on PyPI: see
<https://pypi.python.org/pypi/juju-git-deploy>.
It is possible to register and upload a new release on PyPI by just running
``make release`` and providing your PyPI credentials.
