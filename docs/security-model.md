# AccessMatrix Security Model

AccessMatrix is security-testing software and should itself be treated as security-sensitive software.

This document describes the major security assumptions, controls, and known limitations of AccessMatrix v0.1.0.

---

# Trust Model

AccessMatrix is designed primarily to run locally on a machine controlled by the tester.

The local machine is therefore inside the AccessMatrix trust boundary.

If that machine is compromised, an attacker may potentially access:

- credentials available to the AccessMatrix process
- OpenAPI specifications
- authorization datasets
- scan evidence
- findings
- reports
- application settings
- audit records

Protect the host appropriately.

---

# Local-First Design

AccessMatrix stores its operational data locally.

This includes data such as:

```text
projects
authorization datasets
scan results
findings
reports
settings
audit events
```

Local-first operation gives the tester greater control over security-assessment data.

It does not remove the need to protect:

- filesystem permissions
- local user accounts
- disk encryption
- backups
- endpoint security

---

# Credential Separation

AccessMatrix is designed to reference credentials rather than unnecessarily duplicate raw secrets throughout project data.

Credential sources can include mechanisms such as:

```text
environment variables
operating-system keyring
```

Never commit real credentials into Git.

Avoid storing credentials in:

- README files
- documentation
- screenshots
- OpenAPI examples
- findings
- reports
- test fixtures intended for publication

The tokens used by the bundled demo are intentionally fake and protect no real system.

---

# Target Validation

Before controlled request execution, AccessMatrix validates the configured target.

Target validation considers information such as:

```text
URL scheme
hostname
resolved IP addresses
network classification
configured network-access policy
```

Only supported HTTP and HTTPS targets should be used.

---

# Network Access Modes

AccessMatrix supports network policies including:

```text
public_only
public_and_loopback
private_networks
```

## public_only

Intended for cases where requests should be restricted to publicly routable targets.

## public_and_loopback

Allows public targets and local loopback addresses.

This is the normal mode used by the bundled local demo.

## private_networks

Allows authorized private-network testing.

This should only be used when the operator is explicitly permitted to assess the internal target.

---

# Special Address Classes

Separate controls exist for address categories such as:

```text
link-local
multicast
reserved
```

These are disabled by default.

Enable them only when the testing environment specifically requires them and the target is authorized.

---

# DNS Resolution

AccessMatrix can resolve target hostnames before execution and classify the returned IP addresses.

Current defaults include:

```text
DNS resolution: enabled
DNS timeout: 3 seconds
Maximum resolved addresses: 16
```

---

# Known DNS Limitation

AccessMatrix performs DNS pre-resolution and address classification.

However:

```text
validated DNS resolution
```

is not equivalent to:

```text
pinning the actual network connection to the validated IP address
```

The underlying HTTP networking layer may perform another DNS lookup when establishing the connection.

Therefore AccessMatrix v0.1.0 should not be described as completely resistant to every DNS-rebinding scenario.

This is a known limitation.

---

# Redirect Safety

Redirect behavior is restricted during controlled execution.

Following arbitrary redirects can cause a request to reach a destination different from the target that was originally validated.

---

# Request Timeout

The default execution timeout is:

```text
10 seconds
```

This limits how long AccessMatrix waits for an individual target request.

---

# Request Size Limit

The default maximum request-body size is:

```text
1 MiB
```

This helps prevent unexpectedly large generated requests.

---

# Response Size Limit

The default maximum response-body size is:

```text
4 MiB
```

This bounds response processing and evidence collection.

---

# Rate Limiting

The default execution rate limit is:

```text
30 requests per 60 seconds
```

The configured AccessMatrix limit is not permission to send traffic at that rate.

Always follow the lower limit defined by:

```text
AccessMatrix configuration
rules of engagement
target safety requirements
```

---

# Parallel Requests

The default maximum number of parallel requests is:

```text
4
```

Higher concurrency can increase target load.

Use conservative settings when testing sensitive systems.

---

# Evidence Controls

AccessMatrix bounds stored evidence.

Current defaults include:

```text
Response excerpt:      16 KiB
Store response headers: enabled
Maximum raw scan:      16 MiB
Maximum report:        32 MiB
Retained raw scans:    50
```

These controls reduce uncontrolled evidence growth.

They do not guarantee that evidence contains no sensitive data.

---

# Sensitive Evidence

API responses may contain:

- personal information
- financial information
- internal identifiers
- application metadata
- tenant information
- account information

Protect AccessMatrix evidence accordingly.

---

# Scan Authorization Acknowledgement

BOLA scanning is active security testing.

AccessMatrix requires explicit acknowledgement before starting a BOLA scan.

This reduces the risk of accidental execution.

It does not grant legal or contractual authorization.

The human operator remains responsible for testing scope and permission.

---

# Findings and Raw Evidence

Findings are stored separately from raw scan evidence.

Conceptually:

```text
Scan
 |
 +--> Raw evidence
 |
 +--> Durable finding
```

Retention can remove older raw scan data while preserving finding history.

This supports regression-testing workflows.

---

# Report Security

Generated reports can contain:

- API paths
- object identifiers
- security findings
- identity labels
- evidence
- application behavior

Treat reports as security-sensitive artifacts.

Do not publish reports from private environments without review and authorization.

---

# Audit Events

AccessMatrix can store local audit events for relevant actions.

Current defaults include:

```text
Audit logging: enabled
Retention: 180 days
Maximum events: 10,000
```

Audit data should also be protected.

---

# Local File Safety

AccessMatrix storage components use defensive handling for identifiers and generated file paths.

The project includes controls intended to reduce unsafe path traversal and uncontrolled artifact sizes.

---

# Partial Operations

Some AccessMatrix workflows perform more than one storage operation.

A secondary failure does not always mean that an earlier successful persistence operation was automatically rolled back.

When an operation returns an error, review the resulting application state rather than assuming that nothing changed.

---

# Historical Artifact Limits

Lowering a configured maximum artifact size below the size of an existing historical scan or report may make that older artifact unavailable under the new limit.

Choose retention and artifact-size settings deliberately.

---

# Security Assumptions

AccessMatrix assumes that:

```text
the operator is authorized
the local machine is reasonably trusted
the configured credentials belong to intended identities
the ownership model is accurate
the OpenAPI document represents the relevant API
the selected environment is within scope
```

Incorrect assumptions can produce incorrect conclusions.

---

# What AccessMatrix Does Not Guarantee

AccessMatrix does not guarantee:

- absence of all authorization vulnerabilities
- absence of all API vulnerabilities
- correctness of user-supplied ownership data
- correctness of application business rules
- complete resistance to hostile DNS behavior
- security of the local host
- safe operation against unauthorized systems

AccessMatrix is a security-testing and regression-testing tool, not mathematical proof that an API is secure.

---

# Responsible Use

Use AccessMatrix only against systems:

- you own
- you administer
- or you have explicit authorization to security test

Maintain appropriate rules of engagement for professional assessments.

---

# Reporting Security Issues in AccessMatrix

Security vulnerabilities affecting AccessMatrix itself should be reported according to:

```text
SECURITY.md
```

Do not publicly disclose credentials, customer data, private target information, or sensitive exploit details unnecessarily.