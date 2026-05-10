from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AnomalyPayload(BaseModel):
    machine_id: str = Field(..., description="Stable asset identifier, e.g. conveyance-main-drive-1")
    timestamp_iso: str | None = None
    thermal_c: float | None = None
    thermal_baseline_c: float | None = None
    acoustic_anomaly: bool = False
    acoustic_band_hz: str | None = None
    rgb_summary: str | None = None
    trigger_reason: str | None = None
    notes: str | None = None


class RetrievedChunk(BaseModel):
    doc_id: str
    title: str
    excerpt: str
    score: float


class DiagnosticEvent(BaseModel):
    id: str
    received_at: datetime
    payload: AnomalyPayload
    diagnosis_title: str
    diagnosis_body: str
    retrieved: list[RetrievedChunk]
    work_order_stub: dict[str, Any]
