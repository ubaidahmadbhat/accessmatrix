# AccessMatrix User Guide

AccessMatrix v0.1.0 is a local-first API authorization regression-testing platform focused primarily on **Broken Object Level Authorization (BOLA)**.

This guide explains the normal operational lifecycle when testing an API you are authorized to assess.

---

# Typical Workflow

```text
Create Project
    ↓
Import OpenAPI
    ↓
Create Identities
    ↓
Configure Credential References
    ↓
Define Resources and Objects
    ↓
Assign Object Ownership
    ↓
Validate Authorization Dataset
    ↓
Review BOLA Test Plan
    ↓
Run Controlled Scan
    ↓
Review Findings
    ↓
Generate Reports
    ↓
Retest After Remediation
```

---

# 1. Create a Project

A project represents one API assessment scope.

Examples:

```text
Billing API - Staging
Customer Portal - QA
Internal CRM - Authorization Testing
```

A project groups together:

- target base URL
- OpenAPI specification
- identities
- credential references
- authorization dataset
- scan history
- findings
- reports

Use separate projects for substantially different APIs or environments.

---

# 2. Configure the Target

The project base URL identifies the API environment.

Examples:

```text
https://api.example.com
https://staging-api.example.com
http://127.0.0.1:9000
```

The target must satisfy the configured AccessMatrix network policy before requests can be executed.

---

# 3. Import OpenAPI

Import the OpenAPI specification describing the target API.

AccessMatrix uses OpenAPI to discover operations such as:

```text
GET /invoices/{invoice_id}
GET /orders/{order_id}
GET /users/{user_id}
PATCH /documents/{document_id}
```

Review the discovered operations before configuring authorization testing.

---

# 4. Create Identities

An identity represents one authenticated security context.

Examples:

```text
Alice
Bob
Administrator
Support Agent
Tenant A User
Tenant B User
```

For BOLA testing, two normal users with clearly separate ownership are often the easiest model to interpret.

Privileged users must be handled carefully because wider access may be intentional.

---

# 5. Configure Credential References

Each protected identity requires authentication material.

AccessMatrix supports separating the credential reference from the secret value itself.

Examples of authentication patterns include:

- bearer tokens
- API keys
- basic authentication
- cookies
- custom headers

A conceptual configuration might be:

```text
Identity:
Alice

Credential source:
Environment variable

Reference:
ACCESSMATRIX_ALICE_TOKEN
```

The secret value should not be copied into project documentation or Git.

---

# 6. Define a Resource

A resource represents a protected business-object type.

Examples:

```text
invoice
order
account
document
transaction
customer
ticket
project
```

For:

```text
GET /invoices/{invoice_id}
```

the resource type may simply be:

```text
invoice
```

---

# 7. Add Test Objects

Add known objects that belong to your authorized test accounts.

Example:

```text
invoice-1001
invoice-1002
invoice-2001
invoice-2002
```

Use known test objects rather than uncontrolled identifier enumeration.

---

# 8. Assign Ownership

Tell AccessMatrix which identity owns each object.

Example:

```text
invoice-1001 -> Alice
invoice-1002 -> Alice

invoice-2001 -> Bob
invoice-2002 -> Bob
```

Correct ownership data is critical.

Incorrect ownership information can produce misleading results.

---

# 9. Bind the Resource to an Operation

Associate the resource with the relevant imported API operation.

Example:

```text
Resource:
invoice

Operation:
GET /invoices/{invoice_id}

Object identifier parameter:
invoice_id
```

This allows AccessMatrix to substitute known object identifiers into the request.

---

# 10. Configure Expected Denial Behavior

Different applications represent authorization denial differently.

Common responses include:

```text
401 Unauthorized
403 Forbidden
404 Not Found
```

Some APIs intentionally return `404` for another user's object so that object existence is not disclosed.

Configure the expected behavior according to the application being tested.

---

# 11. Validate the Authorization Dataset

Run dataset validation before scanning.

Validation can detect issues such as:

- unknown identities
- missing objects
- invalid ownership
- missing operations
- invalid bindings
- unusable authorization cases

Do not continue until the dataset is meaningful.

---

# 12. Review the BOLA Test Plan

AccessMatrix generates controlled cases from the ownership model.

Example:

```text
Alice baseline:
GET /invoices/invoice-1001

Alice cross-owner probe:
GET /invoices/invoice-2001
```

Another case may be:

```text
Bob baseline:
GET /invoices/invoice-2001

Bob cross-owner probe:
GET /invoices/invoice-1001
```

---

# 13. Understand the Baseline

A baseline request verifies normal access.

Example:

```text
Alice -> Alice-owned invoice
```

A successful baseline helps establish that:

- the credential works
- the endpoint is reachable
- the object exists
- the request structure is valid
- the identity has legitimate access

This provides context for the cross-owner probe.

---

# 14. Understand the Cross-Owner Probe

A cross-owner probe uses the same identity but requests an object owned by somebody else.

Example:

```text
Alice -> Bob-owned invoice
```

The target API should enforce its authorization policy.

If Alice receives Bob's protected object, AccessMatrix may produce a BOLA finding.

---

# 15. Review Safety Settings

Before active testing, review the application settings.

Important controls include:

- network access mode
- DNS resolution
- request timeout
- request-size limit
- response-size limit
- rate limit
- maximum parallel requests
- evidence excerpt size
- maximum scan size
- maximum report size
- scan retention

Do not weaken safety settings merely to make a request execute.

Understand why the request was blocked first.

---

# 16. Run the Scan

BOLA scanning is active security testing.

AccessMatrix therefore requires explicit authorization acknowledgement before execution.

Before running a scan, confirm:

- correct project
- correct target URL
- authorized environment
- valid test identities
- accurate ownership data
- acceptable request volume

---

# 17. Scan Outcomes

A case can produce several outcomes.

## Pass

The cross-owner request was rejected using expected authorization behavior.

Example:

```text
403 Forbidden
```

A pass applies only to that specific configured case.

---

## Finding

The cross-owner request succeeded in a way that indicates an authorization weakness.

Example:

```text
Alice requests Bob's invoice
        ↓
HTTP 200
        ↓
Bob's invoice is returned
        ↓
BOLA finding
```

---

## Inconclusive

The observed behavior cannot be classified reliably.

Possible causes include:

- unexpected HTTP status
- application errors
- unusual response structure
- ambiguous business behavior

These cases require analyst review.

---

## Blocked

The test could not execute.

Possible causes include:

- missing credential
- target policy restriction
- invalid configuration
- missing object
- request failure
- safety-control rejection

Blocked does **not** mean secure.

---

# 18. Review Findings

For every finding, inspect:

- affected operation
- identity
- baseline object
- probe object
- HTTP result
- severity
- confidence
- evidence
- explanation
- current finding state

Always compare the result with the application's actual business rules.

---

# 19. Severity and Confidence

Severity and confidence are separate concepts.

## Severity

Severity describes the estimated security impact.

## Confidence

Confidence describes how strongly the observed behavior supports the finding classification.

A high-confidence finding may still have different business impact depending on the resource involved.

---

# 20. Finding States

AccessMatrix supports finding states including:

```text
open
resolved
false_positive
accepted_risk
```

## Open

The issue is still active.

## Resolved

The issue has been remediated or closed.

## False Positive

The observed behavior does not violate the intended authorization model.

## Accepted Risk

The issue is known but intentionally accepted according to the organization's risk-management process.

---

# 21. Generate Reports

AccessMatrix supports:

```text
HTML
Markdown
JSON
SARIF 2.1.0
JUnit XML
```

Typical usage:

| Format | Use |
|---|---|
| HTML | Human-readable assessment |
| Markdown | Documentation and issue tracking |
| JSON | Automation |
| SARIF | Security tooling |
| JUnit XML | CI/CD test-result workflows |

Reports are security-sensitive artifacts and should be protected accordingly.

---

# 22. Retest After Remediation

AccessMatrix is designed for regression testing.

Before fix:

```text
Alice -> Bob-owned object -> allowed
```

After remediation:

```text
Alice -> Bob-owned object -> denied
```

Repeat the same authorization model to confirm the issue does not return.

---

# 23. Scan Retention

Raw scan history is subject to retention settings.

The default keeps the latest:

```text
50 scans
```

Durable findings are stored separately so that vulnerability history can remain available after old scan evidence is pruned.

---

# 24. Audit Events

AccessMatrix can maintain local audit events for relevant application activity.

Audit information should also be treated as security-sensitive local data.

---

# Recommended Testing Practice

Prefer:

- dedicated test identities
- dedicated test objects
- staging or QA environments
- explicit written authorization
- conservative request rates
- clearly defined ownership

Avoid:

- uncontrolled identifier enumeration
- production disruption
- testing outside scope
- unnecessary evidence collection
- destructive operations unless explicitly authorized

---

# What a Clean Scan Means

A scan with no findings means:

```text
The configured authorization cases did not produce findings.
```

It does **not** mean:

```text
The application has no authorization vulnerabilities.
```

Coverage depends on:

- identities
- objects
- ownership information
- imported operations
- application state
- business logic
- configured test cases

---

# Recommended Reading

For installation:

```text
docs/installation.md
```

For first-time onboarding:

```text
docs/getting-started.md
```

For the local demonstration:

```text
docs/demo-guide.md
```

For terminology:

```text
docs/concepts.md
```

For security behavior:

```text
docs/security-model.md
```

---

# Responsible Use

Only use AccessMatrix against systems:

- you own
- you administer
- or you have explicit authorization to security test

The operator remains responsible for scope, legal authorization, rules of engagement, and handling of collected security evidence.