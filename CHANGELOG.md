# Changelog

All notable changes to AccessMatrix will be documented in this file.

---

## [0.1.0] - 2026-10-17

First public development release of AccessMatrix.

### Added

- local-first FastAPI backend
- React and TypeScript GUI
- project creation and management
- OpenAPI import
- OpenAPI operation discovery
- identity management
- credential-reference support
- authorization datasets
- resource and object ownership modelling
- authorization dataset validation
- BOLA test-plan generation
- controlled authenticated request execution
- target validation
- network-access policies
- DNS resolution controls
- request timeout controls
- request-size limits
- response-size limits
- request rate limiting
- bounded request concurrency
- automated BOLA scanning
- baseline-first authorization testing
- pass, finding, inconclusive, and blocked scan outcomes
- durable finding storage
- finding lifecycle states
- severity and confidence classification
- bounded response evidence
- response hashing
- scan storage
- configurable scan retention
- application settings
- local audit events
- audit retention
- HTML reports
- Markdown reports
- JSON reports
- SARIF 2.1.0 reports
- JUnit XML reports
- report preview and download
- deliberately vulnerable local invoice demonstration API
- bundled demonstration OpenAPI specification
- demo identity and ownership data
- user documentation
- installation guide
- getting-started guide
- demo guide
- concepts and terminology guide
- security model
- troubleshooting guide
- development guide
- contribution guidance
- security reporting policy

---

### Validation Baseline

AccessMatrix v0.1.0 was validated with:

```text
Python: 3.13.14
Ruff: clean
MyPy: clean
Pytest: 106 passing
Overall test coverage: 76%
```

---

### Known Limitations

The initial release intentionally has a focused scope.

Known limitations include:

- automated authorization scanning currently focuses primarily on BOLA
- authorization ownership information must be supplied or seeded
- OpenAPI alone does not provide enough business ownership context
- AccessMatrix cannot prove the absence of authorization vulnerabilities
- authorization findings still require application and business-context review
- DNS pre-resolution does not provide socket-level IP pinning
- the underlying HTTP client may resolve a hostname again during connection establishment
- some historical artifacts may become unreadable if configured maximum artifact sizes are later reduced below their stored size
- some multi-step persistence workflows can partially succeed before a later secondary operation fails
- privileged identities require careful modelling because broader access may be legitimate

---

### Security Notes

AccessMatrix v0.1.0 includes controls for:

- explicit scan authorization acknowledgement
- network destination validation
- bounded execution
- request rate limiting
- response limits
- evidence limits
- local credential references
- defensive file handling
- durable findings
- audit logging
- report size limits

Security assumptions and limitations are documented in:

```text
docs/security-model.md
```

---

### Demo

The bundled local demonstration is intentionally vulnerable to BOLA.

Expected demonstration result:

```text
Status: completed
Total cases: 4
Findings: 4
Passed: 0
Inconclusive: 0
Blocked: 0
```

The demo should remain bound to local loopback and should not be exposed publicly.

---

### Author

**Ubaid Ahmad Bhat**

LinkedIn:

https://www.linkedin.com/in/ubaid-ahmad-bhat-a766741b6/