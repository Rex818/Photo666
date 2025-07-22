# Contributing to PyPhotoManager

Thank you for your interest in contributing to PyPhotoManager! This document provides guidelines and instructions for contributing to this project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/pyphoto-manager.git`
3. Set up the development environment:
   ```
   python setup_env.py
   ```
4. Activate the virtual environment:
   - Windows: `.venv\Scripts\activate`
   - Linux/Mac: `source .venv/bin/activate`

## Development Workflow

1. Create a new branch for your feature or bugfix:
   ```
   git checkout -b feature/your-feature-name
   ```

2. Make your changes, following the coding standards

3. Write tests for your changes

4. Run the tests:
   ```
   pytest
   ```

5. Format your code:
   ```
   black src tests
   ```

6. Check types:
   ```
   mypy src
   ```

7. Commit your changes:
   ```
   git commit -m "Add feature: your feature description"
   ```

8. Push to your fork:
   ```
   git push origin feature/your-feature-name
   ```

9. Create a Pull Request from your fork to the main repository

## Coding Standards

- Follow PEP 8 style guide
- Use type annotations
- Write docstrings for all functions, classes, and modules
- Keep functions small and focused
- Write unit tests for new functionality

## Commit Message Guidelines

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests after the first line

## Pull Request Process

1. Update the README.md or documentation with details of changes if appropriate
2. Update the tests to reflect your changes
3. The PR should work for Python 3.8 and above
4. Your PR needs to be approved by at least one maintainer

## Adding New Features

When adding new features, please follow these steps:

1. Discuss the feature in an issue before implementing
2. Follow the modular architecture of the project
3. Update documentation to reflect the new feature
4. Add appropriate tests

## Reporting Bugs

When reporting bugs, please include:

- A clear and descriptive title
- Steps to reproduce the bug
- Expected behavior
- Actual behavior
- Screenshots if applicable
- Your environment (OS, Python version, etc.)

## Code of Conduct

Please be respectful and inclusive in your interactions with others. We aim to foster an open and welcoming environment for all contributors.

## License

By contributing to PyPhotoManager, you agree that your contributions will be licensed under the project's MIT License.