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

"""Tests for the Juju Git Deploy application management."""

import argparse
import logging
from unittest import (
    mock,
    TestCase,
)

from . import helpers
from .. import (
    __doc__ as app_doc,
    manage,
)


class TestDescriptionAction(TestCase):

    def setUp(self):
        # Set up the argument parser with a description action.
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument(
            '--test', action=manage._DescriptionAction, nargs=0)

    @mock.patch('sys.exit')
    @helpers.mock_print
    def test_action(self, mock_print, mock_exit):
        # The action just prints the description and exits.
        args = self.parser.parse_args(['--test'])
        self.assertIsNone(args.test)
        mock_print.assert_called_once_with(app_doc)
        mock_exit.assert_called_once_with(0)


class TestPositiveInteger(helpers.ErrorTestsMixin, TestCase):

    def test_valid_value(self):
        # No errors are raised if the value is a positive integer.
        for value in ('1', 42, '47'):
            manage._positive_integer(value)

    def test_not_a_number(self):
        # An argparse error is raised if the value cannot be converted to an
        # integer.
        expected_exception = argparse.ArgumentTypeError
        for value in (None, 'bad wolf', []):
            expected_error = '{!r} is not a number'.format(value)
            with self.assert_error(expected_exception, expected_error, value):
                manage._positive_integer(value)

    def test_not_a_positive_number(self):
        # An argparse error is raised if the value is not > 0.
        expected_exception = argparse.ArgumentTypeError
        for value in (-42, -1, 0):
            expected_error = '{!r} is not a positive number'.format(value)
            with self.assert_error(expected_exception, expected_error, value):
                manage._positive_integer(value)


class TestValidatePlacement(TestCase):

    def setUp(self):
        # Set up a mock parser.
        self.parser = mock.Mock()

    def test_multiple_units(self):
        # More than one units can be requested if machine is not specified.
        options = mock.Mock(num_units=42, machine=None)
        manage._validate_placement(options, self.parser)
        self.assertFalse(self.parser.error.called)

    def test_single_placed_unit(self):
        # A single unit can be placed to a specific machine.
        options = mock.Mock(num_units=1, machine='42')
        manage._validate_placement(options, self.parser)
        self.assertFalse(self.parser.error.called)

    def test_multiple_units_error(self):
        # The parser exits with an error if multiple units are requested and
        # a machine target is specified.
        options = mock.Mock(num_units=42, machine='1')
        manage._validate_placement(options, self.parser)
        self.parser.error.assert_called_once_with(
            'cannot use --num-units > 1 with --to')


class TestSetup(TestCase):

    def patch_get_default_env_name(self, env_name=None):
        """Patch the function used by setup() to retrieve the default env name.

        This way the test does not rely on the user's Juju environment set up,
        and it is also possible to simulate an arbitrary environment name.
        """
        mock_get_default_env_name = mock.Mock(return_value=env_name)
        return mock.patch(
            'jujugd.env.get_default_env_name', mock_get_default_env_name)

    def patch_configure_logging(self):
        """Patch the function used by setup() to configure logging."""
        return mock.patch('jujugd.manage._configure_logging')

    def call_setup(self, args, env_name=None):
        """Call the setup function simulating the given args and env name."""
        with mock.patch('sys.stderr'):
            with mock.patch('sys.argv', ['juju-git-deploy'] + args):
                with mock.patch('sys.exit'):
                    with self.patch_get_default_env_name(env_name):
                        manage.setup()

    def test_help(self):
        # The program help message is properly formatted.
        with mock.patch('sys.stdout') as mock_stdout:
            with self.patch_configure_logging():
                self.call_setup(['--help'])
        stdout_write = mock_stdout.write
        self.assertTrue(stdout_write.called)
        # Retrieve the output from the mock call.
        output = stdout_write.call_args[0][0]
        self.assertIn('usage: juju-git-deploy', output)
        self.assertIn(app_doc, output)
        self.assertIn('--environment', output)
        self.assertIn('The name of the Juju environment to use\n', output)

    def test_help_with_default_environment(self):
        # The program help message is properly formatted when a default Juju
        # environment is found.
        with mock.patch('sys.stdout') as mock_stdout:
            with self.patch_configure_logging():
                self.call_setup(['--help'], env_name='hp')
        stdout_write = mock_stdout.write
        self.assertTrue(stdout_write.called)
        # Retrieve the output from the mock call.
        output = stdout_write.call_args[0][0]
        self.assertIn('The name of the Juju environment to use (hp)\n', output)

    def test_description(self):
        # The program description is properly printed out as required by juju.
        with helpers.mock_print as mock_print:
            with self.patch_configure_logging():
                self.call_setup(['--description'])
        mock_print.assert_called_once_with(app_doc)

    def test_configure_logging(self):
        # Logging is properly set up at the info level.
        with self.patch_configure_logging() as mock_configure_logging:
            self.call_setup(['user/repo'])
        mock_configure_logging.assert_called_once_with(logging.INFO)

    def test_configure_logging_debug(self):
        # Logging is properly set up at the debug level.
        with self.patch_configure_logging() as mock_configure_logging:
            self.call_setup(['user/repo', '--debug'])
        mock_configure_logging.assert_called_once_with(logging.DEBUG)
