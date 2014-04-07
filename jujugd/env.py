# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License version 3, as published by
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranties of MERCHANTABILITY,
# SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Juju Git Deploy interaction with the Juju environment."""

import collections
import os

import yaml

from . import utils


def get_default_env_name():
    """Return the current Juju environment name.

    The environment name can be set either by
        - setting the JUJU_ENV environment variable;
        - using "juju switch my-env-name";
        - setting the default environment in the environments.yaml file.
    The former overrides the latter.

    Return None if a default environment is not found.
    """
    env_name = os.getenv('JUJU_ENV', '').strip()
    if env_name:
        return env_name
    retcode, output, _ = utils.call('juju', 'switch')
    if retcode:
        return None
    return output.strip()


def parse_jenv(env_name, parser):
    """Parse the jenv file corresponding to the given environment name.

    Call the given parser with the jenv file YAML decoded bootstrap options.
    Return what is returned by the parser callable.

    Raise a ValueError if the jenv file is not parsable.
    """
    juju_home = os.path.expanduser('~/.juju')
    jenv = os.path.join(juju_home, 'environments', '{}.jenv'.format(env_name))
    try:
        with open(jenv) as stream:
            contents = yaml.safe_load(stream)
    except Exception as err:
        raise ValueError(str(err))
    config = contents.get('bootstrap-config', {})
    if isinstance(config, collections.Mapping):
        return parser(config)
    raise ValueError('invalid configuration file: {}'.format(jenv))


def get_password(config):
    """Return the Juju environment password (admin-secret).

    Receive the jenv file YAML decoded bootstrap configuration.
    Raise a ValueError is the password cannot be found.
    """
    password = config.get('admin-secret')
    if not password:
        raise ValueError('unable to find the environment password')
    return password


def get_default_series(config):
    """Return the Juju environment default series.

    Receive the jenv file YAML decoded bootstrap configuration.
    Raise a ValueError is the OS series cannot be found.
    """
    return config.get('default-series', '')


def get_bootstrap_node_series(env_name):
    """Return the bootstrap node series parsing the output of "juju status".

    Raise a ValueError if "juju status" exits with an error.
    """
    retcode, output, error = utils.call(
        'juju', 'status', '-e', env_name, '--format', 'yaml')
    if retcode:
        msg = 'unable to retrieve the bootstrap node series: {}'.format(error)
        raise ValueError(msg)
    contents = yaml.safe_load(output)
    return contents['machines']['0']['series']
