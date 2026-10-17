# AccessMatrix Concepts and Terminology

This document explains the core concepts used throughout AccessMatrix.

Understanding these terms makes the platform easier to configure and helps users interpret authorization test results correctly.

---

# Authentication

Authentication answers:

```text
Who are you?
```

Examples include:

- username and password
- bearer token
- API key
- session cookie
- client certificate
- custom authentication header

Authentication establishes identity.

It does not automatically determine which objects that identity is allowed to access.

---

# Authorization

Authorization answers:

```text
What are you allowed to do?
```

Examples:

```text
Can Alice read invoice 1001?

Can Bob access Alice's document?

Can a support user modify another customer's account?

Can Tenant A access Tenant B's records?

Can a normal user call an administrator-only function?
```

AccessMatrix is primarily concerned with testing authorization behavior.

---

# Authentication vs Authorization

These controls are related but different.

Example:

```text
Bob presents a valid token
        |
        v
Authentication succeeds
        |
        v
API knows the requester is Bob
```

The API must still decide:

```text
Is Bob allowed to access invoice 1001?
```

If invoice `1001` belongs to Alice and the API returns it to Bob, authentication worked but authorization failed.

---

# BOLA

BOLA means:

```text
Broken Object Level Authorization
```

It occurs when an application fails to correctly verify whether the requesting identity is authorized to access a specific object.

Example endpoint:

```text
GET /invoices/{invoice_id}
```

Suppose:

```text
invoice-1001 -> Alice
invoice-2001 -> Bob
```

A legitimate request might be:

```text
Alice -> invoice-1001
```

A cross-owner request would be:

```text
Alice -> invoice-2001
```

If Alice can retrieve Bob's protected invoice, the API may contain a BOLA vulnerability.

---

# Object Reference

An object reference is a value used to identify a particular application object.

Examples include:

```text
invoice_id
user_id
order_id
document_id
account_id
transaction_id
UUID
numeric database ID
slug
```

BOLA vulnerabilities often involve changing or substituting these references.

---

# Project

A project is the primary AccessMatrix assessment scope.

A project groups information related to one target API.

This can include:

```text
base URL
OpenAPI specification
identities
credential references
authorization dataset
scan history
findings
reports
```

Example project names:

```text
Customer Portal - Staging
Billing API - QA
Internal CRM Authorization Test
```

---

# Base URL

The base URL identifies the target API environment.

Examples:

```text
https://api.example.com

https://staging-api.example.com

http://127.0.0.1:9000
```

AccessMatrix combines this base URL with imported API operations when creating requests.

The target must also satisfy the configured network-safety policy.

---

# OpenAPI Specification

OpenAPI is a machine-readable description of an HTTP API.

It commonly defines:

- paths
- HTTP methods
- parameters
- schemas
- request bodies
- response structures
- security definitions

AccessMatrix uses OpenAPI to discover operations that may participate in authorization testing.

OpenAPI normally does **not** contain enough information to understand business ownership.

That is why AccessMatrix also uses an authorization dataset.

---

# Operation

An operation represents one callable API action.

Examples:

```text
GET /invoices/{invoice_id}

GET /users/{user_id}

PATCH /documents/{document_id}

DELETE /orders/{order_id}
```

An authorization resource can be associated with one of these imported operations.

---

# HTTP Method

An HTTP method describes the type of action requested.

Common methods include:

```text
GET
POST
PUT
PATCH
DELETE
```

Authorization failures can affect both read and write operations.

For example:

```text
GET another user's object
```

may expose private data.

But:

```text
DELETE another user's object
```

could be even more damaging.

AccessMatrix v0.1.0 is intentionally conservative about controlled execution and safety.

---

# Identity

An identity represents one authenticated security context used during testing.

Examples:

```text
Alice

Bob

Administrator

Support Agent

Tenant A User

Tenant B User
```

An identity is more than a display name.

It represents the authentication and authorization context used when AccessMatrix sends requests.

---

# Privileged Identity

A privileged identity has broader permissions than a normal user.

Examples:

```text
Administrator
Support Agent
Manager
Service Account
```

These identities must be modelled carefully.

An administrator accessing another user's object may be legitimate and therefore should not automatically be treated as a vulnerability.

---

# Credential

A credential is authentication material used to prove identity to the target API.

Examples:

```text
Bearer token
API key
Password
Session cookie
Custom authentication header
```

Credentials are sensitive and must be protected.

---

# Credential Reference

A credential reference tells AccessMatrix where authentication material should be obtained.

The goal is to avoid repeatedly storing the actual secret inside application configuration.

Conceptually:

```text
Identity:
Alice

Credential source:
Environment variable

Reference:
ACCESSMATRIX_ALICE_TOKEN
```

The project can reference the environment variable without storing the token value directly in the authorization dataset.

---

# Environment Variable Credential

An environment variable can hold a credential value for the AccessMatrix process.

Example:

```text
ACCESSMATRIX_ALICE_TOKEN
```

The value exists in the process environment.

Environment variables are convenient but still sensitive.

Do not expose them in:

- screenshots
- shell history
- logs
- public issue reports
- source code
- Git commits

---

# Keyring Credential

AccessMatrix can work with supported operating-system credential storage through keyring mechanisms.

This can provide better separation between application configuration and secret values.

Availability depends on the operating system and configured keyring backend.

---

# Resource

A resource represents a category of business object.

Examples:

```text
invoice
order
document
account
transaction
ticket
customer
project
```

A resource type defines what kind of object is being authorization tested.

---

# Object

An object is one concrete instance of a resource.

For the resource:

```text
invoice
```

objects might include:

```text
invoice-1001
invoice-1002
invoice-2001
invoice-2002
```

AccessMatrix needs known objects so it can create controlled authorization tests.

---

# Owner

An owner is the identity expected to legitimately control or access an object according to the test model.

Example:

```text
invoice-1001 -> Alice

invoice-2001 -> Bob
```

Ownership is central to BOLA testing.

---

# Object Ownership

Object ownership describes the expected relationship between identities and objects.

Example:

```text
Alice
├── invoice-1001
└── invoice-1002

Bob
├── invoice-2001
└── invoice-2002
```

AccessMatrix uses this information to distinguish legitimate requests from cross-owner requests.

---

# Authorization Dataset

The authorization dataset contains the business context required for testing.

It can connect:

```text
identities
resources
objects
owners
operations
parameters
expected denial behavior
evidence fields
```

OpenAPI describes how to call the API.

The authorization dataset describes how AccessMatrix should reason about authorization expectations.

---

# Dataset Validation

Dataset validation checks whether the configured authorization model is internally usable.

Validation may detect problems such as:

```text
missing identity
missing object
unknown owner
unknown operation
invalid operation binding
unusable test combination
```

Validation should be performed before scanning.

---

# Operation Binding

An operation binding connects a resource to an imported API operation.

Example:

```text
Resource:
invoice

Operation:
GET /invoices/{invoice_id}
```

This tells AccessMatrix which operation should be used when testing invoice authorization.

---

# Object Identifier Parameter

The object identifier parameter tells AccessMatrix where the object ID belongs in the request.

For example:

```text
GET /invoices/{invoice_id}
```

The parameter is:

```text
invoice_id
```

AccessMatrix can substitute different known object IDs when building baseline and cross-owner requests.

---

# Expected Denial Status

An expected denial status represents an HTTP response that the application may legitimately use when authorization is rejected.

Common examples:

```text
401
403
404
```

These have different meanings:

```text
401 Unauthorized
```

usually indicates authentication is missing or invalid.

```text
403 Forbidden
```

usually indicates the identity is authenticated but access is denied.

```text
404 Not Found
```

may be used intentionally to hide the existence of another user's object.

The correct expected statuses depend on the target application.

---

# Baseline Request

A baseline request uses an identity to access an object that identity is expected to own.

Example:

```text
Alice -> Alice's invoice
```

The baseline helps verify that:

- the credential works
- the API is reachable
- the object exists
- the operation is functioning
- the identity has expected legitimate access

A useful baseline improves the reliability of the cross-owner test.

---

# Cross-Owner Probe

A cross-owner probe uses an authenticated identity to request an object owned by another identity.

Example:

```text
Alice -> Bob's invoice
```

This is the central BOLA test.

The target API should enforce the expected authorization boundary.

---

# BOLA Test Case

A BOLA test case combines:

```text
identity
owned baseline object
foreign probe object
API operation
expected denial behavior
```

A case conceptually looks like:

```text
Identity:
Alice

Baseline:
invoice-1001 owned by Alice

Probe:
invoice-2001 owned by Bob

Operation:
GET /invoices/{invoice_id}

Expected:
authorization denial
```

---

# BOLA Test Plan

The BOLA test plan is the collection of test cases generated from the authorization dataset.

Not every possible ownership combination necessarily becomes an executable case.

Cases must satisfy the required configuration and safety conditions.

---

# Ready Probe

A ready probe is a generated authorization test that contains the information required for execution.

For the bundled demo, the expected plan contains:

```text
4 ready BOLA probes
```

---

# Controlled Execution

Controlled execution is the request execution layer used by AccessMatrix.

It applies configured safety controls before and during API requests.

Examples include:

```text
target validation
timeouts
request limits
response limits
rate limiting
parallel request limits
redirect restrictions
```

---

# Target Validation

Target validation examines where AccessMatrix is about to send a request.

Checks may include:

```text
URL structure
protocol
hostname
DNS resolution
IP address class
network access policy
```

This reduces the chance of unintentionally targeting disallowed network locations.

---

# Network Access Mode

Network access mode determines which categories of target addresses are permitted.

Current modes include:

```text
public_only
public_and_loopback
private_networks
```

The correct mode depends on the environment being tested.

---

# Loopback

Loopback refers to the local machine.

Typical addresses include:

```text
127.0.0.1
::1
```

The bundled AccessMatrix demo uses loopback.

---

# Private Network

Private networks are address ranges typically used inside organizations or home networks.

Examples include ranges such as:

```text
10.0.0.0/8

172.16.0.0/12

192.168.0.0/16
```

Testing private APIs should only be done when authorized.

---

# Rate Limit

The AccessMatrix execution rate limit controls how many requests can be sent during a configured time window.

The default is:

```text
30 requests per 60 seconds
```

This is an application safety control.

The authorized rules of engagement may require an even lower request rate.

---

# Maximum Parallel Requests

This setting controls how many requests AccessMatrix can execute concurrently.

The default is:

```text
4
```

Higher concurrency can increase load on the target system.

---

# Request Timeout

The request timeout limits how long AccessMatrix waits for a target request.

The default is:

```text
10 seconds
```

---

# Request Size Limit

AccessMatrix limits the size of request bodies.

The default maximum request body is:

```text
1 MiB
```

This helps prevent unexpectedly large generated requests.

---

# Response Size Limit

AccessMatrix limits captured response size.

The default maximum response size is:

```text
4 MiB
```

This helps bound memory and evidence handling.

---

# Evidence

Evidence is the controlled information stored to help explain an observed test result.

Evidence can include:

```text
HTTP status
response metadata
selected response headers
bounded response body excerpts
content hashes
```

Evidence may contain sensitive target information.

Protect it accordingly.

---

# Body Excerpt

Rather than storing unlimited response content, AccessMatrix can retain a bounded excerpt.

The default excerpt limit is:

```text
16 KiB
```

This reduces uncontrolled evidence growth.

---

# Finding

A finding represents an authorization issue identified during testing.

A finding can include information such as:

```text
affected operation
identity
resource type
baseline object
probe object
severity
confidence
evidence
status
```

---

# Durable Finding

Findings are stored separately from raw scan evidence.

This means a finding can remain available after older raw scans are removed through retention.

Conceptually:

```text
Scan
 |
 +--> Evidence
 |
 +--> Finding
```

Later:

```text
Old scan pruned
      |
      v
Finding remains
```

---

# Severity

Severity represents the estimated security impact of a finding.

Severity is not the same as confidence.

An issue can be highly certain but relatively low impact, or highly impactful with lower confidence.

---

# Confidence

Confidence represents how strongly the observed behavior supports the finding classification.

Confidence should be interpreted together with:

```text
evidence
business context
expected authorization policy
```

---

# Finding Status

Findings can move through lifecycle states.

Current states include:

```text
open
resolved
false_positive
accepted_risk
```

---

# Open

The finding is currently active and has not been resolved or otherwise dispositioned.

---

# Resolved

The issue has been remediated or otherwise closed according to the security workflow.

A regression test should ideally confirm the fix.

---

# False Positive

The observed behavior does not represent a real authorization vulnerability.

Use this only after reviewing the application's intended behavior.

---

# Accepted Risk

The issue is known but intentionally accepted according to the organization's security or risk-management process.

---

# Scan

A scan is one execution of generated authorization test cases.

It records:

```text
start time
completion time
case outcomes
findings
evidence
summary counts
status
```

---

# Scan Status

A scan may have states such as:

```text
completed
partial
failed
```

A completed scan does not necessarily mean every test passed.

It means execution completed according to the scan engine's rules.

---

# Pass

A pass means the specific cross-owner request was rejected according to expected authorization behavior.

A pass does not prove the entire endpoint or application is secure.

---

# Finding Outcome

A finding outcome means the cross-owner request succeeded in a manner that indicates an authorization weakness.

Human analysis should still confirm the business impact.

---

# Inconclusive

An inconclusive result means AccessMatrix could not classify the observed behavior confidently as either expected denial or successful unauthorized access.

Possible causes include:

```text
unexpected HTTP status
application error
ambiguous response
unusual business behavior
```

Analyst review is required.

---

# Blocked

Blocked means AccessMatrix could not execute the test case.

Possible reasons include:

```text
missing credential
invalid target
network safety restriction
missing object
invalid test configuration
request failure
```

Blocked is not the same as secure.

---

# Scan Retention

Scan retention controls how many recent raw scan records AccessMatrix keeps.

The default is:

```text
50
```

Retention helps control local evidence growth.

---

# Report

A report is an exported representation of AccessMatrix findings and project results.

Supported formats include:

```text
JSON
Markdown
HTML
SARIF 2.1.0
JUnit XML
```

---

# HTML Report

HTML is useful for human-readable review.

---

# Markdown Report

Markdown is useful for:

```text
documentation
Git repositories
issue trackers
security reports
```

---

# JSON Report

JSON is useful for:

```text
automation
custom processing
integration
archiving
```

---

# SARIF

SARIF means:

```text
Static Analysis Results Interchange Format
```

AccessMatrix can generate SARIF 2.1.0 output for integration with compatible security and development tooling.

---

# JUnit XML

JUnit XML is commonly used by CI/CD systems to represent test results.

AccessMatrix can export authorization findings in a format suitable for those workflows.

---

# Audit Event

An audit event is a local record of relevant AccessMatrix activity.

Audit events improve traceability for security-sensitive operations.

---

# Audit Retention

AccessMatrix limits how long and how many audit events are kept.

Current default values include:

```text
Retention:
180 days

Maximum events:
10,000
```

---

# Local-First

Local-first means AccessMatrix is designed so that core project and security data can remain on the tester's machine.

It does not require a hosted AccessMatrix cloud service for normal operation.

This provides greater control over sensitive assessment data.

However, it also means the user is responsible for securing the local system.

---

# Regression Testing

Regression testing means repeating a known security test after software changes.

Example:

```text
Before fix:

Alice -> Bob's invoice -> allowed
```

After remediation:

```text
Alice -> Bob's invoice -> denied
```

AccessMatrix is intended to make this type of authorization verification repeatable.

---

# False Sense of Security

No automated tool can prove that an application has no authorization vulnerabilities.

A clean AccessMatrix scan means:

```text
the configured authorization cases did not produce findings
```

It does **not** mean:

```text
the entire application is authorization-secure
```

Coverage depends on:

- identities
- ownership data
- operations
- test cases
- application state
- business logic

---

# Responsible Use

AccessMatrix should only be used against systems:

```text
you own
you administer
or you have explicit authorization to test
```

Authorization from the AccessMatrix interface does not grant legal authorization.

The operator remains responsible for scope and permission.

---

# Next Reading

After understanding these concepts, continue with:

```text
docs/user-guide.md
docs/security-model.md
docs/troubleshooting.md
```

For a practical walkthrough, use:

```text
docs/demo-guide.md
```