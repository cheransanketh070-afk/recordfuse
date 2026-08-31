# Contributing

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
make quality
```

## Matching changes

Every change that can alter entity identity decisions should include a positive case, a negative case, an ambiguity or collision case where relevant, a missing/malformed-data case, and a deterministic-output assertion when ordering or IDs can change. For new fields, add normalization/scoring rules and document whether the field is a strong identifier.

## Pull requests

Keep changes focused. Explain any precision/recall trade-off, include sanitized fixtures only, update the changelog for user-visible behavior, and make all CI quality gates pass. Do not weaken lint, type, security, or coverage checks to make a change green.
