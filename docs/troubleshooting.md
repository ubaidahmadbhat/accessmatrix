# AccessMatrix Troubleshooting

This guide covers common AccessMatrix installation, runtime, scanning, and reporting problems.

---

# AccessMatrix Does Not Start

From the repository root, run:

```powershell
uv run accessmatrix gui
```

If startup fails, verify the project environment.

Windows:

```powershell
.\.venv\Scripts\python.exe --version
```

AccessMatrix v0.1.0 expects:

```text
Python 3.13.x
```

Then verify uv:

```powershell
uv --version
```

If dependencies may be missing:

```powershell
uv sync
```

---

# Windows Reports accessmatrix.exe Is In Use

When AccessMatrix is already running, Windows may lock:

```text
.venv\Scripts\accessmatrix.exe
```

This can cause an error similar to:

```text
The process cannot access the file because it is being used by another process.
```

Stop the running AccessMatrix process before running an operation that needs to rebuild or reinstall the package.

Then run:

```powershell
uv sync
```

and start AccessMatrix again.

---

# GUI Does Not Open

The default GUI URL is:

```text
http://127.0.0.1:8765
```

Open it manually in a browser.

Confirm the AccessMatrix terminal is still running.

---

# Port 8765 Is Already In Use

Another process may already be using the GUI port.

Stop the conflicting application before starting AccessMatrix again.

---

# Demo API Does Not Start

The demo uses:

```text
http://127.0.0.1:9000
```

Start it with:

```powershell
uv run uvicorn accessmatrix.demo_api.app:app --host 127.0.0.1 --port 9000
```

If port 9000 is already occupied, identify and stop the conflicting process.

---

# Demo Target Is Blocked

The demo uses loopback networking.

The network access mode should permit loopback.

Use:

```text
public_and_loopback
```

The mode:

```text
public_only
```

should reject the local demo target.

That behavior is intentional.

---

# OpenAPI Import Fails

Check that the document:

- is valid YAML or JSON
- is a valid OpenAPI specification
- contains callable paths
- can be read by AccessMatrix

The bundled demo specification is:

```text
examples/invoice-demo-openapi.yaml
```

---

# No Operations Are Discovered

Confirm the OpenAPI specification contains operations under its `paths` section.

For example:

```text
GET /invoices/{invoice_id}
```

A document containing only schema definitions may not provide usable operations.

---

# Credential Is Unavailable

Check the configured credential source and reference.

For environment-variable credentials, confirm the variable exists in the same environment that starts AccessMatrix.

PowerShell example:

```powershell
$env:ACCESSMATRIX_ALICE_TOKEN
```

Do not print real secrets into terminals that may be logged, recorded, or shared.

---

# Authorization Dataset Does Not Validate

Typical causes include:

- missing identity
- unknown owner
- missing object
- invalid resource
- missing operation
- invalid operation binding
- insufficient information for a BOLA case

Fix validation issues before running scans.

---

# No BOLA Cases Are Generated

BOLA testing requires meaningful ownership separation.

Example:

```text
Alice owns object A
Bob owns object B
```

If all configured objects have the same owner, there may be no useful cross-owner comparison.

Also confirm that the correct API operation is bound to the resource.

---

# Baseline Fails

A failed baseline usually means AccessMatrix cannot confirm expected legitimate access.

Check:

- credential validity
- object identifier
- object ownership
- target URL
- required headers
- required parameters
- current target data

Do not interpret the cross-owner probe until the baseline is meaningful.

---

# Scan Is Blocked

A blocked case can result from:

- missing credentials
- target-validation failure
- network policy
- missing object data
- invalid case configuration
- request failure
- execution safety control

Read the case explanation before changing settings.

Blocked does not mean secure.

---

# Scan Is Inconclusive

An inconclusive result means AccessMatrix could not classify the response confidently.

Review:

- HTTP status
- response body
- expected denial statuses
- object existence
- identity permissions
- application behavior

Human analysis may be required.

---

# Scan Finds More Issues Than Expected

Verify the ownership dataset.

Incorrect ownership assignments can produce misleading findings.

Also consider whether the identity intentionally has broader access.

Examples include:

```text
Administrator
Support Agent
Manager
Service Account
```

---

# Scan Finds Nothing

Possible explanations include:

- authorization is correctly enforced
- relevant endpoint was not configured
- ownership data is incomplete
- selected identities do not provide meaningful separation
- object identifiers are incorrect
- another authorization vulnerability class is present

No findings does not prove the application is secure.

---

# Report Generation Fails

Check:

- report size limit
- scan availability
- finding data
- filesystem permissions
- available disk space

The default maximum report size is:

```text
32 MiB
```

---

# Historical Scan Becomes Unreadable

If the configured maximum scan size is lowered below the size of an existing stored scan, that historical artifact may no longer be readable under the new limit.

Review evidence settings before significantly lowering storage limits.

---

# Rate Limiting Blocks Requests

The default rate limit is:

```text
30 requests per 60 seconds
```

Wait for the rate-limit window to clear or use an authorized configuration appropriate to the target.

Do not increase the rate beyond the approved testing scope.

---

# DNS Resolution Fails

Possible causes include:

- invalid hostname
- DNS unavailable
- timeout
- resolver failure
- excessive returned addresses

Confirm the hostname resolves correctly before changing network policy.

---

# Private Target Is Rejected

The selected network mode may not permit private addresses.

Authorized internal testing may require:

```text
private_networks
```

Use this only for targets you are permitted to assess.

---

# Frontend Changes Are Not Visible

Normal AccessMatrix execution uses bundled production GUI assets.

Developers changing files under:

```text
gui/
```

must rebuild the frontend and update the bundled GUI resources used by the Python application.

---

# Pytest Launcher Is Blocked on Windows

Some Windows application-control environments may block the generated `pytest.exe` launcher.

Use:

```powershell
uv run python -m pytest
```

instead of:

```powershell
uv run pytest
```

This is the recommended project test command.

---

# Full Project Validation

Run:

```powershell
uv run ruff check .
uv run mypy src tests
uv run python -m pytest
```

The AccessMatrix v0.1.0 pre-release validation baseline is:

```text
Ruff: clean
MyPy: clean
Pytest: 106 passing
Overall coverage: 76%
```

---

# Reporting Bugs

Useful information includes:

- AccessMatrix version
- operating system
- Python version
- uv version
- error message
- steps to reproduce
- whether the bundled demo reproduces the issue

Do not include:

- real tokens
- passwords
- cookies
- API keys
- private keys
- sensitive customer data
- private response evidence

Security vulnerabilities affecting AccessMatrix itself should follow the process in:

```text
SECURITY.md
```