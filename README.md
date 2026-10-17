# AccessMatrix

**Local-first API authorization regression testing.**

AccessMatrix is an open-source security testing platform designed to help developers, application security teams, penetration testers, and security engineers identify authorization weaknesses in APIs.

Its first release focuses on **Broken Object Level Authorization (BOLA)** testing: determining whether one authenticated identity can access an object that belongs to another identity.

AccessMatrix imports an OpenAPI specification, models application identities and object ownership, generates controlled authorization test cases, executes them against an authorized target, records durable findings and evidence, and produces security reports in multiple formats.

AccessMatrix is designed to run locally so that API definitions, testing configuration, findings, and evidence can remain under the user's control.

---

## Why AccessMatrix?

Authentication and authorization are different security controls.

An API can correctly verify that a user is logged in while still failing to verify whether that user is permitted to access a particular object.

For example:

```text
GET /api/invoices/1001
```

Suppose invoice `1001` belongs to Alice.

Alice accessing it may be completely legitimate.

But what happens if Bob changes the identifier:

```text
GET /api/invoices/1001
Authorization: Bearer <bob-token>
```

If the API returns Alice's invoice to Bob, authentication succeeded but object-level authorization failed.

That is the type of behavior AccessMatrix is designed to detect systematically.

Instead of manually changing IDs and repeating requests across users, AccessMatrix models:

```text
Identity
   +
Owned Objects
   +
Foreign Objects
   +
API Operations
        |
        v
Authorization Test Plan
        |
        v
Controlled Requests
        |
        v
Expected vs Actual Access
        |
        v
Findings + Evidence + Reports
```

---

## Current Scope

AccessMatrix `v0.1.0` focuses primarily on:

- API authorization regression testing
- Broken Object Level Authorization (BOLA)
- identity-aware request execution
- object ownership modelling
- controlled cross-owner probes
- durable findings
- local evidence storage
- report generation
- network and execution safety controls
- audit events

AccessMatrix is **not** intended to replace a complete penetration test, SAST platform, DAST scanner, or API security program.

Future authorization-testing capabilities may expand into additional authorization classes such as function-level and property-level authorization testing.

---

## Who Is It For?

AccessMatrix is intended for:

- Application Security engineers
- API developers
- penetration testers
- security consultants
- security researchers
- QA and security testing teams
- DevSecOps teams
- engineering teams maintaining sensitive APIs

You should have authorization to test the API you configure as a target.

---

# How AccessMatrix Works

A normal AccessMatrix workflow looks like this:

```text
1. Create Project
       |
       v
2. Import OpenAPI Specification
       |
       v
3. Define Identities
       |
       v
4. Configure Credential References
       |
       v
5. Define Resources and Object Ownership
       |
       v
6. Validate Authorization Dataset
       |
       v
7. Generate BOLA Test Plan
       |
       v
8. Run Controlled Authorization Scan
       |
       v
9. Review Findings and Evidence
       |
       v
10. Generate Report
```

The important concept is that AccessMatrix needs to understand **who owns what**.

For example:

```text
Alice
├── invoice-1001
├── invoice-1002
└── invoice-1003

Bob
├── invoice-2001
├── invoice-2002
└── invoice-2003
```

AccessMatrix can then generate controlled probes such as:

```text
Alice -> invoice-2001
Alice -> invoice-2002

Bob -> invoice-1001
Bob -> invoice-1002
```

A successful cross-owner response can indicate broken object-level authorization.

---

# Key Features

## OpenAPI-based projects

Import an OpenAPI specification and allow AccessMatrix to discover API operations that can participate in authorization testing.

## Multiple identities

Model different application users, roles, tenants, or security contexts.

Examples:

```text
Alice
Bob
Administrator
Tenant A User
Tenant B User
Support Agent
Manager
```

## Credential references

Credentials are resolved separately from project configuration.

This reduces the need to embed secrets directly inside project definitions, reports, or findings.

Supported credential patterns include mechanisms such as bearer tokens, API keys, basic authentication, cookies, and custom headers where configured.

## Authorization datasets

Define:

- resource types
- object identifiers
- ownership
- identity relationships
- operation bindings
- response fields used for evidence

The dataset is validated before scanning.

## Automated BOLA planning

AccessMatrix uses ownership information to build cross-owner authorization probes.

## Controlled execution

Requests are executed through a safety-aware execution layer with configurable controls such as:

- network access policy
- request timeout
- request-size limits
- response-size limits
- request rate limiting
- parallel-request limits
- redirect controls
- target validation

## Durable findings

Detected authorization weaknesses are stored independently from individual raw scan files.

This allows findings to remain available even when old scan evidence is removed through retention policies.

## Evidence controls

Evidence collection can be limited by:

- response excerpt size
- response-header collection
- scan storage limits
- report storage limits
- scan retention count

## Reporting

AccessMatrix supports:

- JSON
- Markdown
- HTML
- SARIF 2.1.0
- JUnit XML

Different formats serve different workflows:

| Format | Typical use |
|---|---|
| HTML | Human-readable assessment |
| Markdown | Documentation and issue tracking |
| JSON | Automation and data processing |
| SARIF | Security tooling and CI integrations |
| JUnit XML | CI/CD test-result workflows |

## Local audit trail

Important application activity can be recorded as local audit events.

---

# Local-First Design

AccessMatrix is designed around a local-first operating model.

Project data, authorization datasets, findings, scan evidence, reports, settings, and audit information are stored locally by the application.

This is useful when testing:

- internal APIs
- sensitive APIs
- development environments
- regulated environments
- security research systems

The local-first model does **not** automatically make every deployment secure. Users remain responsible for protecting the machine on which AccessMatrix runs and for managing credentials appropriately.

---

# Requirements

For the current `v0.1.0` release:

- Python **3.13**
- `uv`
- a modern web browser

The project currently declares:

```text
Python >=3.13,<3.14
```

The GUI is already bundled with AccessMatrix for normal use. Node.js is only required when modifying or rebuilding the React frontend.

---

# Installation

## 1. Install Git

Verify:

```bash
git --version
```

## 2. Install Python 3.13

Verify:

```bash
python --version
```

You should be using Python 3.13.

## 3. Install uv

See the official uv installation documentation:

https://docs.astral.sh/uv/getting-started/installation/

Verify:

```bash
uv --version
```

## 4. Clone AccessMatrix

Once the repository has been cloned:

```bash
cd accessmatrix
```

## 5. Install dependencies

```bash
uv sync
```

## 6. Start AccessMatrix

```bash
uv run accessmatrix gui
```

AccessMatrix starts the local application server and GUI.

By default, open:

```text
http://127.0.0.1:8765
```

in your browser.

---

# Quick Start

After opening the GUI:

```text
Create Project
      |
      v
Import OpenAPI
      |
      v
Configure Identities
      |
      v
Configure Credential References
      |
      v
Create Authorization Dataset
      |
      v
Validate Dataset
      |
      v
Review Generated BOLA Plan
      |
      v
Run Scan
      |
      v
Review Findings
      |
      v
Generate Report
```

For your first experience, the included demo environment is strongly recommended.

---

# Included BOLA Demo

AccessMatrix includes a deliberately vulnerable local invoice API for learning and validation.

The demo is designed to illustrate the difference between:

```text
Authentication
```

and:

```text
Object-level authorization
```

The bundled OpenAPI file is:

```text
examples/invoice-demo-openapi.yaml
```

## Start the demo API

Open a separate terminal:

```bash
uv run uvicorn accessmatrix.demo_api.app:app --host 127.0.0.1 --port 9000
```

The local demo API runs at:

```text
http://127.0.0.1:9000
```

## Demo identities

The demo includes example security contexts for:

```text
Alice
Bob
Administrator
```

For the bundled development demo, environment variables can be configured before starting AccessMatrix.

### PowerShell

```powershell
$env:ACCESSMATRIX_ALICE_TOKEN = "demo-alice-token"
$env:ACCESSMATRIX_BOB_TOKEN = "demo-bob-token"
$env:ACCESSMATRIX_ADMIN_TOKEN = "demo-admin-token"

uv run accessmatrix gui
```

### Linux / macOS shell

```bash
export ACCESSMATRIX_ALICE_TOKEN="demo-alice-token"
export ACCESSMATRIX_BOB_TOKEN="demo-bob-token"
export ACCESSMATRIX_ADMIN_TOKEN="demo-admin-token"

uv run accessmatrix gui
```

These tokens are intentionally non-secret demo values.

Do not copy this pattern using real production secrets in source code or Git.

## Expected demo result

The deliberately vulnerable demo is designed to produce:

```text
Status: completed
Total cases: 4
Findings: 4
Passed: 0
Inconclusive: 0
Blocked: 0
```

The successful cross-owner accesses demonstrate BOLA behavior.

---

# Using AccessMatrix With Your Own API

A real assessment generally requires four things:

### An OpenAPI specification

AccessMatrix needs an API definition describing operations and paths.

### Two or more identities

For meaningful authorization comparison, the tool needs different security contexts.

For example:

```text
customer-alice
customer-bob
```

or:

```text
tenant-a-user
tenant-b-user
```

### Valid credentials

Credentials should belong to accounts you are authorized to use for testing.

### Object ownership information

AccessMatrix needs to know which objects belong to which identities.

For example:

```text
Object: invoice-1001
Owner: alice

Object: invoice-2001
Owner: bob
```

Without ownership information, AccessMatrix cannot reliably determine which cross-user requests constitute authorization tests.

---

# What Is BOLA?

**Broken Object Level Authorization** occurs when an API exposes an object reference but fails to verify that the requesting identity is allowed to access the referenced object.

Typical object identifiers include:

- invoice IDs
- account IDs
- order IDs
- document IDs
- user IDs
- customer IDs
- transaction IDs
- project IDs
- tenant records
- UUIDs

Consider:

```http
GET /orders/10001
Authorization: Bearer <alice-token>
```

If order `10001` belongs to Alice, the request is expected.

Now consider:

```http
GET /orders/20005
Authorization: Bearer <alice-token>
```

If order `20005` belongs to Bob but Alice receives the object anyway, the application may have a BOLA vulnerability.

---

# Example Use Cases

## E-commerce

```text
Customer A -> Customer B's order
```

## Financial applications

```text
Account A -> Account B's transaction
```

## Multi-tenant SaaS

```text
Tenant A -> Tenant B's record
```

## Document platforms

```text
User A -> User B's private document
```

## Internal enterprise applications

```text
Employee A -> record owned by another department/user
```

The exact security impact depends on the application, resource, and authorization model.

---

# Understanding Scan Outcomes

A BOLA test case can produce several outcomes.

## Pass

The cross-owner request was rejected with an expected authorization-denial response.

## Finding

The cross-owner request succeeded in a way that indicates an authorization weakness.

## Inconclusive

The response could not be classified confidently as either expected authorization denial or successful unauthorized access.

## Blocked

AccessMatrix could not execute the case because of configuration, safety controls, missing information, credentials, or another prerequisite.

---

# Findings

AccessMatrix stores findings separately from raw scan history.

A finding can track lifecycle states such as:

```text
open
resolved
false_positive
accepted_risk
```

This allows the platform to act as an authorization regression-testing system rather than only a one-time request runner.

---

# Settings and Safety

AccessMatrix provides configurable safety controls.

Important areas include:

## Network policy

Modes include:

```text
public_only
public_and_loopback
private_networks
```

Choose the mode appropriate for the environment you are authorized to test.

## DNS and target validation

Targets can be resolved and classified before execution.

## Request limits

Controls exist for:

- request body size
- response body size
- request timeout
- request rate
- parallel requests

## Evidence limits

Controls exist for:

- body excerpts
- response headers
- maximum scan size
- maximum report size
- raw scan retention

---

# Security Model

AccessMatrix is itself a security-sensitive application.

Several principles are used throughout the project:

- secrets should be referenced rather than copied into evidence
- reports should not intentionally contain credentials
- evidence size is bounded
- requests are rate limited
- redirects are controlled
- targets are validated
- scan execution requires explicit authorization acknowledgement
- destructive evidence operations require confirmation
- audit events are stored locally
- generated report paths and filenames are validated
- storage operations use bounded and defensive file handling

No security control should be treated as a substitute for operating AccessMatrix on a trusted machine.

---

# Important Network-Safety Limitation

Hostname validation includes DNS pre-resolution and address classification.

However, pre-resolving a hostname is **not equivalent to pinning the actual outbound connection to the validated IP address**.

The underlying HTTP client may resolve the hostname again when establishing the connection.

Therefore the current release should not be described as completely resistant to all DNS-rebinding scenarios.

Users assessing hostile or untrusted targets should account for this limitation.

---

# Responsible Use

AccessMatrix is a security testing tool.

Use it only against:

- systems you own
- systems you administer
- systems for which you have explicit authorization to perform security testing

Do not use AccessMatrix to access data or systems without authorization.

You are responsible for complying with applicable laws, contracts, rules of engagement, and organizational policies.

---

# Data and Credentials

Do not commit real credentials to Git.

Recommended approaches include:

- environment variables
- operating-system credential stores
- supported keyring mechanisms

Before publishing or sharing an AccessMatrix workspace, inspect it for sensitive:

```text
tokens
API keys
passwords
cookies
private keys
reports
scan evidence
internal API specifications
customer information
```

The repository `.gitignore` excludes common local and secret-containing files, but `.gitignore` is not a security boundary.

---

# Architecture Overview

```text
                    +----------------------+
                    |      React GUI       |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    |       FastAPI        |
                    +----------+-----------+
                               |
           +-------------------+-------------------+
           |                   |                   |
           v                   v                   v
     Project Layer       Identity Layer      Settings Layer
           |                   |                   |
           +-------------------+-------------------+
                               |
                               v
                    +----------------------+
                    | Authorization Model  |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    |   BOLA Test Planner  |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    | Controlled Executor  |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    |      Target API      |
                    +----------------------+

                               |
                               v
                    +----------------------+
                    |     Scan Results     |
                    +----------+-----------+
                               |
                    +----------+-----------+
                    |                      |
                    v                      v
              Durable Findings          Evidence
                    |                      |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    |       Reports        |
                    +----------------------+
```

---

# Project Structure

```text
accessmatrix/
├── examples/
├── gui/
├── src/
│   └── accessmatrix/
│       ├── api/
│       ├── application/
│       ├── audit/
│       ├── authorization/
│       ├── cli/
│       ├── core/
│       ├── demo_api/
│       ├── execution/
│       ├── findings/
│       ├── openapi/
│       ├── persistence/
│       ├── reports/
│       ├── resources/
│       ├── scanning/
│       ├── security/
│       └── settings/
├── tests/
├── docs/
├── pyproject.toml
└── README.md
```

---

# Development

Clone the repository and install all dependencies:

```bash
uv sync
```

Run Ruff:

```bash
uv run ruff check .
```

Run MyPy:

```bash
uv run mypy src tests
```

Run tests:

```bash
uv run python -m pytest
```

The `v0.1.0` pre-release validation baseline is:

```text
106 tests passing
Ruff clean
MyPy clean
76% overall test coverage
```

---

# Frontend Development

The source frontend is located under:

```text
gui/
```

The normal AccessMatrix user does not need Node.js when using the bundled GUI.

Developers modifying the frontend can use the package scripts defined in `gui/package.json`.

For example:

```bash
cd gui
npm install
npm run build
```

The built application used by AccessMatrix is packaged into the Python application's GUI resources.

---

# Documentation

Detailed documentation is provided under `docs/`.

Planned/maintained guides include:

- Installation
- Getting Started
- Complete User Guide
- Demo Guide
- Concepts and Terminology
- Architecture
- Security Model
- Reporting
- Troubleshooting
- Development Guide

---

# Known Limitations of v0.1.0

The initial release intentionally has a focused scope.

Notable limitations include:

- primary automated authorization scanner currently focuses on BOLA
- ownership data must be supplied or seeded
- authorization semantics still require human understanding of the target application
- DNS pre-validation does not provide socket-level DNS pinning
- special-purpose network environments may require policy tuning
- a successful HTTP response can require analyst review to confirm business impact
- AccessMatrix does not prove the absence of authorization vulnerabilities

These limitations are documented rather than hidden because security tools should communicate what they can and cannot establish.

---

# Roadmap

Potential future directions include:

- Broken Function Level Authorization testing
- Broken Object Property Level Authorization testing
- broader authorization-policy modelling
- additional CI/CD workflows
- stronger target connection pinning
- expanded finding correlation
- additional authorization regression strategies

Roadmap items are not promises and may change as the project evolves.

---

# Testing Status

Current release validation:

```text
Ruff       PASS
MyPy       PASS
Pytest     106 PASS
Coverage   76%
```

---

# Version

Current version:

```text
0.1.0
```

This is the first public development release of AccessMatrix.

---

# Author

**Ubaid Ahmad Bhat**

LinkedIn:

https://www.linkedin.com/in/ubaid-ahmad-bhat-a766741b6/

---

# Contributing

Contributions, bug reports, documentation improvements, and security-focused discussions are welcome.

See:

```text
CONTRIBUTING.md
```

for the project contribution process.

---

# Security Issues

Do not publish sensitive vulnerability details about AccessMatrix installations or real target systems in public issues.

Security reporting guidance is provided in:

```text
SECURITY.md
```

---

# License

AccessMatrix is intended to be released as open-source software.

See the repository `LICENSE` file for the applicable license terms.

---

## Final Note

AccessMatrix is built around a simple security question:

> A user is authenticated — but are they actually authorized to access this object?

The purpose of the project is to make answering that question repeatable, testable, reviewable, and suitable for regression testing.