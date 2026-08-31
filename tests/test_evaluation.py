from recordfuse.evaluation import LabeledPair, evaluate_pairs
from recordfuse.models import EntityRecord
from recordfuse.config import DecisionPolicy
from recordfuse.scoring import FieldRule, SimilarityEngine


def record(record_id, name, email=None):
    fields = {"name": name}
    if email is not None:
        fields["email"] = email
    return EntityRecord(record_id, "test", fields)


def test_evaluate_pairs_confusion_metrics():
    pairs = [
        LabeledPair(record("a", "Jane Doe", "j@example.com"), record("b", "Jane Doe", "J@example.com"), True),
        LabeledPair(record("c", "Jane Doe", "x@example.com"), record("d", "Jane Doe", "y@example.com"), False),
        LabeledPair(record("e", "Only Name"), record("f", "Only Name"), True),
    ]
    metrics = evaluate_pairs(pairs)
    assert metrics.true_positive == 1
    assert metrics.true_negative == 1
    assert metrics.false_negative == 1
    assert metrics.precision == 1.0
    assert metrics.recall == 0.5
    assert metrics.to_dict()["f1"] > 0


def test_evaluate_empty_pairs():
    metrics = evaluate_pairs([])
    assert metrics.accuracy == 0.0
    assert metrics.to_dict()["precision"] == 0.0


def test_ambiguous_can_be_counted_as_positive():
    rules = {
        "name": FieldRule(0.5, fuzzy=True),
        "email": FieldRule(0.5, fuzzy=False, identifier=True),
    }
    policy = DecisionPolicy(
        match_threshold=0.95,
        ambiguous_threshold=0.7,
        identifier_match_threshold=0.95,
    )
    scorer = SimilarityEngine(rules=rules, policy=policy)
    pair = LabeledPair(
        record("a", "Jane Doe", "same@example.com"),
        record("b", "Jane D", "same@example.com"),
        True,
    )
    strict = evaluate_pairs([pair], scorer)
    review = evaluate_pairs([pair], scorer, ambiguous_as_match=True)
    assert strict.ambiguous == 1
    assert strict.false_negative == 1
    assert review.true_positive == 1
