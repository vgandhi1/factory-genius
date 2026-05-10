# Product Plan: "Factory Genius" Conveyance & Rotary Maintenance Node

## 1. Executive Summary

"Factory Genius" turns **reactive (breakdown) maintenance** into **condition-aware intelligence** for **conveyance systems**—lines, transfer units, drive stations, and **rotary subsystems** (shafts, pulleys, idlers, rollers, sprockets, turntables). By retrofitting critical zones with a multimodal edge sensor suite (thermal, optical, acoustic) on an NVIDIA Jetson-class module, the product spots degradation on **shafts and rotating components** before hard failure. A Retrieval-Augmented Generation (RAG) pipeline, optionally paired with a multimodal VLM, classifies whether the evidence supports **preventive / condition-based** action (schedule intervention, replace on trend) versus **breakdown** response (stop line, emergency work order), and retrieves the right procedure for technicians.

## 2. Product Objectives & Key Results (OKRs)

### Objective 1: Cut unplanned stoppages on conveyance assets

* **KR1:** Increase Overall Equipment Effectiveness (OEE) by **12%** on monitored lines (fewer surprise shaft/bearing/seal failures).
* **KR2:** Reduce Mean Time To Repair (MTTR) by **30%** by auto-retrieving alignment, lubrication, and replacement SOPs at alert time.

### Objective 2: Make preventive vs breakdown decisions explicit

* **KR3:** Cut time spent hunting manuals and line drawings for **drive and rotary assemblies** by **80%**.
* **KR4:** For **85%** of detected anomalies, auto-generate actionable tickets that state **recommended maintenance mode** (preventive window vs immediate breakdown response) and cite OEM or site-approved excerpts.

## 3. Target Users & Stakeholders

* **Maintenance Technicians:** Receive alerts, **preventive vs breakdown** guidance, and cited procedures on mobile or rugged tablets.
* **Reliability Engineers:** Trend thermal, acoustic, and visual features on **shafts and rotary trains** to refine PM intervals and spares.
* **Plant / Operations Directors:** Prioritize line uptime and balance **scheduled PM** against **emergency** workload on conveyance assets.

## 4. Phased Implementation Roadmap

### Phase 1: Data Harvesting & Baseline Creation (Months 1–3)

* Deploy sensor suites (thermal, audio, optical) on **five high-impact conveyance zones** (e.g. main drive, tension station, merge, sortation rotary, elevation transfer).
* Run in **listen-only** mode; capture healthy baselines (acoustic bands, thermal steady-state, visual belt/roller appearance) **per asset and speed**.

### Phase 2: RAG Pipeline Integration (Months 4–5)

* Ingest OEM manuals, line-specific PM checklists, past **shaft/alignment/bearing** work orders, and approved diagrams into a vector store.
* Tune multimodal prompts to fuse sensor context with retrieval and to output **maintenance strategy** (preventive vs breakdown) with justification.

### Phase 3: Active Alerting Pilot (Months 6–8)

* Push notifications to maintenance teams; capture **thumbs up/down** on diagnosis and PM vs breakdown classification for RLHF-style improvement.

### Phase 4: Autonomous Ticketing (Month 9+)

* Integrate with EAM (e.g. Maximo, SAP PM); optionally trigger **parts** (bearings, couplings, belts) when degradation trends cross policy thresholds.

## 5. Security & Privacy

* **Acoustic privacy:** Edge filtering limits capture to **machine-band** energy; voice-band rejection stays on-device where required by policy.
* **Reference implementation:** The repo’s local demo must not log credentials, full manual bodies in production logs, or unredacted payloads to untrusted sinks. User-facing errors stay generic.

## 6. Reference implementation (this repository)

Phase **1–2** style prototype: simulated edge payloads, **MQTT** on topic `conveyance/{asset_id}/anomaly`, BM25 RAG over `data/knowledge/`, optional OpenAI narrative, and a technician dashboard. It does **not** replace certified edge firmware, production VLM deployment, or EAM integrations.

**In scope**

* Simulated multimodal payloads for conveyance / rotary assets.
* MQTT ingest, REST/WebSocket API, BM25 retrieval, optional LLM.

**Out of scope (roadmap)**

* Production DSP privacy guarantees, fleet-scale vector DB, SAP/Maximo connectors, full RLHF loop.
