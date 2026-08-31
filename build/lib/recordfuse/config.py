"""Configuration primitives for deterministic reconciliation."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class SourcePriority:
    """Select canonical values from the highest-priority source after matching."""

    priorities: dict[str, int] = field(
        default_factory=lambda: {"crm": 100, "billing": 90, "support": 70}
    )

    def rank(self, source: str) -> int:
        return self.priorities.get(source, 0)


@dataclass(frozen=True, slots=True)
class DecisionPolicy:
    """Thresholds and safety controls for the matching decision layer."""

    match_threshold: float = 0.82
    identifier_match_threshold: float = 0.55
    ambiguous_threshold: float = 0.65
    ambiguity_margin: float = 0.04
    reject_identifier_conflicts: bool = True
    prevent_transitive_identifier_conflicts: bool = True

    def __post_init__(self) -> None:
        if not 0 <= self.ambiguous_threshold <= self.match_threshold <= 1:
            raise ValueError("thresholds must satisfy 0 <= ambiguous <= match <= 1")
        if not 0 <= self.identifier_match_threshold <= 1:
            raise ValueError("identifier_match_threshold must be between 0 and 1")
        if not 0 <= self.ambiguity_margin <= 1:
            raise ValueError("ambiguity_margin must be between 0 and 1")
