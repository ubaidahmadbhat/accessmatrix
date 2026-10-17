# AccessMatrix Demo Guide

This guide walks through the bundled AccessMatrix demonstration environment from start to finish.

The demo includes a deliberately vulnerable local invoice API designed to demonstrate **Broken Object Level Authorization (BOLA)**.

It allows a new user to understand:

- what AccessMatrix does
- how identities are modelled
- how object ownership is represented
- how BOLA test cases are generated
- how scans work
- how findings are created
- how evidence is recorded
- how reports are generated

The demo runs entirely on the local machine.

---

# What the Demo Is Designed to Show

The central security problem is simple.

Suppose two normal users exist:

```text
Alice
Bob
```

Alice owns her own invoices.

Bob owns his own invoices.

Correct behavior should look like:

```text
Alice -> Alice's invoice -> ALLOWED

Bob -> Bob's invoice -> ALLOWED
```

But cross-owner access should be rejected:

```text
Alice -> Bob's invoice -> DENIED

Bob -> Alice's invoice -> DENIED
```

The bundled demo intentionally fails this authorization check.

That allows AccessMatrix to detect and report the vulnerability.

---

# Demo Architecture

The demonstration environment contains two separate processes:

```text
+-----------------------+
|      AccessMatrix     |
|  http://127.0.0.1:8765
+-----------+-----------+
            |
            | authorization tests
            v
+-----------------------+
| Vulnerable Invoice API|
|  http://127.0.0.1:9000
+-----------------------+
```

The AccessMatrix GUI and backend run locally.

The deliberately vulnerable invoice API also runs locally on a separate port.

---

# Demo Files

The bundled OpenAPI specification is:

```text
examples/invoice-demo-openapi.yaml
```

The deliberately vulnerable API implementation is located under:

```text
src/accessmatrix/demo_api/
```

---

# Demo Credentials

The demo uses three intentionally fake security contexts:

```text
Alice
Bob
Administrator
```

The corresponding demonstration tokens are:

```text
Alice:
demo-alice-token

Bob:
demo-bob-token

Administrator:
demo-admin-token
```

These values are deliberately public and protect no real system.

Never copy this practice when using real credentials.

---

# Before Starting

From the AccessMatrix repository root:

```powershell
Set-Location C:\Dev\accessmatrix
```

AccessMatrix should already be installed with:

```powershell
uv sync
```

The project environment should use Python 3.13.

On Windows:

```powershell
.\.venv\Scripts\python.exe --version
```

Expected:

```text
Python 3.13.x
```

---

# Terminal 1 — Start the Vulnerable Invoice API

Open a new PowerShell terminal.

Run:

```powershell
Set-Location C:\Dev\accessmatrix

uv run uvicorn accessmatrix.demo_api.app:app `
  --host 127.0.0.1 `
  --port 9000
```

Leave this terminal running.

The demo API should now be available at:

```text
http://127.0.0.1:9000
```

---

# Terminal 2 — Configure Demo Credentials

Open another PowerShell terminal.

Run:

```powershell
Set-Location C:\Dev\accessmatrix

$env:ACCESSMATRIX_ALICE_TOKEN = "demo-alice-token"
$env:ACCESSMATRIX_BOB_TOKEN = "demo-bob-token"
$env:ACCESSMATRIX_ADMIN_TOKEN = "demo-admin-token"
```

Then start AccessMatrix:

```powershell
uv run accessmatrix gui
```

Open:

```text
http://127.0.0.1:8765
```

in your browser.

---

# Linux / macOS Demo Credentials

For a Unix-style shell:

```bash
export ACCESSMATRIX_ALICE_TOKEN="demo-alice-token"
export ACCESSMATRIX_BOB_TOKEN="demo-bob-token"
export ACCESSMATRIX_ADMIN_TOKEN="demo-admin-token"

uv run accessmatrix gui
```

---

# Step 1 — Create the Demo Project

Create a new project.

Use a descriptive name such as:

```text
Local Invoice Demo
```

Use this base URL:

```text
http://127.0.0.1:9000
```

This tells AccessMatrix that the project target is the bundled local demonstration API.

---

# Step 2 — Import the Demo OpenAPI Specification

Import:

```text
examples/invoice-demo-openapi.yaml
```

The bundled specification describes the local invoice API.

After import, AccessMatrix should discover the API operations defined in the document.

The current demo specification contains multiple operations, including the vulnerable invoice lookup used for BOLA testing.

---

# Step 3 — Understand the Vulnerable Operation

The main BOLA demonstration revolves around an operation conceptually equivalent to:

```text
GET /invoices/{invoice_id}
```

A legitimate request might be:

```text
Alice -> Alice-owned invoice
```

A cross-owner probe might be:

```text
Alice -> Bob-owned invoice
```

The demonstration endpoint intentionally allows access it should normally deny.

---

# Step 4 — Configure Demo Identities

The demo uses:

```text
Alice
Bob
Administrator
```

For BOLA testing, Alice and Bob are the most important identities because they represent separate normal users with separate owned objects.

The administrator exists as an additional demonstration security context.

---

# Step 5 — Credential References

Configure the identities so they resolve the previously created environment variables.

Conceptually:

```text
Alice
  -> ACCESSMATRIX_ALICE_TOKEN

Bob
  -> ACCESSMATRIX_BOB_TOKEN

Administrator
  -> ACCESSMATRIX_ADMIN_TOKEN
```

The actual secret values remain in the environment rather than being copied into the authorization dataset.

---

# Step 6 — Seed or Configure the Demo Authorization Dataset

AccessMatrix includes support for creating the bundled demonstration ownership data.

Use the demo-seeding functionality available in the authorization dataset interface.

The current demo dataset is designed around:

```text
2 resource ownership groups
6 objects
8 authorization cases
4 ready BOLA probes
```

The important result is that the dataset validates successfully and produces four executable BOLA probes.

---

# Step 7 — Understand the Ownership Model

The demonstration objects are split between Alice and Bob.

Conceptually:

```text
Alice
├── Alice-owned object
├── Alice-owned object
└── Alice-owned object

Bob
├── Bob-owned object
├── Bob-owned object
└── Bob-owned object
```

The exact identifiers are stored in the demonstration authorization dataset.

AccessMatrix uses this ownership information to generate cross-owner tests.

---

# Step 8 — Validate the Authorization Dataset

Run dataset validation.

The dataset should be valid before scanning.

A valid dataset tells AccessMatrix that:

- the identities exist
- the objects exist
- ownership is meaningful
- the relevant operation exists
- the generated BOLA cases can be prepared

Do not continue with a broken dataset.

---

# Step 9 — Review the BOLA Plan

The demo should produce four ready BOLA probes.

Conceptually:

```text
Alice baseline
      |
      v
Alice-owned object

Alice probe
      |
      v
Bob-owned object
```

and:

```text
Bob baseline
      |
      v
Bob-owned object

Bob probe
      |
      v
Alice-owned object
```

Multiple object combinations produce the complete four-case demo plan.

---

# Why AccessMatrix Runs a Baseline First

A cross-owner request only becomes meaningful if the selected identity is working correctly.

For example:

```text
Alice -> Alice's invoice
```

should succeed first.

This helps confirm:

- Alice's credentials are valid
- the target API is reachable
- the object exists
- the endpoint works
- the request structure is usable

Only after that does the cross-owner test become useful.

---

# Step 10 — Confirm Network Settings

The demo uses:

```text
127.0.0.1
```

which is a loopback address.

The appropriate AccessMatrix network mode for the demo is:

```text
public_and_loopback
```

If the network mode is:

```text
public_only
```

AccessMatrix should reject the demo target.

That behavior is intentional.

---

# Optional Network-Safety Test

You can verify the safety policy manually.

Change the AccessMatrix network mode to:

```text
public_only
```

Then try to use the local demo.

The loopback target should be denied.

Restore the mode to:

```text
public_and_loopback
```

before continuing.

---

# Step 11 — Run the BOLA Scan

Start the BOLA scan from the project.

AccessMatrix requires explicit authorization acknowledgement before active scanning.

The bundled local demo is specifically intended for this authorized test.

Confirm that the target is still:

```text
http://127.0.0.1:9000
```

before running the scan.

---

# Expected Scan Result

The deliberately vulnerable demo is expected to produce:

```text
Status: completed

Total cases:     4
Findings:        4
Passed:          0
Inconclusive:    0
Blocked:         0
```

The current regression suite also expects the four vulnerability findings to have:

```text
Severity:   high
Confidence: high
```

---

# What Happened During the Scan?

A simplified example:

```text
Alice requests Alice-owned invoice
            |
            v
HTTP success
            |
            v
Baseline confirmed
            |
            v
Alice requests Bob-owned invoice
            |
            v
Vulnerable API returns success
            |
            v
Foreign object is exposed
            |
            v
BOLA finding
```

The process is repeated for the generated cases.

---

# Step 12 — Review the Scan

Open the completed scan.

Review:

```text
scan status
total cases
finding count
pass count
inconclusive count
blocked count
case explanations
stored evidence
```

The demo should show four findings.

---

# Step 13 — Review Findings

Open the Findings section.

AccessMatrix stores findings independently from raw scan history.

Review each finding for:

- affected operation
- identity
- baseline object
- probe object
- severity
- confidence
- observed behavior
- evidence
- current finding state

The demo findings represent intentional vulnerabilities.

---

# Step 14 — Understand the Finding

The central problem is:

```text
Valid identity
     +
Valid foreign object ID
     +
Missing ownership enforcement
     =
Unauthorized object access
```

This is why authentication alone is not sufficient.

The API knows who Alice is.

The security failure occurs because the API does not correctly verify whether Alice is allowed to access Bob's object.

---

# Step 15 — Generate a Report

Open the reporting section.

Generate a report.

For a first test, use either:

```text
HTML
```

or:

```text
Markdown
```

Confirm that:

```text
report generation succeeds
report appears in history
preview works
download works
```

---

# Other Report Formats

AccessMatrix also supports:

```text
JSON
SARIF 2.1.0
JUnit XML
```

These formats are useful for automation and CI/CD integrations.

---

# Step 16 — Inspect Evidence

Evidence exists to explain why a case was classified.

AccessMatrix intentionally limits evidence collection using configured boundaries such as:

```text
response excerpt size
response header storage
maximum scan size
maximum report size
```

Remember that real API evidence may contain sensitive data.

---

# Step 17 — Understand Durable Findings

Raw scan evidence can eventually be removed according to retention settings.

However, AccessMatrix stores durable findings separately.

Conceptually:

```text
Raw Scan
   |
   +------> Evidence
   |
   +------> Durable Finding
```

Later:

```text
Raw Scan removed by retention
         |
         v
Durable finding remains
```

This supports regression-testing workflows.

---

# Step 18 — Try Scan Retention

The default configuration retains the latest:

```text
50
```

raw scans.

This setting can be adjusted within the supported range.

Retention exists to control evidence accumulation while keeping finding history separate.

---

# Step 19 — Generate Additional Reports

Try the remaining report formats to understand the different outputs.

Recommended learning sequence:

```text
HTML
Markdown
JSON
SARIF
JUnit XML
```

---

# Step 20 — Stop the Demo

When finished, return to the terminal running the invoice API and press:

```text
Ctrl+C
```

Then stop AccessMatrix in its own terminal using:

```text
Ctrl+C
```

---

# Do Not Expose the Demo Publicly

The demonstration API is intentionally vulnerable.

It should remain bound to:

```text
127.0.0.1
```

Do not deliberately expose it to:

```text
0.0.0.0
```

or publish it directly to the Internet.

It exists only for local learning, testing, and regression validation.

---

# Common Demo Problems

## AccessMatrix cannot connect to the demo

Confirm Terminal 1 is still running:

```text
http://127.0.0.1:9000
```

---

## Demo target is blocked

Check network mode.

For the demo use:

```text
public_and_loopback
```

---

## Credentials are unavailable

Make sure the environment variables were defined in the same terminal environment used to start AccessMatrix.

PowerShell:

```powershell
$env:ACCESSMATRIX_ALICE_TOKEN
$env:ACCESSMATRIX_BOB_TOKEN
$env:ACCESSMATRIX_ADMIN_TOKEN
```

Do not use commands like this with real secrets when the terminal output may be recorded or shared.

---

## Dataset does not validate

Confirm the demo dataset has been seeded or configured correctly.

The expected demo model should produce:

```text
4 ready BOLA probes
```

---

## Scan produces blocked cases

Review the case explanation.

Possible causes include:

```text
credential unavailable
target blocked
demo API stopped
dataset mismatch
operation unavailable
```

---

## Scan does not produce four findings

Confirm:

```text
the bundled vulnerable API is running
the correct OpenAPI document was imported
the demo authorization dataset is in use
Alice and Bob credentials resolve correctly
the target base URL is 127.0.0.1:9000
network mode permits loopback
```

---

# What You Should Understand After the Demo

After completing this walkthrough, you should understand the complete AccessMatrix flow:

```text
API definition
     +
identities
     +
credentials
     +
object ownership
     |
     v
authorization dataset
     |
     v
BOLA test plan
     |
     v
controlled execution
     |
     v
findings + evidence
     |
     v
report
```

You are now ready to read:

```text
docs/concepts.md
docs/user-guide.md
docs/security-model.md
```

before configuring AccessMatrix against your own authorized API.