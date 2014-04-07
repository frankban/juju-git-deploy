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

"""Tests for the Juju Git Deploy interaction with the Juju environment."""

import os
import shutil
import tempfile
from unittest import (
    mock,
    TestCase,
)

import yaml

from . import helpers
from .. import env


class TestGetDefaultEnvName(TestCase):

    def test_environment_variable(self):
        # The environment name is successfully returned if JUJU_ENV is set.
        with mock.patch('os.environ', {'JUJU_ENV': 'ec2'}):
            env_name = env.get_default_env_name()
        self.assertEqual('ec2', env_name)

    def test_empty_environment_variable(self):
        # The environment name is not found if JUJU_ENV is empty.
        with helpers.patch_call(1):
            with mock.patch('os.environ', {'JUJU_ENV': ' '}):
                env_name = env.get_default_env_name()
        self.assertIsNone(env_name)

    def test_no_environment_variable(self):
        # The environment name is not found if JUJU_ENV is not defined.
        with helpers.patch_call(1):
            with mock.patch('os.environ', {}):
                env_name = env.get_default_env_name()
        self.assertIsNone(env_name)

    def test_juju_switch(self):
        # The environment name is successfully returned if retrievable using
        # the "juju switch" command. This test exercises the new "juju switch"
        # returning a machine readable output (just the name of the env).
        # This new behavior has been introduced in juju-core 1.17.
        output = 'ec2\n'
        with helpers.patch_call(0, output=output) as mock_call:
            with mock.patch('os.environ', {}):
                env_name = env.get_default_env_name()
        self.assertEqual('ec2', env_name)
        mock_call.assert_called_once_with('juju', 'switch')

    def test_juju_switch_failure(self):
        # The environment name is not found if "juju switch" returns an error.
        with helpers.patch_call(1) as mock_call:
            with mock.patch('os.environ', {}):
                env_name = env.get_default_env_name()
        self.assertIsNone(env_name)
        mock_call.assert_called_once_with('juju', 'switch')


class TestParseJenv(TestCase):

    def make_jenv(self, contents, env_name='ec2'):
        """Create a jenv file in a temp dir containing the given contents.

        Return the path to the temporary directory including the Juju home
        in which the jenv file can be found.
        """
        home_path = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home_path)
        environments_path = os.path.join(home_path, '.juju', 'environments')
        os.makedirs(environments_path)
        jenv_path = os.path.join(environments_path, '{}.jenv'.format(env_name))
        with open(jenv_path, 'w') as jenv_file:
            jenv_file.write(contents)
        return home_path

    def test_config_provided_to_parser(self):
        # The bootstrap config retrieved parsing the jenv file contents is
        # correctly passed to the parser function.
        config = {'default-series': 'trusty'}
        contents = yaml.dump({'bootstrap-config': config})
        home_path = self.make_jenv(contents)
        mock_parser = mock.Mock()
        with mock.patch('os.environ', {'HOME': home_path}):
            env.parse_jenv('ec2', mock_parser)
        mock_parser.assert_called_once_with(config)

    def test_parser_return_value(self):
        # The function returns what is returned by the given parser callable.
        config = {'default-series': 'trusty'}
        contents = yaml.dump({'bootstrap-config': config})
        home_path = self.make_jenv(contents)
        with mock.patch('os.environ', {'HOME': home_path}):
            value = env.parse_jenv('ec2', mock.Mock(return_value=42))
        self.assertEqual(42, value)

    def test_file_not_found(self):
        # A ValueError is raised if the jenv file does not exist.
        contents = yaml.dump({'bootstrap-config': {}})
        home_path = self.make_jenv(contents)
        with mock.patch('os.environ', {'HOME': home_path}):
            with self.assertRaises(ValueError) as context_manager:
                env.parse_jenv('no-such-env', mock.Mock())
        self.assertIn(
            'No such file or directory', str(context_manager.exception))

    def test_invalid_yaml(self):
        # A ValueError is raised if the jenv file is not a YAML.
        home_path = self.make_jenv(':')
        with mock.patch('os.environ', {'HOME': home_path}):
            with self.assertRaises(ValueError) as context_manager:
                env.parse_jenv('ec2', mock.Mock())
        self.assertIn("found ':'", str(context_manager.exception))

    def test_invalid_yaml_contents(self):
        # A ValueError is raised if the jenv file contents are not structured
        # as expected.
        contents = yaml.dump({'bootstrap-config': 42})
        home_path = self.make_jenv(contents)
        with mock.patch('os.environ', {'HOME': home_path}):
            with self.assertRaises(ValueError) as context_manager:
                env.parse_jenv('ec2', mock.Mock())
        self.assertIn(
            'invalid configuration file', str(context_manager.exception))


class TestGetPassword(helpers.ErrorTestsMixin, TestCase):

    error = 'unable to find the environment password'

    def test_value_found(self):
        # The password is correctly returned if included in the configuration.
        password = env.get_password({'admin-secret': 'secret!'})
        self.assertEqual('secret!', password)

    def test_empty_value(self):
        # A ValueError is raised if the password is empty.
        with self.assert_error(ValueError, self.error):
            env.get_password({'admin-secret': ''})

    def test_invalid_configuration(self):
        # A ValueError is returned if the configuration does not include the
        # password.
        with self.assert_error(ValueError, self.error):
            env.get_password({})


class TestGetDefaultSeries(helpers.ErrorTestsMixin, TestCase):

    error = 'unable to find the environment default series'

    def test_value_found(self):
        # The series is correctly returned if included in the configuration.
        series = env.get_default_series({'default-series': 'trusty'})
        self.assertEqual('trusty', series)

    def test_empty_value(self):
        # A ValueError is raised if the default series value is empty.
        with self.assert_error(ValueError, self.error):
            env.get_default_series({'default-series': ''})

    def test_invalid_configuration(self):
        # A ValueError is returned if the configuration does not include the
        # default series.
        with self.assert_error(ValueError, self.error):
            env.get_default_series({})
