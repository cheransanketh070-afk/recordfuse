# RecordFuse

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**RecordFuse** is a deterministic, explainable entity-resolution and record-reconciliation engine for messy multi-source datasets. It is designed for systems that need to deduplicate customers, reconcile CRM/billing/support exports, preserve provenance, and explain *why* two records were or were not merged.

## Why it is more than a fuzzy-match demo

RecordFuse separates candidate generation, evidence scoring, decision policy, constrained clustering, canonical merge, and audit output. The clustering stage includes a **transitive identifier-conflict guard**: even when A≈B and B≈C, the engine can block the final union if the resulting cluster would contain incompatible strong identifiers. That addresses a common over-merge failure mode in naive union-find entity resolution.

Key capabilities:

- Unicode-aware field normalization with a pluggable registry
- deterministic multi-pass blocking with oversized-bucket protection
- exact identifier matching plus fuzzy name similarity
- configurable field rules and decision thresholds
- evidence-rich `match` / `ambiguous` / `rejected` decisions
- safety-constrained union-find clustering
- source-priority canonical value selection
- full conflict, provenance, confidence, warning, and run-metric output
- CSV, JSON, JSONL/NDJSON ingestion
- CLI and FastAPI service
- deterministic run IDs and cluster IDs for reproducible pipelines
- labeled-pair evaluation helpers for precision, recall, F1, accuracy, and ambiguity rate
- strict linting, typing, coverage gate, package build, and dependency audit in CI

## Architecture

```text
CSV / JSON / JSONL
        |
        v
   Ingestion adapters
        |
        v
 Canonical records ---> Normalizer registry
        |                     |
        v                     v
  Blocking/indexing ----> candidate pairs
        |
        v
 Field-level similarity + evidence
        |
        v
 Decision policy + identifier vetoes
        |
        v
 Safety-constrained clustering
        |
        +--------------------+
        |                    |
        v                    v
 Canonical merge       Audit/conflicts
        |                    |
        +---------+----------+
                  v
             JSON result
```

## Quick start

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
ruff check .
mypy src/recordfuse
```

Run the bundled example:

```bash
recordfuse reconcile \
  --input examples/crm.csv \
  --input examples/billing.csv \
  --output reconciled.json
```

Compact output and custom thresholds are supported:

```bash
recordfuse reconcile examples/crm.csv examples/billing.csv \
  --no-pretty \
  --match-threshold 0.84 \
  --ambiguous-threshold 0.68 \
  --identifier-threshold 0.55
```

Start the API:

```bash
uvicorn recordfuse.service:app --host 0.0.0.0 --port 8000
```

Then POST to `/v1/reconcile`:

```json
{
  "records": [
    {
      "record_id": "crm-1",
      "source": "crm",
      "fields": {"name": "Jane Doe", "email": "jane@example.com"}
    },
    {
      "record_id": "billing-9",
      "source": "billing",
      "fields": {"name": "J. Doe", "email": "JANE@example.com"}
    }
  ]
}
```

## Default matching policy

| Field | Weight | Fuzzy | Identifier | Conflict veto |
|---|---:|:---:|:---:|:---:|
| name | 0.25 | yes | no | no |
| email | 0.45 | no | yes | yes |
| phone | 0.30 | no | yes | yes |

Defaults: normal match threshold `0.82`, exact-identifier assisted threshold `0.55`, ambiguous threshold `0.65`. Name-only evidence cannot declare a match. If strong identifiers explicitly conflict and no exact identifier bridges the pair, the pair is rejected.

## Programmatic API

```python
from recordfuse import DecisionPolicy, EntityRecord, Reconciler

records = [
    EntityRecord("1", "crm", {"name": "José Silva", "email": "JOSE@example.com"}),
    EntityRecord("2", "billing", {"name": "Jose Silva", "email": "jose@example.com"}),
]

result = Reconciler(policy=DecisionPolicy(match_threshold=0.82)).reconcile(records)
print(result.to_dict())
```

## Evaluate a calibrated ruleset

```python
from recordfuse import EntityRecord, LabeledPair, evaluate_pairs

pairs = [
    LabeledPair(
        EntityRecord("a", "crm", {"name": "Jane Doe", "email": "jane@example.com"}),
        EntityRecord("b", "billing", {"name": "Jane Doe", "email": "JANE@example.com"}),
        True,
    )
]

print(evaluate_pairs(pairs).to_dict())
```

This is intended for threshold calibration on sanitized, labeled examples rather than relying on a universal score cutoff.

## Reliability and safety properties

RecordFuse is deterministic for the same input and configuration. Candidate pairs are emitted in stable order; run IDs hash canonicalized input; cluster IDs hash sorted member IDs; merge tie-breaking is stable. Oversized blocking buckets are skipped rather than expanding unboundedly, and the result reports that count. Transitive clustering can block identifier-incompatible unions and emits human-readable warnings for review.

## Repository layout

```text
recordfuse/
├── src/recordfuse/          # library, CLI and API
├── tests/                   # unit, integration and regression tests
├── examples/                # runnable sample data
├── docs/                    # architecture, algorithm, decisions, threat model
├── .github/workflows/       # CI and release automation
├── Dockerfile
├── Makefile
├── CHANGELOG.md
├── CONTRIBUTING.md
├── SECURITY.md
└── pyproject.toml
```

## Engineering quality gates

Every pull request runs Ruff, strict MyPy, tests on Python 3.11–3.13, branch coverage with a 90% minimum, package build/install verification, and `pip-audit`. The linter is not configured with `--exit-zero`; failures fail CI.

## Limits

RecordFuse is deliberately deterministic and dependency-light. It is not a probabilistic ML matcher, does not infer hidden identifiers, and does not claim that a threshold is universally correct. Real deployments should calibrate rules on labeled pairs, monitor false merges, and add domain-specific normalization where appropriate. See [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) and [docs/ALGORITHM.md](docs/ALGORITHM.md).

## License

MIT. See [LICENSE](LICENSE).
