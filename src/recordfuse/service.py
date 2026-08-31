"""FastAPI transport for RecordFuse."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from . import __version__
from .models import EntityRecord
from .reconcile import Reconciler

app = FastAPI(
    title="RecordFuse",
    version=__version__,
    description="Deterministic and explainable entity resolution API",
)


class RecordIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    record_id: str = Field(min_length=1, max_length=256)
    source: str = Field(min_length=1, max_length=128)
    fields: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReconcileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    records: list[RecordIn] = Field(min_length=1, max_length=10_000)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.post("/v1/reconcile", tags=["reconciliation"])
def reconcile(request: ReconcileRequest) -> dict[str, Any]:
    records = [
        EntityRecord(r.record_id, r.source, r.fields, r.metadata) for r in request.records
    ]
    try:
        return Reconciler().reconcile(records).to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
