# Contributing to AccessMatrix

AccessMatrix is maintained by **Ubaid Ahmad Bhat**.

Contributions that improve the project are welcome, including:

- bug fixes
- security improvements
- tests
- documentation improvements
- usability improvements
- authorization-testing enhancements
- frontend improvements
- reporting improvements

---

## Development Setup

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

---

## Run AccessMatrix

```bash
uv run accessmatrix gui
```

---

## Run the Demo API

```bash
uv run uvicorn accessmatrix.demo_api.app:app --host 127.0.0.1 --port 9000
```

---

## Required Validation

Before submitting a contribution, run:

```bash
uv run ruff format .
uv run ruff check .
uv run mypy src tests
uv run python -m pytest
```

All checks should pass.

---

## Frontend Changes

Frontend source is located under:

```text
gui/
```

For frontend work:

```bash
cd gui
npm install
npm run build
```

When changing the GUI, ensure the production build used by AccessMatrix is updated appropriately.

---

## Contribution Guidelines

Changes should:

- be focused and understandable
- include appropriate tests
- preserve existing security controls
- avoid weakening safety defaults without clear justification
- document user-visible behavior
- preserve local-first operation unless a design change is explicitly discussed
- avoid unnecessary dependencies

---

## Security-Sensitive Code

Changes involving the following areas require extra care:

- credential handling
- target validation
- DNS handling
- request execution
- redirect behavior
- filesystem paths
- scan evidence
- report generation
- authentication
- authorization
- network policy
- rate limiting

Security-sensitive changes should include regression tests where practical.

---

## Do Not Commit Sensitive Data

Never commit:

- production credentials
- bearer tokens
- API keys
- passwords
- session cookies
- private keys
- customer data
- private OpenAPI specifications
- generated scan evidence
- generated findings
- private reports

Check staged files carefully before committing.

---

## Tests

Tests are located under:

```text
tests/
```

The project uses:

```text
tests/unit/
tests/integration/
```

New functionality should include relevant automated coverage.

---

## Documentation

User-facing functionality should include documentation changes where appropriate.

Important documentation is located under:

```text
docs/
```

---

## Reporting Bugs

Bug reports should include:

- AccessMatrix version
- operating system
- Python version
- uv version
- reproduction steps
- expected result
- actual result
- relevant non-sensitive logs

Do not include credentials or sensitive target data.

---

## Reporting Security Vulnerabilities

Do not publish exploitable AccessMatrix security vulnerabilities as normal public issues.

Follow:

```text
SECURITY.md
```

instead.

---

## Pull Requests

Before opening a pull request:

1. update your branch;
2. run formatting;
3. run linting;
4. run type checking;
5. run the full test suite;
6. review the diff for secrets or local artifacts;
7. update documentation when required.

Keep pull requests focused where practical.

---

## Responsible Use

Contributions must not intentionally turn AccessMatrix into a tool for unauthorized access.

AccessMatrix is intended for legitimate development, defensive security testing, authorized penetration testing, and authorization regression testing.

---

## Maintainer

**Ubaid Ahmad Bhat**

LinkedIn:

https://www.linkedin.com/in/ubaid-ahmad-bhat-a766741b6/
