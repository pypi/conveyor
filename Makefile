default:
	@echo "Call a specific subcommand:"
	@echo
	@$(MAKE) -pRrq -f $(lastword $(MAKEFILE_LIST)) : 2>/dev/null\
	| awk -v RS= -F: '/^# File/,/^# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}'\
	| sort\
	| egrep -v -e '^[^[:alnum:]]' -e '^$@$$'
	@echo
	@exit 1

# Optionally overriden by the user, if they're using a virtual environment manager.
VENV ?= env

# On Windows, venv scripts/shims are under `Scripts` instead of `bin`.
VENV_BIN := $(VENV)/bin
ifeq ($(OS),Windows_NT)
	VENV_BIN := $(VENV)/Scripts
endif

$(VENV)/pyvenv.cfg:
	# Create our Python 3 virtual environment
	python3 -m venv $(VENV)
	$(VENV_BIN)/python -m pip install --upgrade pip pip-tools tox

.PHONY: tests
tests: $(VENV)/pyvenv.cfg
	. $(VENV_BIN)/activate && \
		tox

requirements.txt: requirements.in $(VENV)/pyvenv.cfg
	. $(VENV_BIN)/activate && \
		pip-compile --allow-unsafe --output-file=$@ $<
