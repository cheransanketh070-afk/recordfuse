"""Domain models used by RecordFuse.

The public dataclasses intentionally contain only serialisable values so results can be
written to JSON, stored in audit logs, or transported across service boundaries.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

DecisionStatus = Literal["match", "ambiguous", "rejected"]


@dataclass(frozen=True, slots=True)
class SourceValue:
    source: str
    value: Any
    record_id: str | None = None


@dataclass(frozen=True, slots=True)
class EntityRecord:
    record_id: str
    source: str
    fields: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def value(self, name: str) -> Any:
        return self.fields.get(name)


@dataclass(frozen=True, slots=True)
class Evidence:
    field: str
    left: Any
    right: Any
    similarity: float
    reason: str
    weight: float = 0.0


@dataclass(frozen=True, slots=True)
class MatchDecision:
    left_id: str
    right_id: str
    score: float
    margin: float
    status: DecisionStatus
    evidence: tuple[Evidence, ...]
    veto_reason: str | None = None


@dataclass(frozen=True, slots=True)
class Conflict:
    cluster_id: str
    field: str
    values: tuple[SourceValue, ...]
    selected_source: str | None
    reason: str


@dataclass(slots=True)
class CanonicalEntity:
    cluster_id: str
    fields: dict[str, Any]
    member_ids: list[str]
    provenance: dict[str, str]
    confidence: float = 1.0


@dataclass(slots=True)
class ReconciliationResult:
    run_id: str
    clusters: list[CanonicalEntity]
    decisions: list[MatchDecision]
    conflicts: list[Conflict]
    metrics: dict[str, int | float]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "clusters": [asdict(cluster) for cluster in self.clusters],
            "decisions": [
                {
                    **asdict(decision),
                    "score": round(decision.score, 6),
                    "margin": round(decision.margin, 6),
                    "evidence": [asdict(evidence) for evidence in decision.evidence],
                }
                for decision in self.decisions
            ],
            "conflicts": [asdict(conflict) for conflict in self.conflicts],
            "metrics": self.metrics,
            "warnings": self.warnings,
        }
