from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AudioBandShare(BaseModel):
    hz_low: float
    hz_high: float
    energy_share: float = Field(..., ge=0.0, le=1.0)


class AudioAnalysisResult(BaseModel):
    duration_sec: float
    sample_rate: int
    bands: list[AudioBandShare]
    dominant_band_hz: str
    acoustic_band_hz: str | None = None
    acoustic_anomaly: bool = False
    edge_hypothesis: str
    crest_factor: float
    method: str = "stft_band_energy_v1"
    caveat: str = (
        "Heuristic spectral summary only—not a certified fault classifier. "
        "Validate with qualified personnel, vibration, and thermal data."
    )


class AnomalyPayload(BaseModel):
    machine_id: str = Field(..., description="Stable asset identifier, e.g. conveyance-main-drive-1")
    timestamp_iso: str | None = None
    asset_class: str | None = Field(
        None,
        description="Plant asset category for routing and RAG, e.g. conveyor, stamping_press, cnc",
    )
    thermal_c: float | None = None
    thermal_baseline_c: float | None = None
    acoustic_anomaly: bool = False
    acoustic_band_hz: str | None = None
    rgb_summary: str | None = None
    trigger_reason: str | None = None
    notes: str | None = None
    edge_hypothesis: str | None = Field(
        None,
        description="Short edge-side fused hypothesis for central brain / RAG query expansion",
    )
    thermal_image_ref: str | None = Field(
        None,
        description="URI or opaque id to thermal frame artifact (prefer no embedded credentials)",
    )
    optical_image_ref: str | None = Field(
        None,
        description="URI or opaque id to RGB/optical frame artifact",
    )
    spectrogram_ref: str | None = Field(
        None,
        description="URI or opaque id to audio spectrogram or feature artifact",
    )


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
