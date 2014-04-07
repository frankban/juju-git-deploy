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

"""Juju Git Deploy API management."""

from contextlib import contextmanager
import itertools
import json
import logging

import websocket

from . import utils


# Define the user name used for authenticating to the Juju API.
JUJU_USER = 'user-admin'


def get_api_address(env_name):
    """Return the environment API address.

    Raise a ValueError if the API address cannot be retrieved.
    """
    retcode, output, error = utils.call(
        'juju', 'api-endpoints', '-e', env_name, '--format', 'json')
    if retcode:
        raise ValueError(error)
    addresses = json.loads(output)
    if not addresses:
        raise ValueError('unable to find a usable Juju API address')
    return addresses[0]


def upload_charm(api_address, stream, password, series):
    """Upload a local charm to the given Juju API address.

    Receive the file-like object stream representing the zip contents of the
    charm. Authenticate with the given password and use the given OS series
    to store the local charm.

    Raise an IOError if an error occurs while uploading the charm.

    To upload a local charm to the Juju HTTP API, a POST request must be sent
    to https://<juju API address>/charms?series=<char series>.
    Headers must include at least an "application/zip" content type, and the
    HTTP basic auth credentials.
    The request body is the charm zipped content.
    The Juju response is a JSON message containing either a "CharmURL" key
    with the resulting local charm URL if the request was successful, or an
    "Error" key if an error occurred processing the request.
    """
    host, port = api_address.split(':')
    path = '/charms?series={}'.format(series)
    data, status, reason = utils.urlpost(
        host, port, path, stream, JUJU_USER, password)
    try:
        contents = json.loads(data)
    except Exception as err:
        raise IOError('{} ({}): {}'.format(reason, status, err))
    if status != 200:
        raise IOError('{} ({}): {}'.format(reason, status, contents['Error']))
    return contents['CharmURL']


class JujuError(Exception):
    """An error occurred while using the Juju WebSocket client."""


class JujuWebSocketConnection:
    """A simple Juju WebSocket client."""

    def __init__(self, ws_address):
        self.ws_address = ws_address
        self._connection = None
        self._counter = itertools.count()

    def connect(self):
        """Connect to the Juju WebSocket API."""
        self._connection = websocket.create_connection(self.ws_address)

    def send(self, request):
        """Send a request to Juju."""
        connection = self._connection
        request['RequestId'] = next(self._counter)
        outgoing = json.dumps(request)
        logging.debug('ws -> {}'.format(outgoing))
        try:
            connection.send(outgoing)
            incoming = connection.recv()
        except Exception as err:
            msg = 'error processing the Juju API {}:{} request: {}'.format(
                request['Type'], request['Request'], err)
            raise JujuError(msg)
        logging.debug('ws <- {}'.format(incoming))
        return json.loads(incoming)

    def close(self):
        """Close the WebSocket connection."""
        try:
            self._connection.close()
        except Exception:
            pass
        self._connection = None


@contextmanager
def connect(api_address):
    """Connect to the Juju WebSocket API using the Client above.

    The resulting connection is made available in the context block.

    Raise a JujuError if the connection cannot be established.
    """
    ws_address = 'wss://{}'.format(api_address)
    connection = JujuWebSocketConnection(ws_address)
    # Connect to the Juju WebSocket API.
    try:
        connection.connect()
    except Exception as err:
        msg = 'unable to connect to {}: {}'.format(ws_address, err)
        raise JujuError(msg)
    try:
        yield connection
    finally:
        connection.close()


def _check_reponse(response, message):
    """Check if the given response is an API error.

    If so, raise a JujuError with the given error message.
    """
    error = response.get('Error')
    if error:
        raise JujuError(message.format(error))


def login(connection, password):
    """Log in into the Juju WebSocket API."""
    request = {
        'Type': 'Admin',
        'Request': 'Login',
        'Params': {'AuthTag': JUJU_USER, 'Password': password},
    }
    response = connection.send(request)
    _check_reponse(response, 'error authenticating to Juju: {}')


def deploy(connection, charm_url, service=None, num_units=None, machine=None):
    """Deploy a charm using the Juju WebSocket API.

    Return the deployed service name.
    """
    if service is None:
        service = utils.get_service_from_charm(charm_url)
    if num_units is None:
        num_units = 1
    request = {
        'Type': 'Client',
        'Request': 'ServiceDeploy',
        'Params': {
            'CharmURL': charm_url,
            'ServiceName': service,
            'NumUnits': num_units,
            'Config': {},
            'Constraints': {},
            'ToMachineSpec': machine,
        }
    }
    response = connection.send(request)
    _check_reponse(response, 'error deploying the charm: {}')
    return service
