# Contributing to AI Liberation Front

Thank you for your interest in contributing to the AI Liberation Front (ailf)! This document provides guidelines and instructions for contributing to this project.

## Prerequisites

- Python 3.12 or higher
- pip
- Redis (for messaging functionality)

## Development Environment

1. Clone the repository:
   ```bash
   git clone https://github.com/ai-liberation-front/ailf.git
   cd ailf
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

## Running Tests

Run the test suite with:

```bash
pytest
```

For test coverage:

```bash
pytest --cov=ailf tests/
```

## Code Style

This project follows PEP 8 style guidelines. We use the following tools to maintain consistent code quality:

- Black for code formatting
- isort for import sorting
- flake8 for linting
- mypy for type checking

Run all style checks with:

```bash
make lint
```

Or individually:

```bash
black .
isort .
flake8
mypy .
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add tests for any new functionality
5. Ensure all tests pass
6. Update documentation as necessary
7. Submit a pull request

## Documentation

Documentation is built with Sphinx. You can build the documentation locally with:

```bash
cd docs
make html
```

## Versioning

We use semantic versioning. Please make sure your changes are compatible with the versioning scheme.

## Contact

If you have questions, please open an issue on GitHub or contact the maintainers.

Thank you for contributing to AI Liberation Front!
