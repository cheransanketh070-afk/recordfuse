# Changelog

All notable changes follow Keep a Changelog style and semantic versioning.

## [0.2.0] - 2026-08-31

### Added
- Configurable `DecisionPolicy` and richer `FieldRule` model.
- Safety-constrained clustering that blocks transitive identifier conflicts.
- JSONL/NDJSON ingestion and a unified `read_records` adapter.
- Blocking bucket caps, deterministic pair ordering, and reduction metrics.
- Cluster confidence, merge warnings, evidence weights, and veto reasons.
- API payload validation limits and version-aware health endpoint.
- Strict MyPy, branch coverage gate, package verification, and dependency audit in CI.
- Threat model, benchmark guidance, release checklist, code of conduct, and issue templates.

### Changed
- Reworked core models with slots and fully serializable audit output.
- Improved deterministic root selection and canonical merge tie-breaking.

## [0.1.0] - 2026-08-30
- Initial deterministic entity-resolution engine with CLI, API, tests, and docs.
