# Makefile for Hardware Control System Tests

.PHONY: help install test test-unit test-integration test-quick test-coverage \
        test-safety test-parallel test-html clean lint format check report

# Default target
help:
	@echo "Hardware Control System - Test Commands"
	@echo "========================================"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install test dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test            Run all tests"
	@echo "  make test-unit       Run unit tests only"
	@echo "  make test-integration Run integration tests only"
	@echo "  make test-quick      Run quick smoke tests"
	@echo "  make test-coverage   Run tests with coverage report"
	@echo "  make test-safety     Run safety-critical tests"
	@echo "  make test-parallel   Run tests in parallel (faster)"
	@echo "  make test-html       Generate HTML test report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint            Run linting checks"
	@echo "  make format          Format code with black"
	@echo "  make check           Run all quality checks"
	@echo ""
	@echo "Reporting:"
	@echo "  make report          Generate all reports"
	@echo "  make coverage-html   Open coverage report in browser"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean           Remove generated files"

# Installation
install:
	@echo "Installing test dependencies..."
	pip install -r test_requirements.txt
	@echo "✅ Dependencies installed"

# Test commands
test:
	@echo "Running all tests..."
	python run_tests.py --all

test-unit:
	@echo "Running unit tests..."
	python run_tests.py --unit

test-integration:
	@echo "Running integration tests..."
	python run_tests.py --integration

test-quick:
	@echo "Running quick smoke tests..."
	python run_tests.py --quick

test-coverage:
	@echo "Running tests with coverage..."
	python run_tests.py --coverage

test-safety:
	@echo "Running safety-critical tests..."
	python run_tests.py --safety

test-parallel:
	@echo "Running tests in parallel..."
	python run_tests.py --parallel

test-html:
	@echo "Generating HTML test report..."
	python run_tests.py --html

# Code quality
lint:
	@echo "Running linting checks..."
	flake8 *.py --max-line-length=100 --ignore=E501,W503
	pylint *.py --disable=C0111,C0103 || true

format:
	@echo "Formatting code..."
	black *.py
	isort *.py
	@echo "✅ Code formatted"

check:
	@echo "Running all quality checks..."
	python run_tests.py --quality

# Reporting
report: test-coverage test-html
	@echo "✅ All reports generated"

coverage-html: test-coverage
	@echo "Opening coverage report..."
	@if command -v xdg-open > /dev/null; then \
		xdg-open htmlcov/index.html; \
	elif command -v open > /dev/null; then \
		open htmlcov/index.html; \
	else \
		echo "Please open htmlcov/index.html manually"; \
	fi

# Cleanup
clean:
	@echo "Cleaning up generated files..."
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -f test_report.html
	rm -f report.json
	rm -f .coverage.*
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleanup complete"

# Continuous testing
watch:
	@echo "Watching for changes..."
	python run_tests.py --watch

# List all tests
list:
	@echo "Available tests:"
	python run_tests.py --list

# Run specific module tests
test-hardware:
	pytest -k "hardware" -v

test-motor:
	pytest -k "motor" -v

test-sensor:
	pytest -k "sensor" -v

test-calibration:
	pytest -k "calibration" -v

# Development convenience
dev: install
	@echo "Development environment ready!"

# Pre-commit hook setup
pre-commit: check test-quick
	@echo "✅ Pre-commit checks passed"

# Continuous Integration
ci: install test-coverage lint
	@echo "✅ CI checks complete"
