# Getting Started with AccessMatrix

This guide walks through the normal AccessMatrix workflow after installation.

If AccessMatrix is not installed yet, start with:

```text
docs/installation.md
```

AccessMatrix v0.1.0 is designed primarily for **API authorization regression testing**, with the first automated scanner focused on **Broken Object Level Authorization (BOLA)**.

---

# What Problem Does AccessMatrix Solve?

APIs commonly authenticate users correctly but still make mistakes when deciding which objects those users may access.

Authentication answers:

```text
Who are you?
```

Authorization answers:

```text
What are you allowed to access?
```

Consider two users:

```text
Alice
Bob
```

Alice owns:

```text
invoice-1001
```

Bob owns:

```text
invoice-2001
```

The API should normally allow:

```text
Alice -> invoice-1001
Bob   -> invoice-2001
```

But it should reject:

```text
Alice -> invoice-2001
Bob   -> invoice-1001
```

If a user can successfully access another user's protected object, the API may contain a Broken Object Level Authorization vulnerability.

AccessMatrix helps make these checks structured, repeatable, and suitable for regression testing.

---

# The AccessMatrix Workflow

A typical assessment follows this sequence:

```text
Create a Project
       |
       v
Import OpenAPI
       |
       v
Create Identities
       |
       v
Configure Credentials
       |
       v
Define Resources and Ownership
       |
       v
Validate Authorization Dataset
       |
       v
Generate BOLA Test Plan
       |
       v
Run Controlled Scan
       |
       v
Review Findings and Evidence
       |
       v
Generate Reports
       |
       v
Retest After Remediation
```

Each stage adds information AccessMatrix needs to understand the expected authorization boundary.

---

# Before You Begin

Only test APIs that you are authorized to assess.

Before creating a real project, know:

- which API is in scope
- which environment is approved
- which user accounts can be used
- which objects belong to those users
- which API operations access those objects
- what authorization behavior is expected

Whenever possible, use controlled test accounts and non-production data.

---

# 1. Start AccessMatrix

From the repository root:

```bash
uv run accessmatrix gui
```

Open:

```text
http://127.0.0.1:8765
```

AccessMatrix runs locally.

---

# 2. Create a Project

A project represents one API authorization-testing scope.

Examples:

```text
Customer Portal - Staging
Billing API - QA
Internal CRM - Authorization Testing
```

A project groups together:

- target API information
- OpenAPI definition
- identities
- authorization dataset
- scan history
- findings
- reports

Use a separate project when working with a different API or substantially different environment.

---

# 3. Configure the Target Base URL

The base URL tells AccessMatrix where the API is located.

Examples:

```text
https://api.example.com
https://staging-api.example.com
http://127.0.0.1:9000
```

The bundled demonstration API uses:

```text
http://127.0.0.1:9000
```

AccessMatrix validates targets according to the configured network-safety policy before controlled execution.

---

# 4. Import an OpenAPI Specification

AccessMatrix uses OpenAPI to discover callable API operations.

Example operations might include:

```text
GET /users/{user_id}
GET /invoices/{invoice_id}
GET /orders/{order_id}
PATCH /documents/{document_id}
```

Import the OpenAPI specification belonging to the API you are authorized to test.

For the bundled demo, use:

```text
examples/invoice-demo-openapi.yaml
```

After import, review the discovered operations.

---

# 5. Create Identities

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

For BOLA testing, two normal users with different owned objects are often the clearest starting point.

For example:

```text
Alice
  owns Alice's invoices

Bob
  owns Bob's invoices
```

Be careful when using administrators or privileged accounts.

A privileged identity may legitimately have access to objects belonging to other users, which changes the expected authorization model.

---

# 6. Configure Credentials

Most protected APIs require authentication.

AccessMatrix identities can reference credential sources rather than storing the secret repeatedly inside project data.

Authentication patterns may include:

- bearer tokens
- API keys
- basic authentication
- cookies
- custom headers

A conceptual configuration might be:

```text
Identity:
Alice

Authentication:
Bearer token

Credential source:
Environment variable

Reference:
ACCESSMATRIX_ALICE_TOKEN
```

The actual token remains outside the authorization dataset.

---

# Why Credential References Matter

Security-testing projects can easily contain sensitive information.

Separating credential references from secret values reduces the chance of accidentally copying credentials into:

- reports
- findings
- documentation
- Git commits
- screenshots
- exported configuration

AccessMatrix should still be run on a trusted machine because the application must be able to access credentials when executing authenticated requests.

---

# 7. Define a Resource

A resource represents the type of business object being protected.

Examples:

```text
invoice
order
document
account
transaction
customer
ticket
project
```

Suppose the endpoint is:

```text
GET /invoices/{invoice_id}
```

The resource type could be:

```text
invoice
```

---

# 8. Add Objects

Now identify real test objects belonging to the identities.

Example:

```text
invoice-1001
invoice-1002
invoice-2001
invoice-2002
```

Use known test objects rather than randomly enumerating identifiers.

AccessMatrix is designed around controlled authorization regression testing, not uncontrolled object discovery.

---

# 9. Assign Object Ownership

Ownership tells AccessMatrix which identity should legitimately access which object.

Example:

```text
invoice-1001 -> Alice
invoice-1002 -> Alice

invoice-2001 -> Bob
invoice-2002 -> Bob
```

This information is essential.

OpenAPI describes the technical API structure, but it normally does not explain business ownership.

AccessMatrix needs the ownership model to determine what constitutes a cross-owner authorization test.

---

# 10. Bind the Resource to an API Operation

AccessMatrix must know which operation accesses the protected resource.

Example:

```text
Resource:
invoice

Operation:
GET /invoices/{invoice_id}
```

The object identifier is then inserted into the appropriate request parameter.

Conceptually:

```text
invoice-1001
       |
       v
GET /invoices/invoice-1001
```

---

# 11. Configure Expected Authorization Denials

Different APIs represent authorization denial differently.

Common responses include:

```text
401 Unauthorized
403 Forbidden
404 Not Found
```

Some APIs intentionally return `404` when a user requests another user's object so that object existence is not disclosed.

Configure the expected behavior according to the API you are testing.

---

# 12. Configure Useful Evidence Fields

When appropriate, AccessMatrix can compare selected response fields to help interpret the returned object.

Examples might include:

```text
id
owner_id
customer_id
tenant_id
account_id
```

Only configure fields that are useful for understanding authorization behavior.

Avoid collecting more response data than necessary.

---

# 13. Validate the Authorization Dataset

Before scanning, validate the authorization dataset.

Validation checks that the configured model is usable.

Possible issues include:

- unknown identities
- invalid ownership references
- missing objects
- missing resources
- invalid operation mappings
- unusable BOLA cases

Do not proceed merely because the configuration was saved.

A valid dataset is a prerequisite for meaningful automated testing.

---

# 14. Review the BOLA Test Plan

After validation, AccessMatrix can generate BOLA probes.

Consider:

```text
Alice owns invoice-1001
Bob owns invoice-2001
```

A generated test may conceptually contain:

```text
Baseline:
Alice -> invoice-1001

Probe:
Alice -> invoice-2001
```

Another may contain:

```text
Baseline:
Bob -> invoice-2001

Probe:
Bob -> invoice-1001
```

The baseline and probe serve different purposes.

---

# What Is a Baseline?

A baseline request verifies expected legitimate access.

Example:

```text
Alice -> Alice's invoice
```

A successful baseline helps establish that:

- Alice's credentials work
- the endpoint is reachable
- the object exists
- the request structure is correct
- Alice has normal access to her own object

Without a usable baseline, interpretation of the cross-owner request may become unreliable.

---

# What Is a Cross-Owner Probe?

A cross-owner probe uses the same authenticated identity but requests an object belonging to another identity.

Example:

```text
Alice -> Bob's invoice
```

The API should apply its authorization rules.

If the API returns Bob's protected object to Alice, AccessMatrix may create a BOLA finding.

---

# 15. Review Safety Settings

Before active testing, review application settings.

Important controls include:

- network access mode
- DNS resolution
- request timeout
- request-body limit
- response-body limit
- rate limit
- maximum parallel requests
- evidence excerpt size
- scan size limit
- report size limit
- scan retention

The default configuration is intentionally conservative.

---

# Network Access Modes

AccessMatrix supports policies including:

```text
public_only
public_and_loopback
private_networks
```

The correct setting depends on the authorized target.

For the bundled local demo:

```text
public_and_loopback
```

is appropriate.

If:

```text
public_only
```

is selected, the local `127.0.0.1` demo should be rejected.

---

# 16. Run the BOLA Scan

BOLA scanning is active security testing.

AccessMatrix therefore requires explicit authorization acknowledgement before execution.

Confirm:

- the correct project is selected
- the target URL is correct
- the target is authorized
- identities are test accounts you may use
- scan volume is permitted
- ownership data is correct

Then run the scan.

---

# What Happens During a Scan?

At a high level:

```text
Load validated BOLA case
        |
        v
Resolve selected identity
        |
        v
Execute owned-object baseline
        |
        v
Confirm usable baseline
        |
        v
Execute foreign-object probe
        |
        v
Interpret target response
        |
        v
Record outcome and bounded evidence
```

The process repeats for the selected test cases.

---

# 17. Understand Scan Outcomes

Each test case can result in one of several outcomes.

## Pass

The API rejected the cross-owner request using expected authorization behavior.

Example:

```text
403 Forbidden
```

A pass means this particular authorization case behaved as expected.

It does not prove the entire API has no authorization vulnerabilities.

---

## Finding

The cross-owner request succeeded in a manner indicating an authorization weakness.

Example:

```text
Alice requests Bob's invoice
        |
        v
HTTP 200
        |
        v
Bob's invoice returned
        |
        v
BOLA finding
```

---

## Inconclusive

The target returned behavior that AccessMatrix could not classify reliably.

Examples:

- unexpected status
- application error
- unusual response structure
- ambiguous business behavior

These cases require human review.

---

## Blocked

The test could not execute.

Potential reasons include:

- missing credential
- invalid target
- safety-policy rejection
- missing data
- request failure
- invalid test prerequisite

A blocked result is not equivalent to a secure result.

---

# 18. Review Findings

Findings are stored separately from raw scan history.

For each finding, examine:

- affected API operation
- test identity
- baseline object
- foreign object
- observed HTTP status
- severity
- confidence
- evidence
- explanation

Then verify the application's actual business rules.

---

# 19. Understand Severity and Confidence

Severity and confidence describe different things.

## Severity

Severity describes the expected security impact.

For example, unauthorized access to sensitive financial or personal data may have high impact.

## Confidence

Confidence describes how strongly the observed behavior supports the finding classification.

A finding still requires analyst understanding of the application's intended authorization rules.

---

# 20. Triage Findings

Findings can move through states such as:

```text
open
resolved
false_positive
accepted_risk
```

### Open

The issue remains active.

### Resolved

The issue has been fixed or otherwise remediated.

### False Positive

The observed behavior does not actually violate the intended authorization model.

### Accepted Risk

The issue is understood but intentionally accepted according to the organization's risk process.

---

# 21. Generate a Report

AccessMatrix supports several report formats.

| Format | Typical purpose |
|---|---|
| HTML | Human-readable security assessment |
| Markdown | Documentation, tickets, repositories |
| JSON | Automation and processing |
| SARIF 2.1.0 | Security and CI tooling |
| JUnit XML | CI/CD test-result workflows |

Reports are stored locally.

Treat them as security-sensitive artifacts.

---

# 22. Retest After Remediation

AccessMatrix is designed for regression testing.

Suppose the original result was:

```text
Alice -> Bob's invoice -> HTTP 200
```

Developers fix the authorization logic.

Run the same model again.

The expected new result might be:

```text
Alice -> Bob's invoice -> HTTP 403
```

This allows the authorization boundary to be checked repeatedly rather than relying on a one-time manual test.

---

# Recommended First Experience: Use the Demo

Before testing your own API, use the bundled deliberately vulnerable invoice application.

The demo lets you learn:

- project creation
- OpenAPI import
- identities
- credentials
- ownership modelling
- dataset validation
- BOLA planning
- scanning
- findings
- reporting
- network safety settings

without sending traffic to an external application.

Continue with:

```text
docs/demo-guide.md
```

---

# Important Limitations

AccessMatrix v0.1.0 primarily focuses on BOLA testing.

It does not automatically test every possible authorization problem.

A successful assessment still requires understanding of:

- application business logic
- roles
- privileges
- tenant boundaries
- object relationships
- intended security policy

AccessMatrix should assist professional security analysis rather than replace it.

---

# Security Reminder

Use AccessMatrix only against systems:

- you own
- you administer
- or you have explicit authorization to security test

The operator remains responsible for complying with applicable laws, contracts, policies, and rules of engagement.

---

# Where to Go Next

After this guide, continue with:

```text
docs/demo-guide.md
docs/concepts.md
docs/user-guide.md
docs/security-model.md
docs/troubleshooting.md
```

The demo guide is the recommended next document for new users.