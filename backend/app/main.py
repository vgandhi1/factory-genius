from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .mqtt_worker import start_mqtt_thread
from .rag_engine import ManualRAG
from .schemas import AnomalyPayload, DiagnosticEvent
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


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "rag_chunks": rag.chunk_count}


@app.get("/api/events")
def list_events() -> list[dict[str, Any]]:
    return [e.model_dump(mode="json") for e in event_store.list()]


@app.post("/api/demo/ingest")
async def demo_ingest(payload: AnomalyPayload) -> JSONResponse:
    """HTTP fallback to simulate MQTT when broker is unavailable (dev only)."""
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
