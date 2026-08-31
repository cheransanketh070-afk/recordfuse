"""RecordFuse public API."""

from .config import DecisionPolicy, SourcePriority
from .evaluation import EvaluationMetrics, LabeledPair, evaluate_pairs
from .models import EntityRecord, ReconciliationResult
from .reconcile import Reconciler
from .scoring import FieldRule, SimilarityEngine

__version__ = "0.2.0"

__all__ = [
    "DecisionPolicy",
    "EntityRecord",
    "EvaluationMetrics",
    "FieldRule",
    "LabeledPair",
    "ReconciliationResult",
    "Reconciler",
    "SimilarityEngine",
    "SourcePriority",
    "evaluate_pairs",
]
