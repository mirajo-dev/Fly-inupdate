PYTHON = python3
VENV = venv
VENV_BIN = $(VENV)/bin

install:
	$(PYTHON) -m venv $(VENV)
	$(VENV_BIN)/pip install --upgrade pip
	$(VENV_BIN)/pip install pygame flake8 mypy

run:
	PYGAME_HIDE_SUPPORT_PROMPT=1 $(VENV_BIN)/python display.py maps/easy/01_linear_path.txt

run-visual:
	$(VENV_BIN)/python display.py maps/easy/01_linear_path.txt --visu

debug:
	$(VENV_BIN)/python -m pdb display.py maps/easy/01_linear_path.txt

lint:
	$(VENV_BIN)/flake8 .
	$(VENV_BIN)/mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	$(VENV_BIN)/flake8 .
	$(VENV_BIN)/mypy . --strict

clean:
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

.PHONY: install run debug lint lint-strict clean