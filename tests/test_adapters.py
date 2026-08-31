import pytest
from recordfuse.adapters import read_csv, read_json
from recordfuse.models import EntityRecord


def test_read_csv(tmp_path):
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("id,source,name,email,phone\n1,crm,Jane Doe,jane@example.com,123456\n")

    records = read_csv(str(csv_file))
    assert len(records) == 1
    assert isinstance(records[0], EntityRecord)
    assert records[0].record_id == "1"


def test_read_json(tmp_path):
    json_file = tmp_path / "test.json"
    json_file.write_text('[{"id": "1", "source": "billing", "name": "Jane Doe"}]')

    records = read_json(str(json_file))
    assert len(records) == 1
    assert isinstance(records[0], EntityRecord)
    assert records[0].record_id == "1"
