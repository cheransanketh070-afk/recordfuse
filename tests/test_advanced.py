import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from recordfuse.adapters import read_csv, read_json, read_jsonl, read_records
from recordfuse.blocking import BlockingIndex
from recordfuse.cli import parse_args, run_cli
from recordfuse.config import DecisionPolicy, SourcePriority
from recordfuse.models import EntityRecord
from recordfuse.normalize import NormalizerRegistry, normalize_address, normalize_email, normalize_generic
from recordfuse.reconcile import Reconciler, UnionFind
from recordfuse.scoring import FieldRule, SimilarityEngine, levenshtein_ratio, token_similarity
from recordfuse.service import app


def test_policy_validation():
    with pytest.raises(ValueError):
        DecisionPolicy(match_threshold=0.4, ambiguous_threshold=0.5)
    with pytest.raises(ValueError):
        DecisionPolicy(identifier_match_threshold=1.5)
    with pytest.raises(ValueError):
        DecisionPolicy(ambiguity_margin=-0.1)


def test_source_priority_unknown_source():
    assert SourcePriority().rank("unknown") == 0


def test_normalizers_cover_idna_address_and_generic():
    assert normalize_email(" A@BÜCHER.de ") == "a@xn--bcher-kva.de"
    assert normalize_address("12 Main Street, São Paulo") == "12 main st sao paulo"
    assert normalize_generic(" A   B ") == "a b"


def test_normalizer_registry_custom_field():
    registry = NormalizerRegistry()
    registry.register("sku", lambda value: str(value).replace("-", "").lower())
    assert registry.normalize("sku", "AB-12") == "ab12"
    with pytest.raises(ValueError):
        registry.register("", str)


def test_similarity_helpers():
    assert levenshtein_ratio("abc", "abc") == 1.0
    assert levenshtein_ratio("", "abc") == 0.0
    assert 0 < levenshtein_ratio("kitten", "sitten") < 1
    assert token_similarity("jane doe", "doe jane") == 1.0
    assert token_similarity("", "jane") == 0.0


def test_field_rule_validation():
    with pytest.raises(ValueError):
        FieldRule(0)


def test_similarity_ambiguous_and_missing_identifiers():
    rules = {
        "name": FieldRule(0.6, fuzzy=True),
        "email": FieldRule(0.4, fuzzy=False, identifier=True, veto_on_conflict=True),
    }
    engine = SimilarityEngine(rules=rules, policy=DecisionPolicy(match_threshold=0.95, ambiguous_threshold=0.5))
    a = EntityRecord("a", "x", {"name": "Jane Doe", "email": "j@example.com"})
    b = EntityRecord("b", "y", {"name": "Jane D", "email": "j@example.com"})
    assert engine.compare(a, b).status in {"match", "ambiguous"}

    c = EntityRecord("c", "x", {"name": "Jane Doe"})
    d = EntityRecord("d", "y", {"name": "Jane Doe"})
    decision = engine.compare(c, d)
    assert decision.status == "rejected"
    assert decision.veto_reason == "no identifier evidence"


def test_similarity_identifier_conflict_veto_reason():
    engine = SimilarityEngine()
    a = EntityRecord("a", "x", {"name": "Jane", "email": "a@example.com"})
    b = EntityRecord("b", "y", {"name": "Jane", "email": "b@example.com"})
    decision = engine.compare(a, b)
    assert decision.status == "rejected"
    assert "email" in (decision.veto_reason or "")


def test_blocking_validation_and_oversized_bucket():
    with pytest.raises(ValueError):
        BlockingIndex(max_bucket_size=1)
    with pytest.raises(ValueError):
        BlockingIndex(phone_suffix_length=3)

    records = [EntityRecord(str(i), "x", {"name": "Same Name"}) for i in range(4)]
    blocker = BlockingIndex(max_bucket_size=2)
    assert blocker.candidate_pairs(records) == []
    assert blocker.last_stats.skipped_oversized_buckets > 0


def test_blocking_email_phone_and_deduplication():
    a = EntityRecord("a", "x", {"email": "abc@example.com", "phone": "1112223333"})
    b = EntityRecord("b", "y", {"email": "abc@example.com", "phone": "0002223333"})
    pairs = BlockingIndex().candidate_pairs([b, a])
    assert len(pairs) == 1
    assert pairs[0][0].record_id == "a"


def test_jsonl_and_unified_adapter(tmp_path: Path):
    path = tmp_path / "rows.jsonl"
    path.write_text('{"id":"1","name":"A"}\n\n{"id":"2","name":"B"}\n', encoding="utf-8")
    records = read_jsonl(path)
    assert [r.record_id for r in records] == ["1", "2"]
    assert len(read_records(path)) == 2

    ndjson = tmp_path / "rows.ndjson"
    ndjson.write_text('{"id":"3","name":"C"}\n', encoding="utf-8")
    assert read_records(ndjson)[0].record_id == "3"


def test_adapter_errors(tmp_path: Path):
    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="header"):
        read_csv(empty)

    bad_json = tmp_path / "bad.json"
    bad_json.write_text('{"id": 1}', encoding="utf-8")
    with pytest.raises(ValueError, match="list"):
        read_json(bad_json)

    rows = tmp_path / "bad.jsonl"
    rows.write_text("not-json\n", encoding="utf-8")
    with pytest.raises(ValueError, match="line 1"):
        read_jsonl(rows)

    object_line = tmp_path / "object.jsonl"
    object_line.write_text("[]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="object"):
        read_jsonl(object_line)

    unsupported = tmp_path / "x.txt"
    unsupported.write_text("x")
    with pytest.raises(ValueError, match="unsupported"):
        read_records(unsupported)


def test_read_records_csv_json_sources(tmp_path: Path):
    csv_path = tmp_path / "people.csv"
    csv_path.write_text("id,name\n1,A\n", encoding="utf-8")
    assert read_records(csv_path)[0].source == "people"

    json_path = tmp_path / "people.json"
    json_path.write_text('[{"id":"2","name":"B"}]', encoding="utf-8")
    assert read_records(json_path)[0].source == "people"


def test_union_find_paths_and_determinism():
    uf = UnionFind(["b", "a", "c"])
    root = uf.union("b", "a")
    assert root == "a"
    uf.union("a", "c")
    assert uf.find("b") == uf.find("c")
    assert uf.union("a", "c") == uf.find("a")


def test_empty_reconciliation():
    result = Reconciler().reconcile([])
    assert result.metrics["input_records"] == 0
    assert result.clusters == []


def test_validation_missing_id_and_non_mapping_fields():
    with pytest.raises(ValueError, match="required"):
        Reconciler().reconcile([EntityRecord("", "crm", {})])
    # dataclass type hints are not runtime guards; exercise explicit validation.
    broken = EntityRecord("1", "crm", {})
    object.__setattr__(broken, "fields", [])
    with pytest.raises(ValueError, match="mappings"):
        Reconciler().reconcile([broken])


def test_transitive_identifier_conflict_is_blocked():
    # A-B match by email, B-C match by phone. A and C carry incompatible emails.
    records = [
        EntityRecord("a", "crm", {"name": "Jane Doe", "email": "a@example.com"}),
        EntityRecord("b", "crm", {"name": "Jane Doe", "email": "a@example.com", "phone": "5551111"}),
        EntityRecord("c", "billing", {"name": "Jane Doe", "email": "c@example.com", "phone": "5551111"}),
    ]
    result = Reconciler().reconcile(records)
    assert result.metrics["blocked_merges"] >= 1
    assert result.metrics["clusters"] == 2
    assert result.warnings


def test_transitive_guard_can_be_disabled():
    policy = DecisionPolicy(prevent_transitive_identifier_conflicts=False)
    records = [
        EntityRecord("a", "crm", {"name": "Jane Doe", "email": "a@example.com"}),
        EntityRecord("b", "crm", {"name": "Jane Doe", "email": "a@example.com", "phone": "5551111"}),
        EntityRecord("c", "billing", {"name": "Jane Doe", "email": "c@example.com", "phone": "5551111"}),
    ]
    result = Reconciler(policy=policy).reconcile(records)
    assert result.metrics["clusters"] == 1


def test_custom_source_priority_changes_canonical_value():
    priority = SourcePriority({"billing": 100, "crm": 1})
    records = [
        EntityRecord("1", "crm", {"name": "Jane", "email": "j@example.com", "city": "A"}),
        EntityRecord("2", "billing", {"name": "Jane", "email": "j@example.com", "city": "B"}),
    ]
    result = Reconciler(source_priority=priority).reconcile(records)
    assert result.clusters[0].fields["city"] == "B"
    assert result.conflicts[0].values[0].record_id in {"1", "2"}


def test_result_is_json_serializable():
    records = [
        EntityRecord("1", "crm", {"name": "Jane", "email": "j@example.com"}),
        EntityRecord("2", "billing", {"name": "Jane", "email": "j@example.com"}),
    ]
    payload = Reconciler().reconcile(records).to_dict()
    json.dumps(payload)
    assert payload["clusters"][0]["confidence"] > 0


def test_cli_writes_output_and_compact_mode(tmp_path: Path):
    source = tmp_path / "input.json"
    source.write_text('[{"id":"1","source":"crm","name":"Jane"}]', encoding="utf-8")
    output = tmp_path / "nested" / "out.json"
    code = run_cli(["reconcile", str(source), "--output", str(output), "--no-pretty"])
    assert code == 0
    assert output.exists()
    assert "\n  " not in output.read_text(encoding="utf-8")


def test_cli_requires_input_and_version():
    with pytest.raises(SystemExit):
        run_cli(["reconcile"])
    with pytest.raises(SystemExit) as exc:
        parse_args(["--version"])
    assert exc.value.code == 0


def test_service_health_and_reconcile():
    client = TestClient(app)
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["version"]

    response = client.post(
        "/v1/reconcile",
        json={
            "records": [
                {"record_id": "1", "source": "crm", "fields": {"name": "Jane", "email": "j@example.com"}},
                {"record_id": "2", "source": "billing", "fields": {"name": "Jane", "email": "j@example.com"}},
            ]
        },
    )
    assert response.status_code == 200
    assert response.json()["metrics"]["clusters"] == 1


def test_service_rejects_bad_payload_and_duplicate_ids():
    client = TestClient(app)
    assert client.post("/v1/reconcile", json={"records": []}).status_code == 422
    duplicate = {
        "records": [
            {"record_id": "x", "source": "a", "fields": {}},
            {"record_id": "x", "source": "b", "fields": {}},
        ]
    }
    response = client.post("/v1/reconcile", json=duplicate)
    assert response.status_code == 422
    assert "globally unique" in response.json()["detail"]
