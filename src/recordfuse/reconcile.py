"""Core deterministic reconciliation pipeline."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from .blocking import BlockingIndex
from .config import DecisionPolicy, SourcePriority
from .models import (
    CanonicalEntity,
    Conflict,
    EntityRecord,
    MatchDecision,
    ReconciliationResult,
    SourceValue,
)
from .scoring import SimilarityEngine


class UnionFind:
    """Disjoint-set structure with deterministic roots and cluster metadata."""

    def __init__(self, ids: Iterable[str]) -> None:
        materialized = list(ids)
        self.parent = {
            item: item
            for item in materialized
        }
        self.rank = {
            item: 0
            for item in materialized
        }

    def find(self, item: str) -> str:
        root = item

        while self.parent[root] != root:
            root = self.parent[root]

        while self.parent[item] != item:
            nxt = self.parent[item]
            self.parent[item] = root
            item = nxt

        return root

    def union(
        self,
        left: str,
        right: str,
    ) -> str:
        root_left = self.find(left)
        root_right = self.find(right)

        if root_left == root_right:
            return root_left

        if (
            self.rank[root_left] < self.rank[root_right]
            or (
                self.rank[root_left] == self.rank[root_right]
                and root_right < root_left
            )
        ):
            root_left, root_right = root_right, root_left

        self.parent[root_right] = root_left

        if self.rank[root_left] == self.rank[root_right]:
            self.rank[root_left] += 1

        return root_left


@dataclass(slots=True)
class Reconciler:
    scorer: SimilarityEngine | None = None
    blocker: BlockingIndex | None = None
    source_priority: SourcePriority | None = None
    policy: DecisionPolicy | None = None

    def __post_init__(self) -> None:
        policy = self.policy or DecisionPolicy()
        scorer = self.scorer or SimilarityEngine(
            policy=policy
        )
        blocker = self.blocker or BlockingIndex(
            registry=scorer.registry
        )
        source_priority = (
            self.source_priority
            or SourcePriority()
        )

        self.policy = policy
        self.scorer = scorer
        self.blocker = blocker
        self.source_priority = source_priority

    @staticmethod
    def _run_id(
        records: list[EntityRecord],
    ) -> str:
        payload = [
            {
                "id": record.record_id,
                "source": record.source,
                "fields": record.fields,
                "metadata": record.metadata,
            }
            for record in sorted(
                records,
                key=lambda item: item.record_id,
            )
        ]

        return hashlib.sha256(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            ).encode()
        ).hexdigest()[:16]

    @staticmethod
    def _validate(
        records: list[EntityRecord],
    ) -> None:
        ids = [
            record.record_id
            for record in records
        ]

        if len(ids) != len(set(ids)):
            raise ValueError(
                "record_id values must be globally unique"
            )

        if any(
            not record.record_id
            or not record.source
            for record in records
        ):
            raise ValueError(
                "record_id and source are required"
            )

        if any(
            not isinstance(record.fields, dict)
            for record in records
        ):
            raise ValueError(
                "fields must be mappings"
            )

    @staticmethod
    def _cluster_id(
        members: list[EntityRecord],
    ) -> str:
        joined = "|".join(
            sorted(
                record.record_id
                for record in members
            )
        )

        return (
            "ent_"
            + hashlib.sha256(
                joined.encode()
            ).hexdigest()[:12]
        )

    def _identifier_values(
        self,
        records: Iterable[EntityRecord],
    ) -> dict[str, set[str]]:
        values: dict[str, set[str]] = defaultdict(set)

        assert self.scorer is not None

        for record in records:
            for field, rule in self.scorer.rules.items():
                if not rule.identifier:
                    continue

                value = self.scorer.registry.normalize(
                    field,
                    record.value(field),
                )

                if value:
                    values[field].add(value)

        return values

    def _clusters_compatible(
        self,
        left_members: list[EntityRecord],
        right_members: list[EntityRecord],
        decision: MatchDecision,
    ) -> tuple[bool, str | None]:
        assert self.policy is not None

        if not self.policy.prevent_transitive_identifier_conflicts:
            return True, None

        left_values = self._identifier_values(
            left_members
        )
        right_values = self._identifier_values(
            right_members
        )

        direct_conflict_fields = {
            evidence.field
            for evidence in decision.evidence
            if (
                evidence.similarity == 0.0
                and self.scorer is not None
                and self.scorer.rules[
                    evidence.field
                ].identifier
            )
        }

        expanding_existing_cluster = (
            len(left_members) > 1
            or len(right_members) > 1
        )

        for field in sorted(
            set(left_values)
            & set(right_values)
        ):
            if (
                left_values[field].isdisjoint(
                    right_values[field]
                )
                and (
                    expanding_existing_cluster
                    or field not in direct_conflict_fields
                )
            ):
                return (
                    False,
                    f"transitive {field} conflict",
                )

        return True, None

    def reconcile(
        self,
        records: Iterable[EntityRecord],
    ) -> ReconciliationResult:
        materialized = list(records)
        self._validate(materialized)

        if not materialized:
            return ReconciliationResult(
                self._run_id([]),
                [],
                [],
                [],
                {
                    "input_records": 0,
                    "candidate_pairs": 0,
                    "matched_pairs": 0,
                    "ambiguous_pairs": 0,
                    "rejected_pairs": 0,
                    "clusters": 0,
                    "conflicts": 0,
                    "blocked_merges": 0,
                    "reduction_ratio": 1.0,
                },
            )

        assert (
            self.blocker is not None
            and self.scorer is not None
        )

        uf = UnionFind(
            record.record_id
            for record in materialized
        )

        cluster_members: dict[
            str,
            list[EntityRecord],
        ] = {
            record.record_id: [record]
            for record in materialized
        }

        raw_decisions = [
            self.scorer.compare(left, right)
            for left, right in self.blocker.candidate_pairs(
                materialized
            )
        ]

        decisions = self._compute_margins(
            raw_decisions
        )

        blocked_merges = 0
        warnings: list[str] = []

        for decision in sorted(
            decisions,
            key=lambda item: (
                -item.score,
                item.left_id,
                item.right_id,
            ),
        ):
            if decision.status != "match":
                continue

            left_root = uf.find(
                decision.left_id
            )
            right_root = uf.find(
                decision.right_id
            )

            if left_root == right_root:
                continue

            compatible, reason = (
                self._clusters_compatible(
                    cluster_members[left_root],
                    cluster_members[right_root],
                    decision,
                )
            )

            if not compatible:
                blocked_merges += 1
                warnings.append(
                    "blocked merge "
                    f"{decision.left_id}<->"
                    f"{decision.right_id}: {reason}"
                )
                continue

            new_root = uf.union(
                left_root,
                right_root,
            )

            old_root = (
                right_root
                if new_root == left_root
                else left_root
            )

            cluster_members[new_root] = (
                cluster_members[left_root]
                + cluster_members[right_root]
            )

            cluster_members.pop(
                old_root,
                None,
            )

        groups: dict[
            str,
            list[EntityRecord],
        ] = defaultdict(list)

        for record in materialized:
            groups[
                uf.find(record.record_id)
            ].append(record)

        clusters: list[CanonicalEntity] = []
        conflicts: list[Conflict] = []

        match_scores_by_member: dict[
            str,
            list[float],
        ] = defaultdict(list)

        for decision in decisions:
            if (
                decision.status == "match"
                and uf.find(decision.left_id)
                == uf.find(decision.right_id)
            ):
                root = uf.find(
                    decision.left_id
                )
                match_scores_by_member[root].append(
                    decision.score
                )

        for members in sorted(
            groups.values(),
            key=lambda group: min(
                record.record_id
                for record in group
            ),
        ):
            cluster_id = self._cluster_id(
                members
            )

            canonical, provenance, found = (
                self._merge(
                    cluster_id,
                    members,
                )
            )

            root = uf.find(
                members[0].record_id
            )

            scores = match_scores_by_member.get(
                root,
                [],
            )

            confidence = (
                min(scores)
                if scores
                else 1.0
            )

            clusters.append(
                CanonicalEntity(
                    cluster_id=cluster_id,
                    fields=canonical,
                    member_ids=sorted(
                        record.record_id
                        for record in members
                    ),
                    provenance=provenance,
                    confidence=round(
                        confidence,
                        6,
                    ),
                )
            )

            conflicts.extend(found)

        total_possible = (
            len(materialized)
            * (len(materialized) - 1)
            // 2
        )

        candidate_count = len(decisions)

        reduction_ratio = (
            1.0
            if total_possible == 0
            else 1
            - candidate_count / total_possible
        )

        metrics: dict[str, int | float] = {
            "input_records": len(materialized),
            "candidate_pairs": candidate_count,
            "matched_pairs": sum(
                decision.status == "match"
                for decision in decisions
            ),
            "ambiguous_pairs": sum(
                decision.status == "ambiguous"
                for decision in decisions
            ),
            "rejected_pairs": sum(
                decision.status == "rejected"
                for decision in decisions
            ),
            "clusters": len(clusters),
            "conflicts": len(conflicts),
            "blocked_merges": blocked_merges,
            "reduction_ratio": round(
                reduction_ratio,
                6,
            ),
            "skipped_oversized_buckets": (
                self.blocker
                .last_stats
                .skipped_oversized_buckets
            ),
        }

        return ReconciliationResult(
            self._run_id(materialized),
            clusters,
            decisions,
            conflicts,
            metrics,
            warnings,
        )

    def _merge(
        self,
        cluster_id: str,
        members: list[EntityRecord],
    ) -> tuple[
        dict[str, object],
        dict[str, str],
        list[Conflict],
    ]:
        assert (
            self.scorer is not None
            and self.source_priority is not None
        )

        fields = sorted(
            {
                key
                for record in members
                for key in record.fields
            }
        )

        canonical: dict[str, object] = {}
        provenance: dict[str, str] = {}
        conflicts: list[Conflict] = []

        for field in fields:
            values = [
                SourceValue(
                    record.source,
                    record.value(field),
                    record.record_id,
                )
                for record in members
                if record.value(field)
                not in (None, "")
            ]

            if not values:
                continue

            normalized = {
                self.scorer.registry.normalize(
                    field,
                    source_value.value,
                )
                for source_value in values
            }

            ranked = sorted(
                values,
                key=lambda value: (
                    -self.source_priority.rank(
                        value.source
                    ),
                    str(value.value),
                    value.record_id or "",
                ),
            )

            selected = ranked[0]
            canonical[field] = selected.value
            provenance[field] = selected.source

            if len(normalized) > 1:
                conflicts.append(
                    Conflict(
                        cluster_id=cluster_id,
                        field=field,
                        values=tuple(values),
                        selected_source=selected.source,
                        reason=(
                            "multiple normalized values; "
                            "highest source priority selected"
                        ),
                    )
                )

        return (
            canonical,
            provenance,
            conflicts,
        )

    def _compute_margins(
        self,
        decisions: list[MatchDecision],
    ) -> list[MatchDecision]:
        """Record nearest-rival margins without downgrading valid duplicate groups.

        The margin is diagnostic. A pair is downgraded only when a strong rival
        shares one endpoint and the two edges rely on different exact
        identifiers, which is a useful sign of a one-to-many collision rather
        than a legitimate duplicate clique.
        """
        assert self.policy is not None

        by_id: dict[
            str,
            list[MatchDecision],
        ] = defaultdict(list)

        for decision in decisions:
            by_id[decision.left_id].append(
                decision
            )
            by_id[decision.right_id].append(
                decision
            )

        updated: list[MatchDecision] = []

        for decision in decisions:
            alternatives = [
                other
                for other in (
                    by_id[decision.left_id]
                    + by_id[decision.right_id]
                )
                if (
                    other.left_id,
                    other.right_id,
                )
                != (
                    decision.left_id,
                    decision.right_id,
                )
            ]

            best_alt = max(
                (
                    other.score
                    for other in alternatives
                ),
                default=0.0,
            )

            margin = max(
                0.0,
                decision.score - best_alt,
            )

            status = decision.status

            if (
                decision.status == "match"
                and margin
                < self.policy.ambiguity_margin
            ):
                exact_ids = {
                    evidence.field
                    for evidence in decision.evidence
                    if (
                        evidence.similarity == 1.0
                        and self.scorer is not None
                        and self.scorer.rules[
                            evidence.field
                        ].identifier
                    )
                }

                for alternative in alternatives:
                    if (
                        abs(
                            alternative.score
                            - decision.score
                        )
                        > self.policy.ambiguity_margin
                    ):
                        continue

                    alt_exact_ids = {
                        evidence.field
                        for evidence in alternative.evidence
                        if (
                            evidence.similarity == 1.0
                            and self.scorer is not None
                            and self.scorer.rules[
                                evidence.field
                            ].identifier
                        )
                    }

                    if (
                        exact_ids
                        and alt_exact_ids
                        and exact_ids.isdisjoint(
                            alt_exact_ids
                        )
                    ):
                        status = "ambiguous"
                        break

            updated.append(
                MatchDecision(
                    decision.left_id,
                    decision.right_id,
                    decision.score,
                    margin,
                    status,
                    decision.evidence,
                    decision.veto_reason,
                )
            )

        return updated
