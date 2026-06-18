from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from .diagnosis import retrieve_chunks, synthesize_diagnosis
from .rag_engine import ManualRAG
from .schemas import AnomalyPayload, DiagnosticEvent


def _work_order_stub(payload: AnomalyPayload) -> dict[str, Any]:
    return {
        "asset": payload.machine_id,
        "priority": "P1" if (payload.thermal_c or 0) > 80 else "P2",
        "title": f"Inspect {payload.machine_id}: {payload.trigger_reason or 'anomaly'}",
        "eam_status": "not_integrated",
    }


def build_event(rag: ManualRAG, payload: AnomalyPayload, top_k: int = 5) -> DiagnosticEvent:
    """Retrieve context, synthesize diagnosis, and assemble a DiagnosticEvent.

    Blocking: ``synthesize_diagnosis`` may call an external LLM. Run off the event
    loop (``asyncio.to_thread``) and off the MQTT network thread.
    """
    retrieved = retrieve_chunks(rag, payload, top_k=top_k)
    title, body = synthesize_diagnosis(payload, retrieved)
    return DiagnosticEvent(
        id=str(uuid.uuid4()),
        received_at=datetime.now(timezone.utc),
        payload=payload,
        diagnosis_title=title,
        diagnosis_body=body,
        retrieved=retrieved,
        work_order_stub=_work_order_stub(payload),
    )
