.PHONY: help install install-dev test lint format clean run setup pre-commit

# Default target
help:
	@echo "Available commands:"
	@echo "  make install      - Install production dependencies"
	@echo "  make install-dev  - Install development dependencies"
	@echo "  make setup        - Initial project setup"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Run linters"
	@echo "  make format       - Format code"
	@echo "  make clean        - Clean cache and temporary files"
	@echo "  make run          - Run the bot"
	@echo "  make pre-commit   - Install pre-commit hooks"

# Install production dependencies
install:
	pip install --upgrade pip
	pip install -r requirements.txt

# Install development dependencies
install-dev: install
	pip install -r requirements-dev.txt

# Initial setup
setup: install-dev pre-commit
	@echo "Creating necessary directories..."
	@mkdir -p data cache logs temp
	@echo "Copying example config..."
	@if [ ! -f data/config.ini ]; then cp config.ini.example data/config.ini; fi
	@echo "Setup complete! Edit data/config.ini with your credentials"

# Run tests
test:
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term

# Run linters
lint:
	flake8 src/ --max-line-length=100 --extend-ignore=E203,W503
	mypy src/ --ignore-missing-imports
	bandit -r src/
	black --check src/
	isort --check-only src/

# Format code
format:
	black src/ --line-length=100
	isort src/ --profile black --line-length 100

# Clean temporary files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.tmp" -delete
	find . -type f -name "*.temp" -delete
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf .mypy_cache
	rm -rf build dist *.egg-info

# Run the bot
run:
	python -m src.main

# Install pre-commit hooks
pre-commit:
	pre-commit install
	pre-commit run --all-files || true

# Development server with auto-reload
dev:
	python -m src.main --debug

# Check code quality
quality: lint test
	@echo "Code quality check complete!"

# Build distribution
build: clean
	python -m build

# Upload to PyPI (requires credentials)
upload: build
	python -m twine upload dist/*

# Docker commands (if using Docker)
docker-build:
	docker build -t sakaibot:latest .

docker-run:
	docker run -it --rm -v $(PWD)/data:/app/data sakaibot:latest