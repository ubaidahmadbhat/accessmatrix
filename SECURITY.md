# Security Policy

AccessMatrix is security-testing software, so security issues affecting AccessMatrix itself should be handled carefully and responsibly.

---

## Supported Version

The currently supported public release line is:

```text
0.1.x
```

Security fixes will primarily target the latest available release.

---

## Reporting a Security Vulnerability

Please do **not** publicly disclose an exploitable AccessMatrix vulnerability before it has been reviewed.

When available, use GitHub's **Private Vulnerability Reporting** or GitHub Security Advisory functionality for the repository.

Maintainer:

**Ubaid Ahmad Bhat**

LinkedIn:

https://www.linkedin.com/in/ubaid-ahmad-bhat-a766741b6/

---

## What to Include

A useful security report should contain:

- affected AccessMatrix version
- operating system
- Python version
- clear vulnerability description
- reproduction steps
- expected behavior
- observed behavior
- security impact
- proof of concept where appropriate
- suggested mitigation if known

Provide only the information required to reproduce the AccessMatrix vulnerability.

---

## Do Not Include Unnecessary Secrets

Do not include unrelated:

- passwords
- bearer tokens
- API keys
- session cookies
- private keys
- customer information
- production API responses
- private OpenAPI specifications

Redact sensitive information whenever it is not necessary to reproduce the issue.

---

## Security Issues in Scope

Examples include vulnerabilities involving:

- credential disclosure
- unsafe credential handling
- target-validation bypass
- network-policy bypass
- unsafe redirects
- arbitrary file access
- path traversal
- report or evidence injection
- unsafe artifact handling
- unexpected external network access
- sensitive data leakage
- authentication or authorization problems in AccessMatrix
- dangerous default behavior
- execution-limit bypass
- security-control bypass

This list is not exhaustive.

---

## Third-Party Target Vulnerabilities

This security policy applies to **AccessMatrix itself**.

If AccessMatrix discovers a vulnerability in a third-party API, do not report that target vulnerability through the AccessMatrix repository.

Instead, use the target organization's authorized vulnerability-reporting or responsible-disclosure process.

Do not publish sensitive target information in AccessMatrix GitHub issues.

---

## Responsible Security Research

Security research involving AccessMatrix should use:

- systems you own
- systems you administer
- or systems you have explicit authorization to test

The presence of AccessMatrix does not grant authorization to test third-party systems.

---

## Disclosure

Please allow reasonable time for investigation and remediation before public disclosure of a confirmed vulnerability.

Coordinated disclosure helps protect AccessMatrix users while a fix is developed and released.

---

## Public Issues

Normal bugs, documentation problems, usability issues, and non-sensitive feature requests may be reported through GitHub Issues.

Do not use a public issue when the report contains information that could immediately help exploit a security vulnerability in AccessMatrix.

---

## Security Philosophy

AccessMatrix aims to maintain:

- explicit authorization before active scanning
- local-first operation
- credential separation
- bounded evidence
- defensive storage
- target validation
- network restrictions
- controlled execution
- documented limitations

Security controls and limitations should be communicated clearly rather than hidden.