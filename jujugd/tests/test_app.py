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

"""Tests for the Juju Git Deploy base application function."""

from contextlib import contextmanager
from unittest import (
    mock,
    TestCase,
)

import yaml

from . import helpers
from .. import app


class TestProgramExit(TestCase):

    def test_string_representation(self):
        # The error is correctly represented as a string.
        exception = app.ProgramExit('bad wolf')
        self.assertEqual('juju-git-deploy: error: bad wolf', str(exception))


class TestPrepare(helpers.ErrorTestsMixin, TestCase):

    @contextmanager
    def patch_all(self, series='trusty'):
        """Patch the API and environment calls used by app.prepare."""
        patch_api_address = mock.patch(
            'jujugd.api.get_api_address', return_value='10.0.3.1:17070')
        # Patch the env.parse_jenv call: this is used two times, the first time
        # to return the environment's password, the second time to fetch the
        # default series.
        patch_parse_jenv = mock.patch(
            'jujugd.env.parse_jenv', side_effect=['secret!', series])
        with patch_api_address:
            with patch_parse_jenv:
                yield

    def test_collected_info(self):
        # The required info (zip URL, Juju API address, Juju environment
        # password and default series) is returned.
        with self.patch_all():
            zip_url, api_address, password, series = app.prepare(
                'hatched/ghost-charm', 'ec2', None)
        self.assertEqual(
            'https://api.github.com/repos/hatched/ghost-charm/zipball/',
            zip_url)
        self.assertEqual('10.0.3.1:17070', api_address)
        self.assertEqual('secret!', password)
        self.assertEqual('trusty', series)

    def test_series_not_found_in_jenv(self):
        # The bootstrap node series is used if the default series is not
        # included in the jenv file.
        status_output = yaml.dump({'machines': {'0': {'series': 'saucy'}}})
        with self.patch_all(series=''):
            with helpers.patch_call(0, status_output):
                zip_url, api_address, password, series = app.prepare(
                    'hatched/ghost-charm', 'ec2', None)
        self.assertEqual(
            'https://api.github.com/repos/hatched/ghost-charm/zipball/',
            zip_url)
        self.assertEqual('10.0.3.1:17070', api_address)
        self.assertEqual('secret!', password)
        self.assertEqual('saucy', series)

    def test_invalid_repository(self):
        # A ProgramExit is raised if the Github repository is not valid.
        expected = 'juju-git-deploy: error: invalid repository: invalid-repo'
        with self.patch_all():
            with self.assert_error(app.ProgramExit, expected):
                app.prepare('invalid-repo', 'ec2', None)


@helpers.mock_print
class TestProcess(helpers.ErrorTestsMixin, TestCase):

    api_address = '10.0.3.1:17070'
    password = 'secret!'
    zip_url = 'api.example.com/django'

    def patch_upload_charm(self, error=False):
        side_effect = IOError('bad wolf') if error else 'local:trusty/django-1'
        return mock.patch('jujugd.api.upload_charm', side_effect=[side_effect])

    def test_charm_url(self, mock_print):
        # The function return the newly uploaded local charm URL.
        with helpers.patch_urlopen(contents='zip contents') as mock_urlopen:
            with self.patch_upload_charm(error=False) as mock_upload_charm:
                charm_url = app.process(
                    self.zip_url, self.api_address, self.password, 'trusty')
        self.assertEqual('local:trusty/django-1', charm_url)
        mock_urlopen.assert_called_once_with(self.zip_url)
        mock_upload_charm.assert_called_once_with(
            self.api_address, mock_urlopen(), self.password, 'trusty')
        self.assertEqual(2, mock_print.call_count)
        mock_print.assert_has_calls([
            mock.call('connecting to github'),
            mock.call('uploading charm'),
        ])

    def test_charm_retrieval_error(self, mock_print):
        # A ProgramExit is raised if a problem occurs fetching the charm.
        expected_error = (
            'juju-git-deploy: error: '
            'unable to retrieve charm contents: '
            'invalid response from api.example.com/django (400): '
            'bad request'
        )
        with helpers.patch_urlopen(status=400, reason='bad request'):
            with self.assert_error(app.ProgramExit, expected_error):
                app.process(
                    self.zip_url, self.api_address, self.password, 'trusty')

    def test_upload_error(self, mock_print):
        # A ProgramExit is raised if a problem occurs uploading the charm.
        expected_error = (
            'juju-git-deploy: error: charm upload failed: bad wolf')
        with helpers.patch_urlopen(contents='zip contents'):
            with self.patch_upload_charm(error=True):
                with self.assert_error(app.ProgramExit, expected_error):
                    app.process(
                        self.zip_url, self.api_address, self.password,
                        'trusty')
