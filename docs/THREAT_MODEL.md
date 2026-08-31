# Threat Model

RecordFuse processes potentially sensitive identity data. This document describes application-level risks; operators remain responsible for infrastructure and regulatory controls.

## Assets

- raw identifiers such as email and phone
- canonical records and provenance
- decision evidence and conflict logs
- reconciliation output consumed by downstream systems

## Main risks and mitigations

**Over-merge / identity corruption.** Identifier vetoes, name-only rejection, ambiguity states, and transitive-cluster conflict guards reduce accidental merges. Thresholds remain domain-specific and should be calibrated.

**Denial of service from pathological inputs.** HTTP record count is capped; blocking buckets have maximum sizes; unsupported formats and malformed JSON fail early.

**PII leakage through logs.** The library does not log raw records by default. Applications should avoid logging full API payloads and should protect reconciliation output as sensitive data.

**Formula injection when re-exporting CSV.** RecordFuse currently emits JSON. Integrators that export spreadsheet formats should escape cells beginning with `=`, `+`, `-`, or `@`.

**Dependency compromise.** Runtime dependencies are intentionally small. CI runs dependency auditing; releases should pin deployment lockfiles or image digests where operationally required.

## Out of scope

RecordFuse does not authenticate users, encrypt storage, implement tenancy, or provide legal/compliance guarantees. Those belong in the hosting application or platform.
