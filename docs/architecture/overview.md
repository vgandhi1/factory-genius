# System Architecture: Conveyance & Rotary Predictive Maintenance

## 1. High-Level System Overview

Edge **data fusion** on conveyance lines (drive stations, rotary units, transfer equipment) feeds a cloud or on-prem **inference** layer augmented by **RAG** so operators see not only *what* looks wrong on **shafts and rotating parts**, but *whether* to act in a **preventive** window or treat the event as **breakdown** maintenance, with cited procedures.

## 2. Layer 1: The Edge Sensor Node (Data Fusion)

* **Hardware suite (per monitored zone):**

  * NVIDIA Jetson Nano / Xavier NX (or equivalent edge AI).
  * Thermal camera (e.g. FLIR Lepton class) aimed at **bearings, gearcases, shaft couplings**.
  * Directional microphone for **bearing, belt, idler, and gear-mesh** bands.
  * RGB camera for **misalignment, belt wander, roller wear, guard-off anomalies**.

* **Edge processing:**

  * **Continuous monitoring:** DSP + thresholds on acoustic bands and thermal drift vs baseline at **line speed**.
  * **Trigger & fuse:** On breach, capture a short **spectrogram**, **thermal frame**, and **RGB frame** into one payload (with asset ID and speed/load context).

## 3. Layer 2: RAG & Inference Backend

* **Transport:** MQTT to central analytics (topic pattern `conveyance/{asset_id}/anomaly`).
* **Multimodal model:** VLM or API capable of spectrogram + imagery + text (roadmap: local or gated cloud).
* **RAG store:** Chunks from manuals, PM schedules, **shaft alignment** SOPs, bearing replacement guides, site history.
* **Query example:** Asset `sortation-rotary-2` + "rising 3–6 kHz + hotspot at drive-end pillow block" retrieves idler/bearing and **misalignment** excerpts.
* **Prompt intent:** Reliability engineer persona—diagnose likely **rotary** failure mode, state **preventive vs breakdown** recommendation, list **stepwise** actions from retrieved text only.

## 4. Layer 3: Presentation & Action

* **Dashboard / mobile:** Diagnosis, evidence thumbnails, **maintenance mode** (preventive vs breakdown), cited manual sections.
* **EAM:** Work order creation with labor/parts codes (prototype: stub only).

## 5. Architecture Diagram (Text)

```text
[Conveyance line / rotary module]
   |--- (Thermal on bearing housing) --> |
   |--- (Mic: shaft / roller / belt) ---> | [Jetson edge node]
   |--- (RGB: belt path / coupling) -----> |     DSP + thresholds
                              |
                    [Anomaly payload]
                              v
                 [Central inference server]
                    /                    \
           [RAG: manuals / PM / history]  [VLM / LLM synthesis]
                    \                    /
                         [Diagnostic WO + PM vs breakdown flag]
                              |
              +---------------+---------------+
              |                               |
    [Technician app / dashboard]     [EAM system]
```

## 6. Reference implementation mapping (this repository)

| Architecture layer | Prototype component |
|--------------------|---------------------|
| Edge node | `scripts/edge_simulator.py` — JSON payloads to `conveyance/{asset_id}/anomaly` |
| MQTT | Mosquitto via `docker-compose.yml` |
| RAG | BM25 over `data/knowledge/` (`backend/app/rag_engine.py`) |
| VLM / reasoning | Optional OpenAI Chat; else template from retrieval + metrics |
| Dashboard | `web/` — React UI |
| EAM | Not implemented |

## 7. End-to-end demo flow

1. Start Mosquitto and the API (see root `README.md`).
2. Run the edge simulator for a conveyance asset ID.
3. Backend retrieves chunks, labels **preventive vs breakdown** in the narrative template, stores events.
4. Open the dashboard for live feed and citations.

## 8. Future production hardening

* Embeddings + Milvus/Qdrant; audited multimodal API; mTLS on MQTT; strict log redaction and retention per product plan.
