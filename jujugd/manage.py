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

"""Juju Git Deploy application management."""

import argparse
import logging

from . import (
    __doc__ as app_doc,
    app,
    env,
    get_version,
)


class _DescriptionAction(argparse.Action):
    """A customized argparse action that just shows a description."""

    def __call__(self, parser, *args, **kwargs):
        print(app_doc)
        parser.exit()


def _configure_logging(level):
    """Set up the application logging."""
    root = logging.getLogger()
    # Remove any previous handler on the root logger.
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    logging.basicConfig(
        level=level,
        format=(
            '%(asctime)s %(levelname)s '
            '%(module)s@%(funcName)s:%(lineno)d '
            '%(message)s'
        ),
        datefmt='%H:%M:%S',
    )


def _positive_integer(value):
    """An argparse type for positive integer numbers."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        msg = '{!r} is not a number'.format(value)
        raise argparse.ArgumentTypeError(msg)
    if value < 1:
        msg = '{!r} is not a positive number'.format(value)
        raise argparse.ArgumentTypeError(msg)


def _validate_placement(options, parser):
    """Ensure one unit has been requested if machine is not None."""
    if (options.machine is not None) and (options.num_units != 1):
        parser.error('cannot use --num-units > 1 with --to')


def setup():
    """Set up the application options and logger.

    Return the options as a namespace containing the following attributes:
        - repo: the Github repository/branch hosting the charm;
        - service: the service name, or None if the name must be derived from
          the charm name;
        - series: the OS series, or None if the default environment series must
          be used;
        - num_units: the number of units to be deployed;
        - machine: the machine/container where to deploy the unit;
        - env_name: the name of the Juju environment to use.
    """
    default_env_name = env.get_default_env_name()
    # Define the help message for the --environment option.
    env_help = 'The name of the Juju environment to use'
    if default_env_name is not None:
        env_help = '{} (%(default)s)'.format(env_help)
    # Create and set up the arguments parser.
    parser = argparse.ArgumentParser(
        description=app_doc, formatter_class=argparse.RawTextHelpFormatter)
    # Note: since we use the RawTextHelpFormatter, when adding/changing options
    # make sure the help text is nicely displayed on small 80 columns terms.
    parser.add_argument(
        'repo',
        help='The Github repository hosting the charm, e.g.\n'
             '    juju git-deploy github.com/hatched/ghost-charm\n'
             'The charm above can be deployed also copy/pasting the URL:\n'
             '    juju git-deploy https://github.com/hatched/ghost-charm\n'
             'It is possible to use the simplified {user}/{repo} form:\n'
             '    juju git-deploy hatched/ghost-charm\n'
             'To deploy a specific git branch or reference, append a colon\n'
             'followed by the reference identifier, e.g.:\n'
             '    juju git-deploy frankban/ghost-charm:develop\n'
             "If the reference is not specified, the repository's default\n"
             'branch is used (usually "master")')
    parser.add_argument(
        'service', default=None, nargs='?',
        help='The service name. If omitted, the service name is derived from\n'
             'the charm name')
    parser.add_argument(
        '-s', '--series',
        help='The OS series to use when deploying the charm. If not\n'
             'specified, the default series for the Juju environment is used')
    parser.add_argument(
        '-n', '--num-units', type=_positive_integer, default=1,
        help='The number of units to be deployed (default: 1)')
    parser.add_argument(
        '--to', dest='machine',
        help='The machine or container to deploy the unit in.\n'
             'See "juju help deploy"')
    parser.add_argument(
        '-e', '--environment', default=default_env_name, dest='env_name',
        help=env_help)
    parser.add_argument(
        '--version', action='version',
        version='%(prog)s {}'.format(get_version()))
    parser.add_argument(
        '--debug', action='store_true',
        help='Turn debug mode on. When enabled, all the subcommands\n'
             'and API calls are logged to stdout')
    # This is required by juju-core: see "juju help plugins".
    parser.add_argument(
        '--description', action=_DescriptionAction, default=argparse.SUPPRESS,
        nargs=0, help="Show program's description and exit")
    # Parse the provided arguments.
    options = parser.parse_args()
    # Validate the provided arguments.
    _validate_placement(options, parser)
    # Set up logging.
    _configure_logging(logging.DEBUG if options.debug else logging.INFO)
    return options


def run(options):
    """Run the application."""
    zip_url, api_address, password, series = app.prepare(
        options.repo, options.env_name, options.series)
    charm_url = app.process(zip_url, api_address, password, series)
    app.deploy(
        charm_url, options.service, options.num_units, options.machine,
        api_address, password)
