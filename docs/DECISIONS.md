# Architecture Decisions

## ADR-001: Deterministic by default
Reproducible decisions make regression testing, audit, replay, and rollback easier than opaque nondeterministic matching.

## ADR-002: Conservative identity policy
False merges can corrupt downstream systems. Name-only similarity is insufficient and contradictory strong identifiers are treated as negative evidence.

## ADR-003: Evidence is first-class data
Every scored field records raw values, normalized-match reason, similarity, and rule weight. Rejections can include a machine-readable veto reason.

## ADR-004: Source trust is not identity
Source priority chooses a canonical value *after* clustering. It cannot make two records the same entity.

## ADR-005: Guard against transitive over-merges
Plain connected components can merge incompatible records through intermediate nodes. Constrained union checks component identifier sets before accepting an edge.

## ADR-006: Dependency-light core
Core reconciliation uses the standard library. FastAPI is only the HTTP transport. This keeps embedding simple and makes alternative scorers possible later.
