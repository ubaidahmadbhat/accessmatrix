# AccessMatrix Development Guide

This guide is for developers and contributors working on AccessMatrix itself.

AccessMatrix v0.1.0 uses:

- Python 3.13
- FastAPI
- SQLAlchemy
- Pydantic
- Typer
- React
- TypeScript
- Vite
- uv
- Ruff
- MyPy
- Pytest

---

# Repository Structure

```text
accessmatrix/
â”œâ”€â”€ docs/
â”œâ”€â”€ examples/
â”œâ”€â”€ gui/
â”œâ”€â”€ src/
â”‚   â””â”€â”€ accessmatrix/
â”‚       â”œâ”€â”€ api/
â”‚       â”œâ”€â”€ application/
â”‚       â”œâ”€â”€ audit/
â”‚       â”œâ”€â”€ authorization/
â”‚       â”œâ”€â”€ cli/
â”‚       â”œâ”€â”€ core/
â”‚       â”œâ”€â”€ demo_api/
â”‚       â”œâ”€â”€ execution/
â”‚       â”œâ”€â”€ findings/
â”‚       â”œâ”€â”€ openapi/
â”‚       â”œâ”€â”€ persistence/
â”‚       â”œâ”€â”€ reports/
â”‚       â”œâ”€â”€ resources/
â”‚       â”œâ”€â”€ scanning/
â”‚       â”œâ”€â”€ security/
â”‚       â””â”€â”€ settings/
â”œâ”€â”€ tests/
â”œâ”€â”€ pyproject.toml
â””â”€â”€ uv.lock
```

---

# Development Setup

Clone the repository:

```bash
git clone https://github.com/ubaidahmadbhat/accessmatrix.git
cd accessmatrix
```

Install dependencies:

```bash
uv sync
```

AccessMatrix v0.1.0 requires Python 3.13.

Verify the project environment:

### Windows

```powershell
.\.venv\Scripts\python.exe --version
```

### Linux / macOS

```bash
./.venv/bin/python --version
```

---

# Run AccessMatrix

```bash
uv run accessmatrix gui
```

The GUI is available at:

```text
http://127.0.0.1:8765
```

---

# Run the Demo API

```bash
uv run uvicorn accessmatrix.demo_api.app:app --host 127.0.0.1 --port 9000
```

The demo API is available at:

```text
http://127.0.0.1:9000
```

---

# Python Formatting

Run:

```bash
uv run ruff format .
```

---

# Python Linting

Run:

```bash
uv run ruff check .
```

---

# Static Type Checking

Run:

```bash
uv run mypy src tests
```

---

# Tests

Run:

```bash
uv run python -m pytest
```

This form is preferred because some Windows application-control environments can block generated executable launchers such as `pytest.exe`.

---

# Current Validation Baseline

For AccessMatrix v0.1.0:

```text
Ruff: clean
MyPy: clean
Pytest: 106 passing
Overall coverage: 76%
```

---

# Frontend Development

Frontend source is located under:

```text
gui/
```

Install frontend dependencies:

```bash
cd gui
npm install
```

Run the development frontend:

```bash
npm run dev
```

Build the production frontend:

```bash
npm run build
```

Normal AccessMatrix users do not need Node.js.

The production GUI assets used by the Python application are bundled under:

```text
src/accessmatrix/resources/gui/
```

When modifying the frontend, ensure the final production build is reflected in the bundled GUI resources before release.

---

# Backend Architecture

The backend is organized by responsibility.

## API

```text
src/accessmatrix/api/
```

Contains FastAPI application setup, routes, and API schemas.

## Application

```text
src/accessmatrix/application/
```

Contains application-level services and business orchestration.

## Authorization

```text
src/accessmatrix/authorization/
```

Contains authorization datasets, ownership models, validation, demo seeding, and BOLA planning.

## Execution

```text
src/accessmatrix/execution/
```

Contains controlled request execution, rate limiting, credential-aware execution, and policy enforcement.

## Scanning

```text
src/accessmatrix/scanning/
```

Contains automated BOLA scan execution and scan persistence.

## Findings

```text
src/accessmatrix/findings/
```

Contains durable finding models and storage.

## Reports

```text
src/accessmatrix/reports/
```

Contains report models, rendering, and artifact storage.

## Security

```text
src/accessmatrix/security/
```

Contains security-sensitive target validation logic.

## Settings

```text
src/accessmatrix/settings/
```

Contains persistent application security and execution settings.

## Audit

```text
src/accessmatrix/audit/
```

Contains local audit-event models and persistence.

---

# Development Principles

Changes should preserve the core AccessMatrix design principles:

- local-first operation
- explicit authorization before active testing
- credential separation
- bounded evidence collection
- defensive local storage
- target validation
- controlled request execution
- durable findings
- clear security limitations

---

# Request Execution

New scanners should use the controlled request-executor abstraction.

Security-sensitive code should not bypass:

- target validation
- configured network policy
- timeouts
- request-size limits
- response-size limits
- rate limiting
- concurrency controls

---

# Evidence Handling

Do not store unlimited target responses.

Evidence should remain bounded and should avoid intentionally storing credentials.

Remember that even bounded evidence can contain sensitive application data.

---

# Adding Tests

New behavior should include appropriate tests.

Tests are located under:

```text
tests/
```

Current test categories include:

```text
tests/integration/
tests/unit/
```

Prefer regression tests for previously fixed security-sensitive behavior.

---

# Before Submitting Changes

Run:

```bash
uv run ruff format .
uv run ruff check .
uv run mypy src tests
uv run python -m pytest
```

All checks should pass.

---

# Do Not Commit Sensitive Data

Never commit:

- real bearer tokens
- passwords
- API keys
- session cookies
- private keys
- customer OpenAPI specifications
- generated scan evidence
- generated findings
- private security reports
- customer data

---

# Security-Sensitive Changes

Changes involving:

- credentials
- network validation
- target execution
- evidence storage
- report generation
- filesystem paths
- authentication
- authorization logic

should receive additional review and regression testing.

See:

```text
SECURITY.md
```

for vulnerability-reporting guidance.

---

# Release Checklist

Before creating a release:

```text
Ruff passes
MyPy passes
Pytest passes
Frontend build is current
No secrets are tracked
No runtime evidence is tracked
README is current
Documentation is current
Version is correct
CHANGELOG is current
CI configuration is valid
```

---

# Maintainer

**Ubaid Ahmad Bhat**

LinkedIn:

https://www.linkedin.com/in/ubaid-ahmad-bhat-a766741b6/
