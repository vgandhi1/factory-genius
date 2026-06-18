from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .audio_analysis import analyze_audio_bytes, anomaly_payload_from_audio
from .config import settings
from .mqtt_worker import start_mqtt_thread
from .rag_engine import ManualRAG
from .schemas import AnomalyPayload, AudioAnalysisResult, DiagnosticEvent
from .store import EventStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

event_store = EventStore()
rag = ManualRAG(settings.knowledge_dir)
event_queue: asyncio.Queue[DiagnosticEvent] = asyncio.Queue()
_ws_clients: set[WebSocket] = set()


async def _broadcast_event(event: DiagnosticEvent) -> None:
    dead: list[WebSocket] = []
    payload = json.dumps(event.model_dump(mode="json"), default=str)
    for ws in _ws_clients:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _ws_clients.discard(ws)


async def _queue_pump() -> None:
    while True:
        ev = await event_queue.get()
        await _broadcast_event(ev)


@asynccontextmanager
async def lifespan(app: FastAPI):
    n = rag.load()
    logger.info("RAG loaded %s chunks from %s", n, settings.knowledge_dir)
    loop = asyncio.get_running_loop()
    pump = asyncio.create_task(_queue_pump())
    start_mqtt_thread(rag, event_store, loop, event_queue)
    yield
    pump.cancel()


app = FastAPI(title="Factory Genius API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _ingest_diagnostic_event(payload: AnomalyPayload) -> DiagnosticEvent:
    from datetime import datetime, timezone
    import uuid

    from .diagnosis import retrieve_chunks, synthesize_diagnosis

    retrieved = retrieve_chunks(rag, payload, top_k=5)
    title, diag_body = synthesize_diagnosis(payload, retrieved)
    event = DiagnosticEvent(
        id=str(uuid.uuid4()),
        received_at=datetime.now(timezone.utc),
        payload=payload,
        diagnosis_title=title,
        diagnosis_body=diag_body,
        retrieved=retrieved,
        work_order_stub={
            "asset": payload.machine_id,
            "priority": "P1" if (payload.thermal_c or 0) > 80 else "P2",
            "title": f"Inspect {payload.machine_id}: {payload.trigger_reason or 'anomaly'}",
            "eam_status": "not_integrated",
        },
    )
    event_store.add(event)
    await event_queue.put(event)
    return event


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "rag_chunks": rag.chunk_count}


@app.get("/api/events")
def list_events() -> list[dict[str, Any]]:
    return [e.model_dump(mode="json") for e in event_store.list()]


@app.post("/api/demo/ingest")
async def demo_ingest(payload: AnomalyPayload) -> JSONResponse:
    """HTTP fallback to simulate MQTT when broker is unavailable (dev only)."""
    event = await _ingest_diagnostic_event(payload)
    return JSONResponse(event.model_dump(mode="json"))


@app.post("/api/audio/analyze", response_model=AudioAnalysisResult)
async def audio_analyze(
    audio: UploadFile = File(..., description="WAV/FLAC machinery recording"),
) -> AudioAnalysisResult:
    """STFT band-energy heuristic over uploaded audio (no RAG)."""
    data = await audio.read()
    try:
        return await asyncio.to_thread(analyze_audio_bytes, data, settings.max_audio_upload_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception:
        logger.exception("Audio analysis failed")
        raise HTTPException(status_code=400, detail="Audio analysis failed.") from None


@app.post("/api/audio/diagnose")
async def audio_diagnose(
    machine_id: str = Form(...),
    audio: UploadFile = File(..., description="WAV/FLAC machinery recording"),
    asset_class: str | None = Form(None),
    thermal_c: float | None = Form(None),
    thermal_baseline_c: float | None = Form(None),
    rgb_summary: str | None = Form(None),
) -> JSONResponse:
    """Analyze uploaded machinery audio, run BM25 (+ optional LLM), store diagnostic event."""
    data = await audio.read()
    try:
        analysis = await asyncio.to_thread(analyze_audio_bytes, data, settings.max_audio_upload_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception:
        logger.exception("Audio analysis failed")
        raise HTTPException(status_code=400, detail="Audio analysis failed.") from None

    ac = asset_class.strip() if asset_class and asset_class.strip() else None
    rs = rgb_summary.strip() if rgb_summary and rgb_summary.strip() else None
    payload = anomaly_payload_from_audio(
        machine_id,
        analysis,
        asset_class=ac,
        thermal_c=thermal_c,
        thermal_baseline_c=thermal_baseline_c,
        rgb_summary=rs,
    )
    event = await _ingest_diagnostic_event(payload)
    return JSONResponse(event.model_dump(mode="json"))


@app.websocket("/ws/events")
async def ws_events(ws: WebSocket) -> None:
    await ws.accept()
    _ws_clients.add(ws)
    try:
        for e in event_store.list()[:50]:
            await ws.send_text(json.dumps(e.model_dump(mode="json"), default=str))
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _ws_clients.discard(ws)


_REPO_ROOT = Path(__file__).resolve().parents[2]
_spa_dist = _REPO_ROOT / "web" / "dist"
if _spa_dist.is_dir():
    app.mount("/", StaticFiles(directory=str(_spa_dist), html=True), name="spa")
