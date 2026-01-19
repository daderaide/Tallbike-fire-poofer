# Makefile for MicroPython ESP32-S3 project

.PHONY: help setup test clean

help:
	@echo "Available targets:"
	@echo "  make setup  - Create virtual environment and install dependencies"
	@echo "  make test   - Run unit tests"
	@echo "  make clean  - Remove virtual environment and cache files"

setup:
	python3 -m venv venv
	. venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt
	@echo "Virtual environment created! Activate it with: source venv/bin/activate"

test:
	pytest tests/ -v

clean:
	rm -rf venv/
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type d -name ".coverage" -exec rm -r {} +
