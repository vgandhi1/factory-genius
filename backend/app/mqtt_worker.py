from __future__ import annotations

import asyncio
import json
import logging
import threading
from typing import TYPE_CHECKING, Callable

import paho.mqtt.client as mqtt

from .config import settings
from .events import build_event
from .rag_engine import ManualRAG
from .schemas import AnomalyPayload, DiagnosticEvent

if TYPE_CHECKING:
    from .store import EventStore

logger = logging.getLogger(__name__)


def _parse_payload(raw: bytes) -> AnomalyPayload | None:
    try:
        data = json.loads(raw.decode("utf-8"))
        return AnomalyPayload.model_validate(data)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as e:
        logger.warning("Invalid anomaly payload: %s", type(e).__name__)
        return None


def make_on_message(
    rag: ManualRAG,
    store: EventStore,
    loop: asyncio.AbstractEventLoop,
    event_queue: asyncio.Queue[DiagnosticEvent],
) -> Callable[[mqtt.Client, object, mqtt.MQTTMessage], None]:
    async def _process(payload: AnomalyPayload) -> None:
        # Diagnosis (incl. optional LLM) runs in a worker thread so it never blocks
        # the MQTT network loop nor the asyncio event loop.
        event = await asyncio.to_thread(build_event, rag, payload)
        store.add(event)
        await event_queue.put(event)

    def on_message(_client: mqtt.Client, _userdata: object, message: mqtt.MQTTMessage) -> None:
        payload = _parse_payload(message.payload)
        if payload is None:
            return
        # Hand off to the event loop immediately; do not block loop_forever().
        future = asyncio.run_coroutine_threadsafe(_process(payload), loop)

        def _log_error(fut: object) -> None:
            try:
                future.result()
            except Exception:
                logger.exception("Failed to process diagnostic event")

        future.add_done_callback(_log_error)

    return on_message


def start_mqtt_thread(
    rag: ManualRAG,
    store: EventStore,
    loop: asyncio.AbstractEventLoop,
    event_queue: asyncio.Queue[DiagnosticEvent],
) -> threading.Thread:
    def _run() -> None:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="factory-genius-api")
        client.on_connect = _on_connect
        client.on_message = make_on_message(rag, store, loop, event_queue)

        try:
            client.connect(settings.mqtt_host, settings.mqtt_port, keepalive=60)
        except OSError as e:
            logger.error("MQTT connect failed (%s:%s): %s", settings.mqtt_host, settings.mqtt_port, e)
            return

        client.loop_forever()

    t = threading.Thread(target=_run, name="mqtt-worker", daemon=True)
    t.start()
    return t


def _on_connect(
    client: mqtt.Client,
    _userdata: object,
    _flags: mqtt.ConnectFlags,
    reason_code: mqtt.ReasonCode,
    _properties: object | None = None,
) -> None:
    if reason_code.is_failure:
        logger.error("MQTT connection rejected: %s", reason_code)
        return
    client.subscribe(settings.mqtt_topic_pattern, qos=1)
    logger.info("MQTT subscribed to %s", settings.mqtt_topic_pattern)
