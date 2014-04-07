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

"""Tests for the Juju Git Deploy utility functions and classes."""

from unittest import TestCase

from . import helpers
from .. import utils


class TestCall(TestCase):

    def test_success(self):
        # A zero exit code and the subprocess output are correctly returned.
        retcode, output, error = utils.call('echo')
        self.assertEqual(0, retcode)
        self.assertEqual('\n', output)
        self.assertEqual('', error)

    def test_multiple_arguments(self):
        # A zero exit code and the subprocess output are correctly returned
        # when executing a command passing multiple arguments.
        retcode, output, error = utils.call('echo', 'we are the borg!')
        self.assertEqual(0, retcode)
        self.assertEqual('we are the borg!\n', output)
        self.assertEqual('', error)

    def test_failure(self):
        # An error code and the error are returned if the subprocess fails.
        retcode, output, error = utils.call('ls', 'no-such-file')
        self.assertNotEqual(0, retcode)
        self.assertEqual('', output)
        self.assertEqual(
            'ls: cannot access no-such-file: No such file or directory\n',
            error)

    def test_invalid_command(self):
        # An error code and the error are returned if the subprocess fails to
        # find the provided command in the PATH.
        retcode, output, error = utils.call('no-such-command')
        self.assertEqual(127, retcode)
        self.assertEqual('', output)
        self.assertIn(
            'no-such-command: [Errno 2] No such file or directory', error)


class TestGetServiceFromCharm(TestCase):

    def test_simple_service_name(self):
        # A service name is properly returned given a charm.
        service = utils.get_service_from_charm('cs:precise/django-42')
        self.assertEqual('django', service)

    def test_complex_service_name(self):
        # The correct service is properly retrieved even if the charm name
        # include multiple dashes.
        service = utils.get_service_from_charm('local:trusty/juju-gui-142')
        self.assertEqual('juju-gui', service)


class TestUrlget(helpers.ErrorTestsMixin, TestCase):

    def test_successful_response(self):
        # A remote response is correctly returned.
        with helpers.patch_urlopen(contents='exterminate') as mock_urlopen:
            response = utils.urlget('https://example.com')
        mock_urlopen.assert_called_once_with('https://example.com')
        self.assertEqual('exterminate', response.read())
        self.assertEqual(200, response.status)
        self.assertEqual('OK', response.reason)

    def test_url_error(self):
        # An IOError is raised if the given URL is not reachable.
        with helpers.patch_urlopen(error='bad wolf'):
            with self.assert_error(IOError, 'bad wolf'):
                utils.urlget('https://example.com')

    def test_response_error(self):
        # An IOError is raised if the response is not ok.
        expected = 'invalid response from https://example.com (404): not found'
        with helpers.patch_urlopen(status=404, reason='not found'):
            with self.assert_error(IOError, expected):
                utils.urlget('https://example.com')


class TestUrlpost(TestCase):

    host = 'example.com'
    port = 17070
    path = '/voyages/'
    user = 'jean luc'
    password = 'secret!'

    def test_length_known(self):
        # The stream is properly sent if the content length is retrievable.
        stream = helpers.make_stream('request contents', 42)
        with helpers.patch_connection(
                contents='response contents') as mock_connection:
            data, status, reason = utils.urlpost(
                self.host, self.port, self.path, stream,
                self.user, self.password)
        self.assertEqual('response contents', data)
        self.assertEqual(200, status)
        self.assertEqual('OK', reason)
        # The connection is first instantiated.
        mock_connection.assert_called_once_with(self.host, self.port)
        mock_instance = mock_connection()
        # Then the remote request is performed passing the file-like stream.
        expected_headers = {
            'Content-Type': 'application/zip',
            'Authorization': 'Basic amVhbiBsdWM6c2VjcmV0IQ==',
            'Content-Length': 42,
        }
        mock_instance.request.assert_called_once_with(
            'POST', self.path, stream, expected_headers)
        # The response is retrieved.
        mock_instance.getresponse.assert_called_once_with()
        # Finally the connection is closed.
        mock_instance.close.assert_called_once_with()

    def test_length_unknown(self):
        # The stream contents are retrieved and properly sent if the content
        # length is unavailable.
        stream = helpers.make_stream('request contents')
        with helpers.patch_connection(
                contents='response contents',
                status=500, reason='internal error') as mock_connection:
            data, status, reason = utils.urlpost(
                self.host, self.port, self.path, stream,
                self.user, self.password)
        self.assertEqual('response contents', data)
        self.assertEqual(500, status)
        self.assertEqual('internal error', reason)
        # The connection is first instantiated.
        mock_connection.assert_called_once_with(self.host, self.port)
        mock_instance = mock_connection()
        # Then the remote request is performed passing the file contents.
        expected_headers = {
            'Content-Type': 'application/zip',
            'Authorization': 'Basic amVhbiBsdWM6c2VjcmV0IQ==',
        }
        mock_instance.request.assert_called_once_with(
            'POST', self.path, 'request contents', expected_headers)
        # The response is retrieved.
        mock_instance.getresponse.assert_called_once_with()
        # Finally the connection is closed.
        mock_instance.close.assert_called_once_with()
