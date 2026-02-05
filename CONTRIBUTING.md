# Contributing to ScamNest

Thank you for your interest in contributing to ScamNest! This document provides guidelines and instructions for contributing to the project.

---

## 📋 Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Contribution Workflow](#contribution-workflow)
5. [Coding Standards](#coding-standards)
6. [Testing Requirements](#testing-requirements)
7. [Pull Request Process](#pull-request-process)
8. [Issue Guidelines](#issue-guidelines)
9. [Documentation](#documentation)
10. [Community](#community)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors, regardless of experience level, background, or identity.

### Expected Behavior

- ✅ Be respectful and professional
- ✅ Provide constructive feedback
- ✅ Accept criticism gracefully
- ✅ Focus on what's best for the project
- ✅ Show empathy towards other contributors

### Unacceptable Behavior

- ❌ Harassment, discrimination, or offensive comments
- ❌ Trolling or insulting remarks
- ❌ Personal or political attacks
- ❌ Publishing others' private information
- ❌ Any behavior that could be considered inappropriate

**Reporting**: If you experience or witness unacceptable behavior, please contact the maintainers through GitHub.

---

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- GitHub account
- OpenAI API key (for testing)

### Find an Issue

1. Browse [open issues](https://github.com/adarshnaik1/ScamNest/issues)
2. Look for issues tagged with:
   - `good first issue` - Great for newcomers
   - `help wanted` - Maintainers need assistance
   - `bug` - Bug fixes needed
   - `enhancement` - New features

3. Comment on the issue to express interest
4. Wait for maintainer approval before starting work

### Types of Contributions

We welcome:
- 🐛 **Bug fixes**
- ✨ **New features**
- 📝 **Documentation improvements**
- 🧪 **Test coverage**
- ♻️ **Code refactoring**
- 🔒 **Security enhancements**
- 🌍 **Translations**

---

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/ScamNest.git
cd ScamNest

# Add upstream remote
git remote add upstream https://github.com/adarshnaik1/ScamNest.git
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux/MacOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
# Install production dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Or install both
pip install -r requirements.txt -r requirements-dev.txt
```

### 4. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your credentials
# At minimum, set:
# - API_KEY
# - OPENAI_API_KEY
```

### 5. Verify Setup

```bash
# Run tests
pytest

# Run linting
flake8 app/ tests/

# Format code
black --check app/ tests/

# Type check
mypy app/

# Run the application
uvicorn app.main:app --reload
```

---

## Contribution Workflow

### 1. Create a Branch

```bash
# Sync with upstream
git fetch upstream
git checkout main
git merge upstream/main

# Create feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/bug-description
```

**Branch Naming Convention**:
- `feature/add-redis-session-storage`
- `fix/authentication-bypass`
- `docs/update-readme`
- `refactor/improve-session-service`
- `test/add-unit-tests-for-detector`

### 2. Make Changes

- Write clean, readable code
- Follow existing code style
- Add tests for new functionality
- Update documentation as needed
- Keep commits atomic and logical

### 3. Commit Changes

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: add Redis session storage support"
```

**Commit Message Format**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Example**:
```
feat(session): add Redis session storage

- Implement RedisSessionService
- Add Redis configuration
- Update session_service to use Redis
- Add tests for Redis integration

Closes #123
```

### 4. Push Changes

```bash
# Push to your fork
git push origin feature/your-feature-name
```

### 5. Create Pull Request

1. Go to your fork on GitHub
2. Click "New Pull Request"
3. Select `main` as base branch
4. Select your feature branch as compare branch
5. Fill in the PR template
6. Click "Create Pull Request"

---

## Coding Standards

### General Guidelines

1. **Follow PEP 8** for Python code style
2. **Use type hints** wherever possible
3. **Write docstrings** for all public functions and classes (Google style)
4. **Keep functions small** (ideally < 50 lines)
5. **Use meaningful variable names** (no single-letter variables except loop counters)
6. **Avoid magic numbers** (use named constants)

### Data Privacy and Security

**⚠️ CRITICAL: Never log sensitive data without masking**

```python
# ❌ BAD - Exposes PII
logger.info(f"Processing UPI: {upi_id}")
logger.debug(f"API key: {api_key}")

# ✅ GOOD - Masked for safety
from app.services.data_masker import mask_for_logging, DataMasker

logger.info(f"Processing UPI: {mask_for_logging(upi_id)}")
logger.debug(f"API key: {DataMasker.mask_api_key(api_key)}")

# ✅ GOOD - Mask intelligence before logging
masked_intel = DataMasker.mask_intelligence(intelligence.model_dump())
logger.info(f"Extracted: {masked_intel}")
```

**Masking Requirements**:
- ✅ All phone numbers, UPI IDs, bank accounts, emails MUST be masked in logs
- ✅ API keys and tokens MUST be masked in all outputs
- ✅ Use context-aware masking: FULL for logs, PARTIAL for debugging
- ✅ Never mask data in callbacks (GUVI endpoint needs full data)
- ✅ Use `DemaskedData` wrapper for temporary de-masking with audit trail

### Coding Standards

### Python Style Guide

We follow **PEP 8** with some modifications:

#### Line Length
- Maximum: 100 characters (not 79)
- Exception: Long URLs, imports

#### Naming Conventions
```python
# Classes: PascalCase
class ScamDetector:
    pass

# Functions/Variables: snake_case
def detect_scam(message: str) -> bool:
    scam_probability = 0.0

# Constants: UPPER_SNAKE_CASE
MAX_MESSAGE_LENGTH = 10000

# Private: _leading_underscore
def _internal_helper():
    pass
```

#### Type Hints
Always use type hints:
```python
def process_message(
    message: str,
    session_id: str,
    confidence_threshold: float = 0.8
) -> dict[str, Any]:
    """Process incoming message and return response."""
    pass
```

#### Docstrings
Use Google-style docstrings:
```python
def extract_intelligence(text: str) -> ExtractedIntelligence:
    """
    Extract scam indicators from message text.
    
    Args:
        text: The message text to analyze
        
    Returns:
        ExtractedIntelligence object containing all found indicators
        
    Raises:
        ValueError: If text is empty or None
        
    Example:
        >>> intel = extract_intelligence("Send money to user@bank")
        >>> print(intel.upi_ids)
        ['user@bank']
    """
    pass
```

#### Imports
```python
# Standard library
import os
import re
from typing import Any, Dict, List, Optional

# Third-party
import fastapi
from pydantic import BaseModel

# Local
from app.config import settings
from app.models.schemas import HoneypotRequest
```

### Code Quality Tools

#### Black (Formatting)
```bash
# Format code
black app/ tests/

# Check without formatting
black --check app/ tests/
```

#### Flake8 (Linting)
```bash
# Lint code
flake8 app/ tests/

# With configuration
flake8 --max-line-length=100 --extend-ignore=E203,W503 app/
```

#### MyPy (Type Checking)
```bash
# Type check
mypy app/

# With strict mode
mypy --strict app/
```

#### isort (Import Sorting)
```bash
# Sort imports
isort app/ tests/

# Check without sorting
isort --check-only app/ tests/
```

### Pre-commit Hooks

Install pre-commit hooks to automate checks:

```bash
# Install pre-commit
pip install pre-commit

# Set up hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

---

## Testing Requirements

### Test Structure

```
tests/
├── __init__.py
├── conftest.py           # Shared fixtures
├── unit/                 # Unit tests
│   ├── test_services.py
│   ├── test_models.py
│   └── test_utils.py
└── integration/          # Integration tests
    ├── test_api.py
    └── test_end_to_end.py
```

### Writing Tests

#### Unit Tests
```python
import pytest
from app.services.intelligence_extractor import extract_upi_ids

def test_extract_upi_ids():
    """Test UPI ID extraction from message."""
    text = "Send money to user@paytm"
    upi_ids = extract_upi_ids(text)
    
    assert len(upi_ids) == 1
    assert upi_ids[0] == "user@paytm"

def test_extract_upi_ids_empty():
    """Test UPI ID extraction with no matches."""
    text = "This has no UPI ID"
    upi_ids = extract_upi_ids(text)
    
    assert len(upi_ids) == 0
```

#### Integration Tests
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_honeypot_endpoint():
    """Test honeypot endpoint with valid request."""
    response = client.post(
        "/honeypot",
        headers={"x-api-key": "test-key"},
        json={
            "sessionId": "test-001",
            "message": {
                "sender": "scammer",
                "text": "Urgent! Share OTP",
                "timestamp": "2026-02-05T10:00:00Z"
            },
            "conversationHistory": []
        }
    )
    
    assert response.status_code == 200
    assert "reply" in response.json()
```

### Test Coverage

- Aim for **>80% code coverage**
- Focus on critical paths
- Test edge cases and error conditions

```bash
# Run tests with coverage
pytest --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Test Requirements

- ✅ All new features must have tests
- ✅ Bug fixes must include regression tests
- ✅ Tests must pass before PR approval
- ✅ Maintain or improve coverage percentage

---

## Pull Request Process

### Before Submitting

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] Commit messages follow convention
- [ ] Branch is up-to-date with main
- [ ] No merge conflicts

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Related Issues
Fixes #123

## Testing
Describe testing performed

## Checklist
- [ ] Tests pass
- [ ] Documentation updated
- [ ] Code follows style guidelines
- [ ] No new warnings
```

### Review Process

1. **Automated Checks**: CI/CD runs tests and linting
2. **Code Review**: Maintainer reviews code
3. **Feedback**: Address review comments
4. **Approval**: Maintainer approves PR
5. **Merge**: Maintainer merges to main

### Review Timeline

- **Initial Response**: Within 3 days
- **Follow-up**: Within 1 week
- **Merge**: After approval and CI passes

---

## Issue Guidelines

### Creating Issues

#### Bug Reports

```markdown
**Bug Description**
Clear description of the bug

**Steps to Reproduce**
1. Step 1
2. Step 2
3. See error

**Expected Behavior**
What should happen

**Actual Behavior**
What actually happens

**Environment**
- OS: Windows 10
- Python: 3.10
- Version: 1.0.0

**Logs**
```
Paste relevant logs
```
````

#### Feature Requests

```markdown
**Feature Description**
Clear description of proposed feature

**Use Case**
Why is this feature needed?

**Proposed Solution**
How could this be implemented?

**Alternatives Considered**
Other solutions you've considered

**Additional Context**
Any other relevant information
```

---

## Documentation

### Documentation Requirements

- Update README.md for user-facing changes
- Update API_SPEC.md for API changes
- Update ARCHITECTURE.md for structural changes
- Add inline comments for complex logic
- Update docstrings for modified functions

### Documentation Style

- Use clear, concise language
- Include code examples
- Add diagrams where helpful
- Keep it up-to-date

---

## Community

### Getting Help

- **GitHub Issues**: For bugs and features
- **Discussions**: For questions and ideas
- **Email**: Contact maintainer via GitHub profile

### Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Credited in release notes
- Thanked publicly (if desired)

---

## License

By contributing to ScamNest, you agree that your contributions will be licensed under the MIT License.

---

## Questions?

If you have questions about contributing, please:
1. Check existing documentation
2. Search closed issues
3. Open a new issue with "Question:" prefix

---

**Thank you for contributing to ScamNest!** 🎉

Every contribution, no matter how small, helps make the internet safer.

---

**Last Updated**: February 5, 2026  
**Version**: 1.0
