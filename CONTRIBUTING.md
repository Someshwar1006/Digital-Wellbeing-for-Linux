# Contributing to ZenScreen

First off, thank you for considering contributing to ZenScreen! 🎉

## Code of Conduct

This project adheres to a Code of Conduct. By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the existing issues. When creating a bug report, include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Describe the behavior you observed and what you expected**
- **Include your environment details**:
  - Desktop environment (GNOME, KDE, etc.)
  - Display server (X11 or Wayland)
  - Python version
  - ZenScreen version

### Suggesting Features

Feature suggestions are welcome! Please:

- **Use a clear and descriptive title**
- **Explain why this feature would be useful**
- **Provide examples of how it would work**

### Pull Requests

1. **Fork the repo** and create your branch from `main`
2. **Install development dependencies**: `pip install -e ".[dev]"`
3. **Make your changes** and add tests if applicable
4. **Run tests**: `pytest tests/ -v`
5. **Format code**: `black zenscreen/` and `isort zenscreen/`
6. **Commit your changes** with a clear commit message
7. **Push to your fork** and submit a pull request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/zenscreen.git
cd zenscreen

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Format code
black zenscreen/
isort zenscreen/

# Type check
mypy zenscreen/
```

## Project Structure

```
zenscreen/
├── zenscreen/
│   ├── core/       # Core tracking and data logic
│   ├── cli/        # Command-line interface
│   ├── gui/        # GTK4 graphical interface
│   └── daemon/     # Background service
├── data/           # Desktop files and icons
├── systemd/        # Systemd service
└── tests/          # Test suite
```

## Code Style

- We use **Black** for code formatting
- We use **isort** for import sorting
- Line length is 100 characters
- Type hints are encouraged
- Docstrings should follow Google style

## Testing

- Write tests for new features
- Ensure all tests pass before submitting PR
- Aim for good test coverage

## Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Keep the first line under 72 characters
- Reference issues and PRs when relevant

Example:
```
Add weekly usage visualization chart

- Implement bar chart for past 7 days
- Add color coding based on usage levels
- Include trend indicator

Closes #42
```

## License

By contributing, you agree that your contributions will be licensed under the GPL-3.0 License.

## Questions?

Feel free to open an issue or start a discussion if you have questions!

---

Thank you for contributing! 💜
