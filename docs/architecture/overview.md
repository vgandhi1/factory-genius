# System Architecture: Auto-Plant Multimodal Maintenance Copilot

## 1. High-Level System Overview

**Stamping presses, conveyor systems, and CNC machines** are typical loss leaders when they trip unexpectedly. This architecture describes a **generative-AI maintenance copilot**: a **Jetson-class edge** fuses **thermal (FLIR-class), optical (RGB), and acoustic** streams to detect anomalies; a **central brain** runs **VLM + audio/spectrogram reasoning** (industry-tuned) and **RAG** over manuals so technicians see not only *what* is wrong but *how to fix it*—with **preventive vs breakdown** framing and **cited** procedures.

## 2. Layer 1: The Edge (Jetson / smart camera) — decentralized fusion

* **Hardware suite (per critical machine or zone):**

  * NVIDIA Jetson (Nano / Orin family or equivalent) as the **fusion and trigger** node.
  * **Standard optical camera** — belt wander, misalignment, guard-off, **CNC** way covers/chip load cues, **press** tooling area visibility (site policy permitting).
  * **FLIR-class thermal camera** — bearings, **spindle** cartridges, **slide/bolster** hotspots, motor and drive-end trains.
  * **Directional microphone** — bearing grind, gear mesh, **chatter**, leak hiss; processed to **spectrogram** or band-energy features on-device.

* **Edge processing:**

  * **Continuous monitoring:** DSP on audio; thermal drift vs baseline; optional lightweight vision cues—**aligned in time** with machine state (speed, program, tonnage where available).
  * **Trigger & fuse:** On breach (e.g. **sudden thermal step** coincident with **grinding energy** in a fault band), assemble a **fused anomaly packet**: references or compact encodings for **thermal image**, **optical image**, **audio spectrogram**, plus **asset id**, **asset class** (conveyor / press / CNC), timestamp, and trigger hypothesis. Large blobs are typically **object-store URIs** or sidecar uploads, not raw multi-megabyte JSON in MQTT.

## 3. Layer 2: The brain — VLM + audio model + RAG

* **Transport:** MQTT (or equivalent) to central analytics; topic pattern in this repo: `conveyance/{asset_id}/anomaly` (evolvable to `plant/{site}/{asset_class}/{asset_id}/anomaly`).
* **Multimodal inference (target):**

  * **VLM path:** Thermal + RGB (and crops) for spatial hotspots, misalignment, and contextual scene understanding.
  * **Audio path:** Spectrogram or embedding from **directional mic** features for bearing wear, chatter, and impulsive faults—**combined** with VLM outputs in a fusion head or orchestrated prompt.
* **RAG store:** Chunks from OEM manuals, PM schedules, **press / CNC / conveyor** SOPs, alignment and lubrication guides, site history.
* **Query example:** Asset `stamping-press-3` + fused summary "slide guide hotspot + 2–4 kHz grind" retrieves **gib adjustment / lubrication** and **tonnage verification** excerpts; asset `cnc-hmc-7` + "spindle thermal + chatter band" retrieves **tooling / drawbar / bearing** procedures.
* **Prompt intent:** Reliability engineer persona—hypothesize failure mode from **multimodal** evidence, state **preventive vs breakdown** recommendation, list **stepwise** actions grounded in retrieved text (no invented part numbers).

## 4. Layer 3: Presentation & Action

* **Dashboard / mobile:** Diagnosis, evidence thumbnails, **maintenance mode** (preventive vs breakdown), cited manual sections.
* **EAM:** Work order creation with labor/parts codes (prototype: stub only).

## 5. Architecture Diagram (Text)

```text
[Conveyor / press / CNC — critical zone]
   |--- (FLIR-class thermal) -----------> |
   |--- (RGB optical) --------------------> | [Jetson edge — fusion]
   |--- (Directional mic -> spectrogram) -> |     anomaly trigger
                              |
              [Fused packet: thermal + optical + spectrogram + meta]
                              v
                 [Central inference — "brain"]
                    /            |            \
        [Audio / spectrogram     [VLM on       [RAG: manuals /
         model or encoder]       thermal+RGB]   PM / history]
                    \            |            /
                         [Fused diagnosis + PM vs breakdown + citations]
                              |
              +---------------+---------------+
              |                               |
    [Technician app / dashboard]     [EAM system]
```

## 6. Fused anomaly packet (target contract)

Production payloads should carry **references** to thermal, optical, and spectrogram artifacts (object storage URI, content hash, or sidecar upload id)—not large inline blobs on MQTT. Optional metadata in the API evolution includes **`asset_class`** (e.g. `conveyor`, `stamping_press`, `cnc`), **program / tonnage / spindle speed** context where available, and a short **edge hypothesis** string for RAG query expansion. The reference repo’s `AnomalyPayload` accepts optional ref fields for forward compatibility.

## 7. Reference implementation mapping (this repository)

| Architecture layer | Prototype component |
|--------------------|---------------------|
| Edge node | `scripts/edge_simulator.py` — JSON payloads to `conveyance/{asset_id}/anomaly` |
| MQTT | Mosquitto via `docker-compose.yml` |
| RAG | BM25 over `data/knowledge/` (`backend/app/rag_engine.py`) |
| VLM + audio / reasoning | **Roadmap:** VLM + spectrogram-aware model on fused artifacts; **prototype:** optional OpenAI **text** Chat from retrieval + scalar/text evidence; else template |
| Dashboard | `web/` — React UI |
| EAM | Not implemented |

## 8. End-to-end demo flow

1. Start Mosquitto and the API (see root `README.md`).
2. Run the edge simulator for a conveyance asset ID.
3. Backend retrieves chunks, labels **preventive vs breakdown** in the narrative template, stores events.
4. Open the dashboard for live feed and citations.

## 9. Future production hardening

* Embeddings + Milvus/Qdrant; audited multimodal API; mTLS on MQTT; strict log redaction and retention per product plan.
