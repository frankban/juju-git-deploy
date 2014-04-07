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

"""Juju Git Deploy utility functions and classes."""

import base64
import http
import logging
import pipes
import subprocess
from urllib import request


def call(command, *args):
    """Call a subprocess passing the given arguments.

    Take the subcommand and its parameters as args.

    Return a tuple containing the subprocess return code, output and error.
    """
    pipe = subprocess.PIPE
    cmd = (command,) + args
    cmdline = ' '.join(map(pipes.quote, cmd))
    logging.debug('running the following: {}'.format(cmdline))
    try:
        process = subprocess.Popen(cmd, stdout=pipe, stderr=pipe)
    except OSError as err:
        # A return code 127 is returned by the shell when the command is not
        # found in the PATH.
        return 127, '', '{}: {}'.format(command, err)
    output, error = process.communicate()
    retcode = process.poll()
    logging.debug('retcode: {} | output: {!r} | error: {!r}'.format(
        retcode, output, error))
    return retcode, output.decode('utf-8'), error.decode('utf-8')


def get_service_from_charm(charm_url):
    """Return a service name given a charm URL."""
    return charm_url.split('/')[1].rsplit('-', 1)[0]


def urlget(url):
    """Open the given remote URL.

    Return the HTTP response file-like object.

    Raise an IOError if the URL is unreachable or in the case an invalid
    response is returned.
    """
    logging.debug('http -> {}'.format(url))
    try:
        response = request.urlopen(url)
    except request.URLError as err:
        raise IOError(err.reason)
    if response.status != 200:
        msg = 'invalid response from {} ({}): {}'.format(
            url, response.status, response.reason)
        raise IOError(msg)
    logging.debug('http <- {} {}'.format(response.status, response.reason))
    return response


def urlpost(host, port, path, stream, user, password):
    """Post the given file-like object stream to the given URL.

    The user and password arguments are used for HTTP basic authentication.

    Return the response contents, status and reason.
    """
    auth = base64.b64encode('{}:{}'.format(user, password).encode('utf-8'))
    headers = {
        'Content-Type': 'application/zip',
        'Authorization': 'Basic {}'.format(auth.decode('utf-8')),
    }
    if stream.length is None:
        # The content length is not available: the body must be a byte string.
        body = stream.read()
    else:
        # Having the content length, we can provide it directly in the headers.
        headers['Content-Length'] = stream.length
        body = stream
    logging.debug('http -> {}:{}{} ({})'.format(host, port, path, headers))
    # Establish the HTTPS connection and send the request.
    connection = http.client.HTTPSConnection(host, port)
    connection.request('POST', path, body, headers)
    # Retrieve the server response.
    response = connection.getresponse()
    data = response.read().decode('utf-8')
    logging.debug('http <- {} (status: {})'.format(data, response.status))
    connection.close()
    return data, response.status, response.reason
