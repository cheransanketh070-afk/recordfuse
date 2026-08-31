"""Data ingestion adapters for CSV, JSON and JSON Lines."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

from .models import EntityRecord


def _record_from_mapping(
    row: dict[str, Any], default_source: str, fallback_id: int
) -> EntityRecord:
    record_id = str(row.get("record_id", row.get("id", fallback_id))).strip()
    source = str(row.get("source") or default_source).strip()
    fields = {key: value for key, value in row.items() if key not in {"id", "record_id", "source"}}
    return EntityRecord(record_id=record_id, source=source, fields=fields)


def read_csv(filepath: str | Path, default_source: str = "csv") -> list[EntityRecord]:
    records: list[EntityRecord] = []
    with Path(filepath).open(mode="r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("CSV input must contain a header row")
        for row in reader:
            records.append(_record_from_mapping(dict(row), default_source, len(records) + 1))
    return records


def read_json(filepath: str | Path, default_source: str = "json") -> list[EntityRecord]:
    with Path(filepath).open(mode="r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError("JSON input must contain a list of records")
    return _mappings_to_records(data, default_source)


def read_jsonl(filepath: str | Path, default_source: str = "jsonl") -> list[EntityRecord]:
    rows: list[dict[str, Any]] = []
    with Path(filepath).open(mode="r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON on line {line_number}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"JSONL line {line_number} must contain an object")
            rows.append(row)
    return _mappings_to_records(rows, default_source)


def _mappings_to_records(rows: Iterable[dict[str, Any]], default_source: str) -> list[EntityRecord]:
    records: list[EntityRecord] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("each record must be an object")
        records.append(_record_from_mapping(row, default_source, len(records) + 1))
    return records


def read_records(filepath: str | Path) -> list[EntityRecord]:
    path = Path(filepath)
    suffix = path.suffix.casefold()
    if suffix == ".csv":
        return read_csv(path, default_source=path.stem)
    if suffix == ".json":
        return read_json(path, default_source=path.stem)
    if suffix in {".jsonl", ".ndjson"}:
        return read_jsonl(path, default_source=path.stem)
    raise ValueError(f"unsupported input format: {path.suffix or '<none>'}")


load_records_from_csv = read_csv
