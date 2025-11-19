# Contributing to Cookie Scanner Platform

Thank you for your interest in contributing to the Cookie Scanner Platform! This document provides guidelines and instructions for contributing to the project.

## Table of Contents
1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Development Workflow](#development-workflow)
5. [Coding Standards](#coding-standards)
6. [Testing Guidelines](#testing-guidelines)
7. [Commit Messages](#commit-messages)
8. [Pull Request Process](#pull-request-process)
9. [Documentation](#documentation)
10. [Getting Help](#getting-help)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors. We expect all participants to:

- Be respectful and considerate
- Accept constructive criticism gracefully
- Focus on what is best for the community
- Show empathy towards other community members

### Unacceptable Behavior

- Harassment, discrimination, or offensive comments
- Personal attacks or trolling
- Publishing others' private information
- Other conduct that could reasonably be considered inappropriate

---

## Getting Started

### Prerequisites

Before contributing, ensure you have:

- Python 3.11 or higher
- Node.js 18 or higher
- PostgreSQL 15 or higher
- Redis 7 or higher
- Docker and Docker Compose (for local development)
- Git

### Finding Issues to Work On

1. Check the [Issues](https://github.com/your-org/cookie-scanner/issues) page
2. Look for issues labeled `good first issue` or `help wanted`
3. Comment on the issue to express interest
4. Wait for maintainer approval before starting work

### Reporting Bugs

When reporting bugs, include:

- Clear, descriptive title
- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- Environment details (OS, Python version, etc.)
- Screenshots or logs if applicable

**Bug Report Template:**
```markdown
**Description:**
Brief description of the bug

**Steps to Reproduce:**
1. Step one
2. Step two
3. Step three

**Expected Behavior:**
What should happen

**Actual Behavior:**
What actually happens

**Environment:**
- OS: macOS 14.0
- Python: 3.11.5
- Browser: Chrome 120
```

### Suggesting Features

When suggesting features, include:

- Clear use case and problem statement
- Proposed solution
- Alternative solutions considered
- Impact on existing functionality

---

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub
# Clone your fork
git clone https://github.com/YOUR_USERNAME/cookie-scanner.git
cd cookie-scanner

# Add upstream remote
git remote add upstream https://github.com/your-org/cookie-scanner.git
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 3. Set Up Database

```bash
# Start PostgreSQL and Redis with Docker
docker-compose up -d postgres redis

# Run migrations
python run_migrations.py
```

### 4. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your local settings
# Key variables:
# - DATABASE_URL
# - REDIS_URL
# - JWT_SECRET_KEY
```

### 5. Set Up Dashboard

```bash
cd dashboard

# Install dependencies
npm install

# Copy environment file
cp .env.local.example .env.local

# Edit .env.local with API URL
```

### 6. Verify Setup

```bash
# Run tests
pytest

# Start API server
python run_api.py

# In another terminal, start dashboard
cd dashboard
npm run dev
```

Visit `http://localhost:3000` to verify the dashboard loads.

---

## Development Workflow

### 1. Create a Branch

```bash
# Update main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name
```

**Branch Naming Convention:**
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Test additions or fixes

### 2. Make Changes

- Write clean, readable code
- Follow coding standards (see below)
- Add tests for new functionality
- Update documentation as needed

### 3. Test Your Changes

```bash
# Run unit tests
pytest

# Run specific test file
pytest tests/test_scan_service.py

# Run with coverage
pytest --cov=services --cov-report=html

# Run integration tests
pytest tests/integration/

# Lint code
flake8 .
black --check .
mypy .
```

### 4. Commit Changes

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: add real-time scan progress streaming"
```

### 5. Push and Create Pull Request

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create pull request on GitHub
# Fill out the PR template
```

---

## Coding Standards

### Python Code Style

We follow [PEP 8](https://pep8.org/) with some modifications:

**Formatting:**
- Use [Black](https://black.readthedocs.io/) for code formatting
- Line length: 100 characters
- Use double quotes for strings
- 4 spaces for indentation

**Imports:**
```python
# Standard library imports
import os
import sys
from typing import List, Optional

# Third-party imports
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Local imports
from services.scan_service import ScanService
from models.scan import ScanResult
```

**Type Hints:**
Always use type hints for function parameters and return values:

```python
def calculate_compliance_score(cookies: List[Cookie]) -> float:
    """Calculate compliance score from cookie list."""
    # Implementation
    return score
```

**Docstrings:**
Use Google-style docstrings:

```python
def create_scan(domain: str, scan_mode: str) -> ScanResult:
    """Create and execute a new scan.
    
    Args:
        domain: The domain URL to scan
        scan_mode: The scan mode (quick, deep, scheduled)
    
    Returns:
        ScanResult object containing scan data
    
    Raises:
        ValueError: If domain is invalid
        ScanError: If scan execution fails
    """
    # Implementation
```

**Error Handling:**
```python
# Use specific exceptions
try:
    result = await scan_service.create_scan(domain)
except ValueError as e:
    logger.error(f"Invalid domain: {e}")
    raise HTTPException(status_code=400, detail=str(e))
except ScanError as e:
    logger.error(f"Scan failed: {e}")
    raise HTTPException(status_code=500, detail="Scan execution failed")
```

### TypeScript/React Code Style

**Formatting:**
- Use [Prettier](https://prettier.io/) for code formatting
- 2 spaces for indentation
- Single quotes for strings
- Semicolons required

**Component Structure:**
```typescript
import React, { useState, useEffect } from 'react';
import { ScanResult } from '@/types';

interface ScanListProps {
  scans: ScanResult[];
  onScanClick: (scanId: string) => void;
}

export const ScanList: React.FC<ScanListProps> = ({ scans, onScanClick }) => {
  const [selectedScan, setSelectedScan] = useState<string | null>(null);

  useEffect(() => {
    // Effect logic
  }, [scans]);

  return (
    <div className="scan-list">
      {/* Component JSX */}
    </div>
  );
};
```

**Hooks:**
- Use custom hooks for reusable logic
- Prefix custom hooks with `use`
- Keep hooks focused and single-purpose

**State Management:**
- Use Zustand for global state
- Use React hooks for local state
- Avoid prop drilling (use context or global state)

### SQL Style

**Formatting:**
```sql
-- Use uppercase for keywords
-- Use snake_case for table and column names
-- Indent subqueries

SELECT
    s.scan_id,
    s.domain,
    COUNT(c.cookie_id) AS cookie_count
FROM scan_results s
LEFT JOIN cookies c ON s.scan_id = c.scan_id
WHERE s.status = 'success'
    AND s.timestamp_utc >= NOW() - INTERVAL '7 days'
GROUP BY s.scan_id, s.domain
ORDER BY s.timestamp_utc DESC;
```

---

## Testing Guidelines

### Test Structure

Organize tests to mirror the source code structure:

```
tests/
├── unit/
│   ├── test_scan_service.py
│   ├── test_analytics.py
│   └── test_notification_service.py
├── integration/
│   ├── test_api_endpoints.py
│   └── test_scan_workflow.py
└── e2e/
    └── test_dashboard_flows.py
```

### Writing Unit Tests

```python
import pytest
from services.scan_service import ScanService

@pytest.fixture
def scan_service():
    """Fixture providing ScanService instance."""
    return ScanService()

def test_create_scan_success(scan_service):
    """Test successful scan creation."""
    # Arrange
    domain = "https://example.com"
    scan_mode = "quick"
    
    # Act
    result = scan_service.create_scan(domain, scan_mode)
    
    # Assert
    assert result.scan_id is not None
    assert result.domain == domain
    assert result.scan_mode == scan_mode

def test_create_scan_invalid_domain(scan_service):
    """Test scan creation with invalid domain."""
    with pytest.raises(ValueError, match="Invalid domain"):
        scan_service.create_scan("not-a-url", "quick")
```

### Writing Integration Tests

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_scan_workflow(client: AsyncClient, db_session):
    """Test complete scan workflow."""
    # Create scan
    response = await client.post(
        "/api/v1/scans",
        json={"domain": "https://example.com", "scan_mode": "quick"}
    )
    assert response.status_code == 201
    scan_id = response.json()["scan_id"]
    
    # Wait for completion (in real test, use polling or mock)
    # ...
    
    # Retrieve results
    response = await client.get(f"/api/v1/scans/{scan_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
```

### Test Coverage

- Aim for 80% code coverage
- Focus on critical paths and edge cases
- Don't test framework code or third-party libraries
- Use mocks sparingly (prefer real implementations in tests)

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_scan_service.py

# Run tests matching pattern
pytest -k "test_scan"

# Run with coverage
pytest --cov=services --cov-report=html

# Run only fast tests (skip slow integration tests)
pytest -m "not slow"
```

---

## Commit Messages

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification.

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks (dependencies, build, etc.)
- `perf`: Performance improvements

### Examples

```bash
# Simple feature
git commit -m "feat: add real-time scan progress streaming"

# Bug fix with scope
git commit -m "fix(api): correct rate limiting calculation"

# Breaking change
git commit -m "feat!: change scan result API response format

BREAKING CHANGE: scan_id field renamed to id"

# With body
git commit -m "refactor(scan): improve cookie categorization logic

- Extract categorization into separate service
- Add caching for IAB GVL lookups
- Improve error handling"
```

### Guidelines

- Use imperative mood ("add" not "added" or "adds")
- Don't capitalize first letter
- No period at the end
- Keep subject line under 72 characters
- Separate subject from body with blank line
- Use body to explain what and why, not how

---

## Pull Request Process

### Before Submitting

1. **Update your branch** with latest main:
   ```bash
   git checkout main
   git pull upstream main
   git checkout your-branch
   git rebase main
   ```

2. **Run all tests** and ensure they pass:
   ```bash
   pytest
   npm test  # For dashboard changes
   ```

3. **Lint your code**:
   ```bash
   black .
   flake8 .
   mypy .
   ```

4. **Update documentation** if needed

5. **Add tests** for new functionality

### PR Template

When creating a PR, fill out the template:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Related Issues
Closes #123

## Changes Made
- Change 1
- Change 2
- Change 3

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Screenshots (if applicable)
[Add screenshots here]

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests added and passing
- [ ] Dependent changes merged
```

### Review Process

1. **Automated Checks**: CI/CD pipeline runs tests and linting
2. **Code Review**: At least one maintainer reviews the code
3. **Feedback**: Address review comments and push updates
4. **Approval**: Maintainer approves the PR
5. **Merge**: Maintainer merges the PR

### Review Guidelines

**For Contributors:**
- Respond to feedback promptly
- Be open to suggestions
- Ask questions if feedback is unclear
- Update PR based on feedback

**For Reviewers:**
- Be respectful and constructive
- Explain reasoning for suggestions
- Approve when satisfied with changes
- Provide clear action items

---

## Documentation

### Code Documentation

- Add docstrings to all public functions and classes
- Include type hints for all parameters and return values
- Document complex algorithms or business logic
- Add inline comments for non-obvious code

### API Documentation

- Update OpenAPI schemas when changing endpoints
- Add examples for request/response bodies
- Document error responses
- Update API_ENDPOINTS_REFERENCE.md

### User Documentation

- Update USER_GUIDE.md for user-facing changes
- Add screenshots for UI changes
- Update troubleshooting section if needed
- Keep examples up to date

### Architecture Documentation

- Update ARCHITECTURE.md for architectural changes
- Document design decisions
- Update diagrams if structure changes
- Keep technology stack section current

---

## Getting Help

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and discussions
- **Slack**: Real-time chat (invite link in README)
- **Email**: maintainers@example.com

### Resources

- **Documentation**: See README.md, ARCHITECTURE.md, USER_GUIDE.md
- **API Docs**: Visit `/api/docs` on running instance
- **Code Examples**: See `examples/` directory
- **Video Tutorials**: [YouTube playlist](https://youtube.com/...)

### Common Questions

**Q: How do I run a single test?**
```bash
pytest tests/unit/test_scan_service.py::test_create_scan_success
```

**Q: How do I debug a failing test?**
```bash
pytest --pdb tests/unit/test_scan_service.py
```

**Q: How do I update database schema?**
```bash
# Create new migration file in database/migrations/
# Name it with next number: 007_your_migration.sql
# Run migrations
python run_migrations.py
```

**Q: How do I add a new API endpoint?**
1. Add route in `api/routers/`
2. Add request/response models
3. Implement handler function
4. Add tests in `tests/integration/`
5. Update API documentation

**Q: How do I add a new notification channel?**
1. Create class in `services/notification_channels.py`
2. Inherit from `NotificationChannel`
3. Implement `send()` method
4. Register in `NotificationService`
5. Add tests

---

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (see LICENSE file).

---

## Recognition

Contributors are recognized in:
- CONTRIBUTORS.md file
- Release notes
- GitHub contributors page

Thank you for contributing to Cookie Scanner Platform! 🎉

---

**Questions?** Open an issue or reach out to maintainers@example.com
