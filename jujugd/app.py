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

"""Juju Git Deploy base application function."""

import re

from . import (
    api,
    env,
    utils,
)


GITHUB_API = 'https://api.github.com/repos'

# Compile the regular expression used to parse the Github repository URL.
_repo_expression = re.compile(r"""
    ^(?:https://)?  # Optional schema.
    (?:github.com/)?  # Optional Domain.
    ([-\w]+)/  # User name.
    ([-\w]+)  # Repository name.
    /?  # Optional trailing slash.
    (?::([-\w]+))?$  # Optional branch/reference name.
""", re.VERBOSE)


class ProgramExit(Exception):
    """An error occurred in the application.

    Raise this exception if you want the program to exit gracefully printing
    the error message to stderr.
    """

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return 'juju-git-deploy: error: {}'.format(self.message)


def prepare(repo, env_name, series):
    """Prepare the Juju environment.

    Return the Github zip URL, the Juju API address and password.
    """
    # Retrieve the Juju API address, password and, if required, OS series.
    try:
        api_address = api.get_api_address(env_name)
        password = env.parse_jenv(env_name, env.get_password)
        if series is None:
            series = env.parse_jenv(env_name, env.get_default_series)
    except ValueError as err:
        raise ProgramExit(str(err))
    # Generate the Github zip URL.
    match = _repo_expression.match(repo)
    if match is None:
        raise ProgramExit('invalid repository: {}'.format(repo))
    user, repo_name, branch = match.groups()
    if branch is None:
        branch = ''
    zip_url = '{}/{}/{}/zipball/{}'.format(GITHUB_API, user, repo_name, branch)
    return zip_url, api_address, password, series


def process(zip_url, api_address, password, series):
    """Upload the charm represented by the given zip URL and OS series.

    If series is None, use the default Juju environment series.

    Use the given API address and password to upload the charm to Juju.
    Return the resulting charm URL
    """
    print('connecting to github')
    try:
        response = utils.urlget(zip_url)
    except IOError as err:
        msg = 'unable to retrieve charm contents: {}'.format(err)
        raise ProgramExit(msg)
    print('uploading charm')
    try:
        charm_url = api.upload_charm(api_address, response, password, series)
    except IOError as err:
        msg = 'charm upload failed: {}'.format(err)
        raise ProgramExit(msg)
    return charm_url


def deploy(charm_url, service, num_units, machine, api_address, password):
    """Deploy a charm using the Juju API."""
    print('deploying {}'.format(charm_url))
    try:
        with api.connect(api_address) as connection:
            api.login(connection, password)
            deployed_service = api.deploy(
                connection, charm_url, service=service, num_units=num_units,
                machine=machine)
    except api.JujuError as err:
        msg = 'API failure: {}'.format(err)
        raise ProgramExit(msg)
    print('deployed as service {}'.format(deployed_service))
