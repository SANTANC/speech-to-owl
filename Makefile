PYTHON ?= python3
PIP ?= pip
START_DIR := Project_Files

install:
	$(PIP) install -r requirements.txt

run:
	$(PYTHON) -m $(START_DIR).main_app

test:
	$(PYTHON) -m unittest discover -s $(START_DIR) -p "test_*.py" -v

test-junit:
	$(PYTHON) -m $(START_DIR).run_tests_junit
