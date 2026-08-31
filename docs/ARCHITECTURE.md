# Architecture

RecordFuse is split into boundaries that can evolve independently:

- `adapters.py`: file formats -> `EntityRecord`
- `normalize.py`: field-aware canonicalization
- `blocking.py`: candidate generation and blocking statistics
- `scoring.py`: field rules, similarity, evidence and pair decisions
- `reconcile.py`: validation, constrained clustering, canonical merge and metrics
- `models.py`: transport-neutral domain objects
- `cli.py`: command-line transport
- `service.py`: HTTP transport

## Dependency direction

Transports depend on the core; the core does not depend on FastAPI. Normalizers and field rules are injectable. Source priority affects only canonical field selection, not identity scoring.

## Failure strategy

Invalid duplicate IDs fail fast. Unsupported file types fail explicitly. The service forbids unexpected request fields and caps request record count. Expensive blocking buckets are skipped and surfaced in metrics instead of silently consuming unbounded compute.

## Extension points

A deployment can replace `NormalizerRegistry`, `BlockingIndex`, `SimilarityEngine`, `FieldRule` maps, `DecisionPolicy`, or `SourcePriority` while keeping `Reconciler.reconcile()` stable.
