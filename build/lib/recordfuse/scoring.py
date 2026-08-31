"""Explainable field-level similarity and pair decisions."""

from __future__ import annotations

from dataclasses import dataclass

from .config import DecisionPolicy
from .models import EntityRecord, Evidence, MatchDecision
from .normalize import NormalizerRegistry


def levenshtein_ratio(a: str, b: str) -> float:
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, char_a in enumerate(a, 1):
        current = [i]
        for j, char_b in enumerate(b, 1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[j] + 1,
                    previous[j - 1] + (char_a != char_b),
                )
            )
        previous = current
    return 1.0 - previous[-1] / max(len(a), len(b))


def token_similarity(a: str, b: str) -> float:
    left, right = set(a.split()), set(b.split())
    return len(left & right) / len(left | right) if left and right else 0.0


@dataclass(frozen=True, slots=True)
class FieldRule:
    weight: float
    fuzzy: bool = True
    identifier: bool = False
    veto_on_conflict: bool = False

    def __post_init__(self) -> None:
        if self.weight <= 0:
            raise ValueError("field rule weight must be positive")


DEFAULT_RULES = {
    "name": FieldRule(0.25, fuzzy=True),
    "email": FieldRule(0.45, fuzzy=False, identifier=True, veto_on_conflict=True),
    "phone": FieldRule(0.30, fuzzy=False, identifier=True, veto_on_conflict=True),
}


class SimilarityEngine:
    """Score record pairs using configured rules while preserving evidence."""

    def __init__(
        self,
        registry: NormalizerRegistry | None = None,
        rules: dict[str, FieldRule] | None = None,
        policy: DecisionPolicy | None = None,
    ) -> None:
        self.registry = registry or NormalizerRegistry()
        self.rules = dict(rules or DEFAULT_RULES)
        self.policy = policy or DecisionPolicy()

    def _field_similarity(self, field: str, left: str, right: str) -> tuple[float, str]:
        if not left or not right:
            return 0.0, "missing-value"
        if left == right:
            return 1.0, "exact-normalized-match"
        rule = self.rules[field]
        if not rule.fuzzy:
            return 0.0, "identifier-mismatch" if rule.identifier else "exact-mismatch"
        if field == "name":
            score = max(levenshtein_ratio(left, right), token_similarity(left, right))
            return score, "name-fuzzy-similarity"
        return levenshtein_ratio(left, right), "generic-fuzzy-similarity"

    def compare(self, left: EntityRecord, right: EntityRecord) -> MatchDecision:
        evidence: list[Evidence] = []
        weighted = 0.0
        weights = 0.0
        conflicting_identifiers: list[str] = []
        exact_identifiers: list[str] = []

        for field, rule in self.rules.items():
            left_norm = self.registry.normalize(field, left.value(field))
            right_norm = self.registry.normalize(field, right.value(field))
            similarity, reason = self._field_similarity(field, left_norm, right_norm)

            if left_norm and right_norm:
                evidence.append(
                    Evidence(
                        field=field,
                        left=left.value(field),
                        right=right.value(field),
                        similarity=similarity,
                        reason=reason,
                        weight=rule.weight,
                    )
                )
                weighted += rule.weight * similarity
                weights += rule.weight

                if rule.identifier and similarity == 1.0:
                    exact_identifiers.append(field)
                elif rule.identifier and rule.veto_on_conflict and similarity == 0.0:
                    conflicting_identifiers.append(field)

        score = weighted / weights if weights else 0.0
        has_identifier_evidence = any(self.rules[e.field].identifier for e in evidence)
        veto_reason = None

        if (
            conflicting_identifiers
            and not exact_identifiers
            and self.policy.reject_identifier_conflicts
        ):
            status = "rejected"
            veto_reason = "conflicting identifier(s): " + ", ".join(sorted(conflicting_identifiers))
        elif exact_identifiers and score >= self.policy.identifier_match_threshold:
            status = "match"
        elif not has_identifier_evidence:
            status = "rejected"
            veto_reason = "no identifier evidence"
        elif score >= self.policy.match_threshold:
            status = "match"
        elif score >= self.policy.ambiguous_threshold:
            status = "ambiguous"
        else:
            status = "rejected"

        return MatchDecision(
            left.record_id,
            right.record_id,
            score,
            0.0,
            status,
            tuple(evidence),
            veto_reason,
        )
