"""Deterministic multi-key candidate generation."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations

from .models import EntityRecord
from .normalize import NormalizerRegistry


@dataclass(frozen=True, slots=True)
class BlockingStats:
    records: int
    buckets: int
    skipped_oversized_buckets: int
    candidate_pairs: int


class BlockingIndex:
    """Generate plausible pairs without an unconditional O(n²) scan.

    Oversized buckets are skipped to prevent generic names or shared email
    domains from turning into accidental quadratic work. Exact email remains
    its own highly selective key.
    """

    def __init__(
        self,
        registry: NormalizerRegistry | None = None,
        *,
        max_bucket_size: int = 250,
        phone_suffix_length: int = 7,
    ) -> None:
        if max_bucket_size < 2:
            raise ValueError("max_bucket_size must be >= 2")

        if phone_suffix_length < 4:
            raise ValueError("phone_suffix_length must be >= 4")

        self.registry = registry or NormalizerRegistry()
        self.max_bucket_size = max_bucket_size
        self.phone_suffix_length = phone_suffix_length
        self.last_stats = BlockingStats(0, 0, 0, 0)

    def keys(self, record: EntityRecord) -> set[str]:
        keys: set[str] = set()

        email = self.registry.normalize(
            "email",
            record.value("email"),
        )
        phone = self.registry.normalize(
            "phone",
            record.value("phone"),
        )
        name = self.registry.normalize(
            "name",
            record.value("name"),
        )

        if email:
            keys.add(f"email:{email}")

            if "@" in email:
                local, domain = email.rsplit("@", 1)

                if len(local) >= 3:
                    keys.add(
                        f"email-local-domain:{local[:3]}:{domain}"
                    )

        if phone:
            keys.add(
                f"phone-suffix:{phone[-self.phone_suffix_length:]}"
            )

        if name:
            tokens = name.split()

            if tokens:
                keys.add(f"name-first:{tokens[0]}")
                keys.add(f"name-last:{tokens[-1]}")

            if len(tokens) >= 2:
                keys.add(
                    f"name-initials:{tokens[0][0]}:{tokens[-1]}"
                )

        return keys

    def candidate_pairs(
        self,
        records: list[EntityRecord],
    ) -> list[tuple[EntityRecord, EntityRecord]]:
        buckets: dict[str, list[EntityRecord]] = defaultdict(list)

        for record in records:
            for key in self.keys(record):
                buckets[key].append(record)

        seen: set[tuple[str, str]] = set()
        result: list[tuple[EntityRecord, EntityRecord]] = []
        skipped = 0

        for key in sorted(buckets):
            bucket = sorted(
                buckets[key],
                key=lambda record: record.record_id,
            )

            if len(bucket) > self.max_bucket_size:
                skipped += 1
                continue

            for left, right in combinations(bucket, 2):
                if left.record_id == right.record_id:
                    continue

                pair = tuple(
                    sorted(
                        (left.record_id, right.record_id)
                    )
                )

                if pair not in seen:
                    seen.add(pair)
                    result.append((left, right))

        result.sort(
            key=lambda pair: (
                pair[0].record_id,
                pair[1].record_id,
            )
        )

        self.last_stats = BlockingStats(
            len(records),
            len(buckets),
            skipped,
            len(result),
        )

        return result
