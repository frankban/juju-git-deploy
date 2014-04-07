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

"""Tests for the Juju Git Deploy API management."""

import json
from unittest import (
    mock,
    TestCase,
)

from . import helpers
from .. import api


class TestGetApiAddress(helpers.ErrorTestsMixin, TestCase):

    def test_address_retrieved(self):
        # The first API address is returned.
        addresses = json.dumps(['10.0.1.42:17070', '10.0.1.47:17077'])
        with helpers.patch_call(0, output=addresses) as mock_call:
            address = api.get_api_address('ec2')
        self.assertEqual('10.0.1.42:17070', address)
        mock_call.assert_called_once_with(
            'juju', 'api-endpoints', '-e', 'ec2', '--format', 'json')

    def test_juju_error(self):
        # A ValueError is raised if the call to "juju api-endpoints" exits
        # with an error.
        with helpers.patch_call(1, error='bad wolf'):
            with self.assert_error(ValueError, 'bad wolf'):
                api.get_api_address('ec2')

    def test_no_addresses(self):
        # A ValueError is raised if no API addresses are found.
        expected_error = 'unable to find a usable Juju API address'
        with helpers.patch_call(0, output=json.dumps([])):
            with self.assert_error(ValueError, expected_error):
                api.get_api_address('ec2')


class TestUploadCharm(helpers.ErrorTestsMixin, TestCase):

    def setUp(self):
        # Set up a file-like request object.
        self.stream = helpers.make_stream('charm zip contents')

    def test_upload_success(self):
        # The newly uploaded charm URL is returned if the upload succeeds.
        contents = json.dumps({'CharmURL': 'local:django-42'})
        with helpers.patch_connection(contents=contents) as mock_conn:
            charm_url = api.upload_charm(
                '10.0.3.1:17070', self.stream, 'secret!', 'trusty')
        self.assertEqual('local:django-42', charm_url)
        mock_conn.assert_called_once_with('10.0.3.1', '17070')
        expected_headers = {
            'Content-Type': 'application/zip',
            'Authorization': 'Basic dXNlci1hZG1pbjpzZWNyZXQh',
        }
        mock_conn().request.assert_called_once_with(
            'POST', '/charms?series=trusty', 'charm zip contents',
            expected_headers)

    def test_response_data_error(self):
        # An IOError is raised if the Juju API server response contains
        # invalid data.
        expected_error = 'OK (200): No JSON object could be decoded'
        with helpers.patch_connection(contents='invalid_data'):
            with self.assert_error(IOError, expected_error):
                api.upload_charm(
                    '10.0.3.1:17070', self.stream, 'secret!', 'trusty')

    def test_response_status_error(self):
        # An IOError is raised if the Juju API server returns an invalid
        # response.
        contents = json.dumps({'Error': 'bad wolf'})
        expected_error = 'bad request (400): bad wolf'
        with helpers.patch_connection(
                contents=contents, status=400, reason='bad request'):
            with self.assert_error(IOError, expected_error):
                api.upload_charm(
                    '10.0.3.1:17070', self.stream, 'secret!', 'trusty')


class TestJujuWebSocketConnection(helpers.ErrorTestsMixin, TestCase):

    ws_address = 'wss://10.0.3.1:17070'

    def setUp(self):
        # Set up the WebSocket connection.
        self.connection = api.JujuWebSocketConnection(self.ws_address)
        create_connection_path = 'websocket.create_connection'
        with mock.patch(create_connection_path) as mock_create_connection:
            self.connection.connect()
        self.mock_create_connection = mock_create_connection

    def test_connect(self):
        # The WebSocket connection is correctly established.
        self.mock_create_connection.assert_called_once_with(self.ws_address)

    def test_send_success(self):
        # A message is properly send as a JSON encoded string.
        ws_connection = self.mock_create_connection()
        response = {'Response': 'test'}
        ws_connection.recv.return_value = json.dumps(response)
        obtained_response = self.connection.send({'Type': 'test'})
        self.assertEqual(response, obtained_response)
        ws_connection.send.assert_called_once_with(
            json.dumps({'RequestId': 0, 'Type': 'test'}))
        ws_connection.recv.assert_called_once_with()

    def test_send_error(self):
        # A JujuError is raised if an error occurs while communicating with
        # the Juju WebSocket API.
        ws_connection = self.mock_create_connection()
        ws_connection.send.side_effect = TypeError('bad wolf')
        expected = 'error processing the Juju API test:error request: bad wolf'
        with self.assert_error(api.JujuError, expected):
            self.connection.send({'Type': 'test', 'Request': 'error'})

    def test_close(self):
        # The connection is properly closed.
        ws_connection = self.mock_create_connection()
        self.connection.close()
        ws_connection.close.assert_called_once_with()

    def test_close_errors(self):
        # Connection errors at closing time are ignored.
        ws_connection = self.mock_create_connection()
        ws_connection.close.side_effect = TypeError('bad wolf')
        self.connection.close()

    def test_incremental_request_id(self):
        # The request identifier is incremented on each request.
        ws_connection = self.mock_create_connection()
        ws_connection.recv.return_value = json.dumps({'Response': 'test'})
        self.connection.send({'Type': 'test1'})
        self.connection.send({'Type': 'test2'})
        self.assertEqual(2, ws_connection.send.call_count)
        ws_connection.send.assert_has_calls([
            mock.call(json.dumps({'RequestId': 0, 'Type': 'test1'})),
            mock.call(json.dumps({'RequestId': 1, 'Type': 'test2'})),
        ])


@mock.patch('jujugd.api.JujuWebSocketConnection')
class TestConnect(helpers.ErrorTestsMixin, TestCase):

    def test_connection_established(self, mock_connection):
        # The connection is properly established and closed.
        with api.connect('10.0.3.1:17070') as connection:
            connection.connect.assert_called_once_with()
        mock_connection.assert_called_once_with('wss://10.0.3.1:17070')

    def test_connection_error(self, mock_connection):
        # A JujuError is raised if the connection cannot be established.
        mock_connection().connect.side_effect = TypeError('bad wolf')
        expected_error = 'unable to connect to wss://10.0.3.1:17070: bad wolf'
        with self.assert_error(api.JujuError, expected_error):
            with api.connect('10.0.3.1:17070'):
                pass

    def test_connection_closed(self, mock_connection):
        # The connection is closed even if an exception is raised in the
        # context block.
        with api.connect('10.0.3.1:17070') as connection:
            pass
        connection.close.assert_called_once_with()


def make_connection(response):
    """Create and return a mock WebSocket connection returning response."""
    mock_send = mock.Mock(return_value=response)
    return mock.Mock(send=mock_send)


class TestLogin(helpers.ErrorTestsMixin, TestCase):

    def test_login_message(self):
        # The Admin:Login message is sent to the Juju WebSocket API.
        connection = make_connection({})
        api.login(connection, 'secret!')
        connection.send.assert_called_once_with({
            'Type': 'Admin',
            'Request': 'Login',
            'Params': {'AuthTag': 'user-admin', 'Password': 'secret!'},
        })

    def test_login_error(self):
        # A JujuError is raised if the response from Juju includes an error.
        connection = make_connection({'Error': 'bad wolf'})
        expected_error = 'error authenticating to Juju: bad wolf'
        with self.assert_error(api.JujuError, expected_error):
            api.login(connection, 'secret!')


class TestDeploy(helpers.ErrorTestsMixin, TestCase):

    def test_deploy_message(self):
        # The Client:ServiceDeploy message is sent to the Juju WebSocket API.
        connection = make_connection({})
        api.deploy(
            connection, 'local:trusty/django-42',
            service='django-project', num_units=47)
        connection.send.assert_called_once_with({
            'Type': 'Client',
            'Request': 'ServiceDeploy',
            'Params':  {
                'CharmURL': 'local:trusty/django-42',
                'ServiceName': 'django-project',
                'NumUnits': 47,
                'Config': {},
                'Constraints': {},
                'ToMachineSpec': None,
            },
        })

    def test_service_name(self):
        # The service name is correctly generated and returned.
        connection = make_connection({})
        service = api.deploy(
            connection, 'local:precise/juju-gui-42', machine='0')
        self.assertEqual('juju-gui', service)
        connection.send.assert_called_once_with({
            'Type': 'Client',
            'Request': 'ServiceDeploy',
            'Params':  {
                'CharmURL': 'local:precise/juju-gui-42',
                'ServiceName': 'juju-gui',
                'NumUnits': 1,
                'Config': {},
                'Constraints': {},
                'ToMachineSpec': '0',
            },
        })

    def test_deploy_error(self):
        # A JujuError is raised if the response from Juju includes an error.
        connection = make_connection({'Error': 'bad wolf'})
        expected_error = 'error deploying the charm: bad wolf'
        with self.assert_error(api.JujuError, expected_error):
            api.deploy(connection, 'local:trusty/django-42')
