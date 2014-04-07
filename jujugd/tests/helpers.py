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

"""Test helpers for the Juju Git Deploy plugin."""

from contextlib import contextmanager
from unittest import mock
from urllib import request


class ErrorTestsMixin:
    """Set up some base methods for testing functions raising exceptions."""

    @contextmanager
    def assert_error(self, exception_class, message, test_message=None):
        """Ensure the given exception is raised in the context block.

        Also check that the exception includes the expected error message.
        """
        with self.assertRaises(exception_class) as context_manager:
            yield
        self.assertEqual(message, str(context_manager.exception), test_message)


# Mock the builtin print function.
mock_print = mock.patch('builtins.print')


def patch_call(retcode, output='', error=''):
    """Patch the jujugd.utils.call function."""
    mock_call = mock.Mock(return_value=(retcode, output, error))
    return mock.patch('jujugd.utils.call', mock_call)


def patch_multiple_calls(side_effect):
    """Patch multiple subsequent jujugd.utils.call calls."""
    mock_call = mock.Mock(side_effect=side_effect)
    return mock.patch('jujugd.utils.call', mock_call)


def make_response(contents='', status=200, reason='OK'):
    """Create and return a response file-like object."""
    mock_read = mock.Mock(return_value=contents)
    return mock.Mock(status=status, reason=reason, read=mock_read)


def make_stream(contents, length=None):
    """Create and return a mock stream object."""
    mock_read = mock.Mock(return_value=contents)
    return mock.Mock(read=mock_read, length=length)


def patch_connection(contents='', status=200, reason='OK'):
    """Patch the http.client.HTTPSConnection object.

    The connection has a getresponse method returning a response like this:
        - response.read() returns the given contents;
        - response.status is the given status;
        - response.reason is the given reason.
    """
    mock_response = make_response(
        contents=contents.encode('utf-8'), status=status, reason=reason)
    mock_getresponse = mock.Mock(return_value=mock_response)
    mock_connection = mock.Mock(getresponse=mock_getresponse)
    mock_connection_class = mock.Mock(return_value=mock_connection)
    return mock.patch('http.client.HTTPSConnection', mock_connection_class)


def patch_urlopen(contents='', status=200, reason='OK', error=None):
    """Patch the urllib.request.urlopen function.

    The returned response is a file-like object set up like the following:
        - response.read() returns the given contents;
        - response.status is the given status;
        - response.reason is the given reason.

    If instead an error message is provided, the returned response generates
    an urllib.request.URLError side effect.
    """
    if error is None:
        mock_response = make_response(
            contents=contents, status=status, reason=reason)
        mock_urlopen = mock.Mock(return_value=mock_response)
    else:
        mock_urlopen = mock.Mock(side_effect=request.URLError(error))
    return mock.patch('urllib.request.urlopen', mock_urlopen)
