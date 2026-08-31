"""Evaluation helpers for calibrating RecordFuse on labeled record pairs."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .models import EntityRecord
from .scoring import SimilarityEngine


@dataclass(frozen=True, slots=True)
class LabeledPair:
    left: EntityRecord
    right: EntityRecord
    is_match: bool


@dataclass(frozen=True, slots=True)
class EvaluationMetrics:
    true_positive: int
    false_positive: int
    true_negative: int
    false_negative: int
    ambiguous: int
    precision: float
    recall: float
    f1: float
    accuracy: float

    def to_dict(self) -> dict[str, int | float]:
        return {
            "true_positive": self.true_positive,
            "false_positive": self.false_positive,
            "true_negative": self.true_negative,
            "false_negative": self.false_negative,
            "ambiguous": self.ambiguous,
            "precision": round(self.precision, 6),
            "recall": round(self.recall, 6),
            "f1": round(self.f1, 6),
            "accuracy": round(self.accuracy, 6),
        }


def evaluate_pairs(
    pairs: Iterable[LabeledPair],
    scorer: SimilarityEngine | None = None,
    *,
    ambiguous_as_match: bool = False,
) -> EvaluationMetrics:
    """Evaluate pair decisions against binary labels.

    Ambiguous decisions are counted separately and, by default, treated as
    non-matches in confusion-matrix metrics. Set ``ambiguous_as_match=True``
    to measure a review-assisted operating point where ambiguous pairs enter
    the positive queue.
    """
    engine = scorer or SimilarityEngine()

    tp = 0
    fp = 0
    tn = 0
    fn = 0
    ambiguous = 0

    for labeled in pairs:
        decision = engine.compare(
            labeled.left,
            labeled.right,
        )

        predicted_match = decision.status == "match"

        if decision.status == "ambiguous":
            ambiguous += 1
            predicted_match = ambiguous_as_match

        if predicted_match and labeled.is_match:
            tp += 1
        elif predicted_match and not labeled.is_match:
            fp += 1
        elif not predicted_match and labeled.is_match:
            fn += 1
        else:
            tn += 1

    precision = (
        tp / (tp + fp)
        if tp + fp
        else 0.0
    )

    recall = (
        tp / (tp + fn)
        if tp + fn
        else 0.0
    )

    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )

    total = tp + fp + tn + fn

    accuracy = (
        (tp + tn) / total
        if total
        else 0.0
    )

    return EvaluationMetrics(
        tp,
        fp,
        tn,
        fn,
        ambiguous,
        precision,
        recall,
        f1,
        accuracy,
    )
