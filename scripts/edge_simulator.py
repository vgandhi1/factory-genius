#!/usr/bin/env python3
"""Simulate edge node publishing conveyance-line multimodal anomaly payloads over MQTT."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt


def _payload(machine_id: str, scenario: str) -> dict:
    ts = datetime.now(timezone.utc).isoformat()
    if scenario == "drive_shaft":
        return {
            "machine_id": machine_id,
            "timestamp_iso": ts,
            "thermal_c": 86.0,
            "thermal_baseline_c": 48.0,
            "acoustic_anomaly": True,
            "acoustic_band_hz": "2000-4000",
            "rgb_summary": "Heat shimmer at main drive pillow block; belt tracking nominal.",
            "trigger_reason": "drive_shaft_thermal_and_bearing_acoustic",
        }
    if scenario == "merge_rotary":
        return {
            "machine_id": machine_id,
            "timestamp_iso": ts,
            "thermal_c": 72.0,
            "thermal_baseline_c": 44.0,
            "acoustic_anomaly": True,
            "acoustic_band_hz": "500-1200",
            "rgb_summary": "Merge table star wheel chatter visible; guard clearance tight.",
            "trigger_reason": "rotary_unit_misalignment_trend",
        }
    return {
        "machine_id": machine_id,
        "timestamp_iso": ts,
        "thermal_c": 55.0,
        "thermal_baseline_c": 50.0,
        "acoustic_anomaly": False,
        "rgb_summary": "Routine heartbeat; no anomaly.",
        "trigger_reason": "heartbeat",
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Publish Factory Genius anomaly payload to MQTT")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=1883)
    p.add_argument("--machine-id", default="conveyance-main-drive-1")
    p.add_argument(
        "--scenario",
        choices=("drive_shaft", "merge_rotary", "heartbeat"),
        default="drive_shaft",
    )
    args = p.parse_args()

    topic = f"conveyance/{args.machine_id}/anomaly"
    body = _payload(args.machine_id, args.scenario)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="factory-genius-sim")
    try:
        client.connect(args.host, args.port, keepalive=30)
    except OSError as e:
        print(f"Could not connect to MQTT at {args.host}:{args.port}: {e}", file=sys.stderr)
        return 1

    client.loop_start()
    time.sleep(0.3)
    info = client.publish(topic, json.dumps(body), qos=1)
    info.wait_for_publish()
    print(f"Published to {topic}: {body['trigger_reason']}")
    client.loop_stop()
    client.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
