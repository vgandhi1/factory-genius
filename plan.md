# Factory Genius — Implementation Plan

**Status:** Active development — reference prototype, T1 compliance in progress  
**Last updated:** 2026-06-17  
**Tier:** T1 Dev → T2 Release-ready (LICENSE added; presentation.html pending)

---

## Goal

Generative-AI **maintenance copilot** for auto-plant critical assets (conveyors, stamping presses, CNC): ingest fused edge evidence (thermal, acoustic, optical summaries), retrieve cited procedures via RAG, and return **preventive vs breakdown** guidance to technicians. Runnable locally without real Jetson hardware or EAM integration.

---

## Current status

| Area | Status | Notes |
|------|--------|-------|
| MQTT anomaly ingest | ✅ Done | `conveyance/{asset_id}/anomaly` via Mosquitto |
| BM25 RAG over Markdown manuals | ✅ Done | `data/knowledge/` (3 files) |
| Template diagnosis + preventive/breakdown heuristics | ✅ Done | `diagnosis.py` |
| Optional OpenAI LLM synthesis | ✅ Done | Falls back to template on failure |
| React dashboard + WebSocket feed | ✅ Done | `web/` |
| Edge simulator | ✅ Done | `scripts/edge_simulator.py` |
| Machinery audio STFT analysis | ✅ Done | `backend/app/audio_analysis.py` |
| LLM prompt `<data>` delimiters | ✅ Done | Per `governance/standards/08-AI-SECURITY.md` |
| Root `plan.md` + `.env.example` + CI | ✅ Done | This milestone |
| Unit tests | ✅ Done | `tests/` — diagnosis, RAG, audio guards |
| Vector DB / VLM / spectrogram model | ⏳ Roadmap | Phase 2 |
| EAM (SAP PM / Maximo) | ⏳ Roadmap | Stub only today |
| Jetson edge firmware | ⏳ Roadmap | Simulated only |

**Legend:** ✅ done · 🔄 in progress · ⏳ planned · ❌ blocked

---

## Scope

### In scope (this repo)

- Simulated edge payloads → MQTT or HTTP demo ingest
- BM25 retrieval over local maintenance Markdown
- Optional text LLM with grounded citations and template fallback
- Technician dashboard (read-only guidance; work order stub, not EAM writes)
- Heuristic audio STFT band analysis (not a certified classifier)

### Out of scope (roadmap)

- Production Jetson sensor fusion and acoustic privacy filters
- VLM + trained spectrogram/audio model serving
- Fleet-scale vector DB; SAP/Maximo connectors; RLHF loop

---

## Portfolio context

**Separate** from the three-repo Factory AI portfolio (Digital Twin, FactoryOps, VisionGuard). Factory Genius is a **reliability / maintenance vertical** — not OEE ops intelligence or visual defect inspection.

See [`docs/architecture/overview.md`](docs/architecture/overview.md) for target production architecture.

---

## Milestones

### M1 — Runnable prototype ✅

- [x] MQTT + HTTP ingest paths
- [x] BM25 RAG + template diagnosis
- [x] React dashboard with live WebSocket

### M2 — T1 engineering hygiene ✅

- [x] Root `plan.md`, `.env.example`, `.github/workflows/test.yml`
- [x] Restore `docker/mosquitto.conf` for MQTT demo path
- [x] Audio STFT pipeline + upload endpoints
- [x] LLM prompt injection guardrails (`<data>` blocks)
- [x] Unit tests for core logic

### M3 — Release-ready 🔄

- [x] `LICENSE` (MIT)
- [x] `presentation.html` (self-contained deck; GitHub Pages deploy pending)
- [ ] Retrieval golden eval set (nDCG / hit-rate)
- [ ] Gate `/api/demo/ingest` on `ENVIRONMENT=development`

### M4 — Product vision (deferred)

- [ ] pgvector / Qdrant for OEM manual corpus
- [ ] VLM on thermal/RGB/spectrogram artifact refs
- [ ] EAM connector stubs

---

## Architecture decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Retrieval (prototype) | BM25 on local Markdown | No vector infra required for demo |
| LLM | OpenAI-compatible API, optional | Template fallback keeps demo offline-safe |
| Event store | In-memory ring buffer (200) | Prototype; persistence deferred |
| MQTT broker | Mosquitto via Docker Compose | Matches edge pub/sub story |

---

## Open questions

- Publish as standalone public repo only, or link from `factory-system-AI` container README?
- Target Python 3.11 vs 3.12 in CI (currently 3.12)?

---

## Change log

| Date | Change |
|------|--------|
| 2026-06-17 | Add MIT LICENSE; sync README and plan tier |
| 2026-06-17 | T1 cleanup: audio feature, CI, root plan, mosquitto restore, LLM `<data>` delimiters |
| 2026-06-17 | Comprehensive review — [`docs/COMPREHENSIVE-REPORT.md`](docs/COMPREHENSIVE-REPORT.md) |
| Initial | Reference prototype — BM25 RAG + MQTT + dashboard |
