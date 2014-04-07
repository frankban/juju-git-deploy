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

PYTHON = python3
SYSDEPS = build-essential python3-dev python3-pip python-virtualenv

VENV = .venv
VENV_ACTIVATE = $(VENV)/bin/activate


$(VENV_ACTIVATE): test-requirements.pip requirements.pip
	virtualenv --distribute -p $(PYTHON) $(VENV)
	$(VENV)/bin/pip install --use-mirrors -r test-requirements.pip || \
		(touch test-requirements.pip; exit 1)
	@touch $(VENV_ACTIVATE)

all: setup

check: test lint

clean:
	$(PYTHON) setup.py clean
	rm -rfv build/ dist/ juju_git_deploy.egg-info MANIFEST
	rm -rfv $(VENV)
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -type d -delete

setup: $(VENV_ACTIVATE)

help:
	@echo -e 'Juju Git Deploy - list of make targets:\n'
	@echo 'make sysdeps - Install the development environment system packages.'
	@echo 'make - Set up the development and testing environment.'
	@echo 'make test - Run tests.'
	@echo 'make lint - Run linter and pep8.'
	@echo 'make check - Run tests, linter and pep8.'
	@echo 'make source - Create source package.'
	@echo 'make install - Install on local system.'
	@echo 'make clean - Get rid of bytecode files, build and dist dirs, venv.'
	@echo 'make release - Register and upload a release on PyPI.'

install:
	$(PYTHON) setup.py install
	pip3 install -r requirements.pip
	rm -rfv ./build ./dist ./juju_git_deploy.egg-info

lint: setup
	@$(VENV)/bin/flake8 --show-source --exclude=$(VENV) ./jujugd

release: check
	$(PYTHON) setup.py register sdist upload

source:
	$(PYTHON) setup.py sdist

sysdeps:
	sudo apt-get install --yes $(SYSDEPS)

test: setup
	@$(VENV)/bin/nosetests -s --verbosity=2 \
	    --with-coverage --cover-package=jujugd jujugd
	@rm .coverage

.PHONY: all clean check help install lint release setup source sysdeps test
