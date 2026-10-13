POETRY = poetry
RUN = $(POETRY) run
MAPS ?= maps/easy/01_linear_path.txt

install:
	$(POETRY) config virtualenvs.in-project true --local
	$(POETRY) install

run:
	PYGAME_HIDE_SUPPORT_PROMPT=1 $(RUN) python display.py $(MAPS)

run-visual:
	$(RUN) python display.py $(MAPS) --visuel

debug:
	$(RUN) python -m pdb display.py $(MAPS)

lint:
	$(RUN) flake8 .
	$(RUN) mypy . --warn-return-any --warn-unused-ignores \
		--ignore-missing-imports --disallow-untyped-defs \
		--check-untyped-defs

lint-strict:
	$(RUN) flake8 .
	$(RUN) mypy . --strict

clean:
	rm -rf .venv
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

.PHONY: install run run-visual debug lint lint-strict clean