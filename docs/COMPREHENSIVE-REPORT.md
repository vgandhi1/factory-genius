# Factory Genius — Comprehensive Review Report

**Review date:** 2026-06-17  
**Repository:** `factory-system-AI/Factory-genius/` (git remote: `https://github.com/vgandhi1/factory-genius.git`)  
**Branch:** `main` · **HEAD:** `81c1185` — *Initial commit: Factory Genius predictive maintenance reference stack*  
**Reviewed against:** [`governance/standards/COMPLIANCE.md`](../../../governance/standards/COMPLIANCE.md), [`governance/standards/08-AI-SECURITY.md`](../../../governance/standards/08-AI-SECURITY.md), [`governance/Guardrails/specialized/factory-portfolio/factory-ai-portfolio-guardrails.md`](../../../governance/Guardrails/specialized/factory-portfolio/factory-ai-portfolio-guardrails.md)

---

## Executive summary

**Factory Genius** is a **standalone reference prototype** for a generative-AI **maintenance copilot** aimed at auto-plant critical assets (conveyors, stamping presses, CNC). It is **explicitly separate** from the three-repo Factory AI portfolio (Digital Twin, FactoryOps, VisionGuard) documented in [`factory-system-AI/portfolio/`](../portfolio/).

| Dimension | Assessment |
|-----------|------------|
| **Concept clarity** | Strong — clear problem (alarms without fix guidance), phased product vision, honest prototype framing |
| **Implementation maturity** | **Reference prototype** — runnable end-to-end guidance loop, not production safety software |
| **Code quality** | Good for scope — small, readable Python backend (~850 LOC), focused React UI |
| **Documentation** | Above average README + architecture + product plan; governance gaps on repo hygiene |
| **Demo readiness** | ⚠️ **Partial** — works via HTTP demo ingest; MQTT path blocked locally by missing `docker/mosquitto.conf` |
| **Governance tier** | **Below T1** — no CI, no tests, no root `plan.md`, no `.env.example`, no `LICENSE` |
| **Portfolio guardrails** | **Out of scope** for the three-repo map; PdM as standalone is allowed as a separate vertical |

**Verdict:** A credible **maintenance-copilot engineering baseline** with BM25 RAG, optional LLM synthesis, MQTT event path, and (in working tree) machinery audio STFT analysis. Value is in the **architecture story and extensibility**, not production hardening. Uncommitted local changes add significant audio features but also delete Mosquitto config — reconcile before demo or publish.

---

## 1. Product identity and scope

### 1.1 What it is

A **generative-AI maintenance copilot** that turns fused edge evidence (thermal, optical summary, acoustic cues) into **actionable, cited** repair guidance with explicit **preventive vs breakdown** framing.

**Target production architecture (documented, not built):**

- Jetson-class edge fusing FLIR-class thermal + RGB + directional mic → spectrogram
- Central **VLM + audio model** + vector RAG over OEM manuals
- EAM integration (SAP PM, Maximo)

**What this repository actually ships:**

| Layer | Built | Notes |
|-------|:-----:|-------|
| Edge fusion (Jetson, real sensors) | ❌ | `scripts/edge_simulator.py` publishes JSON |
| MQTT transport | ✅ | Mosquitto via Docker Compose (config issue — see §6) |
| BM25 RAG over local Markdown | ✅ | `backend/app/rag_engine.py` |
| Optional OpenAI text LLM | ✅ | Template fallback on failure |
| VLM + spectrogram model | ❌ | Roadmap only |
| Machinery audio STFT heuristics | ✅ | **Working tree only** — `backend/app/audio_analysis.py` |
| React technician dashboard | ✅ | WebSocket live feed + demo inject + audio upload |
| EAM / work orders | ❌ | Stub JSON only (`eam_status: not_integrated`) |

### 1.2 Relationship to Factory AI portfolio

Per [`factory-system-AI/README.md`](../README.md):

> **Not in this portfolio:** `Factory-genius/` — separate experiment; not part of the three-repo story.

| Portfolio guardrail | Factory Genius alignment |
|---------------------|--------------------------|
| No standalone PdM in **portfolio** | ✅ Separate repo — not bundled with FactoryOps |
| No real MES/ERP | ✅ EAM explicitly stubbed |
| No embedded/firmware in **portfolio** | ⚠️ Product vision includes Jetson edge; prototype simulates only |
| No deep learning training pipelines | ✅ No training; heuristic STFT + BM25 + optional LLM |
| LLM must not execute raw SQL | N/A — no SQL layer |

Factory Genius occupies a **maintenance / reliability vertical** adjacent to but distinct from OEE (FactoryOps) and visual defect inspection (VisionGuard).

---

## 2. Architecture

### 2.1 Data flow (as implemented)

```text
┌─────────────────────┐     conveyance/{asset_id}/anomaly      ┌──────────────────┐
│ edge_simulator.py   │ ──────────────────────────────────────>│ Mosquitto :1883  │
│ POST /api/demo/ingest│                                        └────────┬─────────┘
│ POST /api/audio/*   │                                                 │
└─────────────────────┘                                                 v
                                                               ┌──────────────────┐
                                                               │ mqtt_worker.py   │
                                                               │ (daemon thread)  │
                                                               └────────┬─────────┘
                                                                        │
                    ┌───────────────────────────────────────────────────┤
                    v                                                   v
           ┌─────────────────┐                              ┌─────────────────────┐
           │ ManualRAG       │                              │ EventStore (200)    │
           │ BM25 on *.md    │                              │ + asyncio.Queue     │
           └────────┬────────┘                              └──────────┬──────────┘
                    v                                                  │
           ┌─────────────────┐                              WebSocket /ws/events
           │ diagnosis.py    │                                         │
           │ template | LLM  │                                         v
           └────────┬────────┘                              ┌─────────────────────┐
                    │                                      │ React dashboard     │
                    └──────────────────────────────────────│ (web/dist or :5173) │
                                                           └─────────────────────┘
```

### 2.2 Repository layout

```text
Factory-genius/
├── backend/app/           # FastAPI application (~851 LOC Python)
│   ├── main.py              # Routes, WebSocket, SPA mount
│   ├── mqtt_worker.py       # MQTT subscribe + diagnosis pipeline
│   ├── rag_engine.py        # BM25 chunking + retrieval
│   ├── diagnosis.py         # Query building, preventive/breakdown heuristics, LLM
│   ├── audio_analysis.py    # STFT band energy (working tree — not in HEAD commit)
│   ├── schemas.py           # Pydantic models
│   ├── config.py            # Pydantic Settings + .env
│   └── store.py             # In-memory event ring buffer
├── data/knowledge/          # 3 maintenance Markdown sources (RAG corpus)
├── scripts/edge_simulator.py
├── web/                     # Vite + React 18 + Tailwind 3
├── docs/
│   ├── product/plan.md      # Product OKRs and phased roadmap
│   └── architecture/overview.md
├── docker-compose.yml       # Mosquitto only
└── requirements.txt
```

### 2.3 API surface

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| `GET` | `/api/health` | Liveness + RAG chunk count | None |
| `GET` | `/api/events` | Recent diagnostic events | None |
| `POST` | `/api/demo/ingest` | HTTP anomaly injection | None (dev) |
| `POST` | `/api/audio/analyze` | STFT analysis only | None |
| `POST` | `/api/audio/diagnose` | Audio → anomaly payload → full diagnosis | None |
| `WS` | `/ws/events` | Live event stream + 50-event backlog | None |
| `*` | `/` | Static SPA from `web/dist/` if built | None |

### 2.4 Anomaly payload contract

`AnomalyPayload` (`schemas.py`) supports forward-compatible multimodal refs:

- Scalars: `thermal_c`, `thermal_baseline_c`, `acoustic_anomaly`, `acoustic_band_hz`
- Text: `rgb_summary`, `trigger_reason`, `edge_hypothesis`
- Artifact refs: `thermal_image_ref`, `optical_image_ref`, `spectrogram_ref` (not fetched in prototype)
- Routing: `asset_class` (conveyor, cnc, stamping_press, …)

Edge simulator scenarios: `drive_shaft`, `merge_rotary`, `cnc_spindle`, `heartbeat`.

---

## 3. Implementation review

### 3.1 Backend strengths

1. **Clean separation** — RAG, diagnosis synthesis, MQTT, and HTTP ingest share one pipeline via `retrieve_chunks` + `synthesize_diagnosis`.
2. **Graceful degradation** — MQTT failure logs and continues; LLM failure falls back to template; broker optional with HTTP ingest.
3. **Honest heuristics** — `_maintenance_mode_hint()` labels preventive vs breakdown from thermal delta rules; audio analysis includes explicit caveat strings.
4. **Security-conscious error handling** — Audio endpoints return generic `"Audio analysis failed."` to clients; exception types logged server-side only.
5. **Artifact ref discipline** — Template diagnosis notes fused packet refs but does not echo URIs into logs by default.
6. **Thread-safe store** — `EventStore` uses lock; MQTT thread enqueues to asyncio via `call_soon_threadsafe`.

### 3.2 Backend gaps and risks

| Issue | Severity | Location | Notes |
|-------|----------|----------|-------|
| No authentication on any endpoint | Medium (demo OK) | `main.py` | Acceptable for local prototype; required before any network exposure |
| Open `POST /api/demo/ingest` | Low (dev) | `main.py` | Should be env-gated or removed in production builds |
| LLM prompt lacks `<data>` delimiters | Medium | `diagnosis.py` `_openai_diagnosis` | [`08-AI-SECURITY.md`](../../../governance/standards/08-AI-SECURITY.md) §1 — retrieved excerpts and metrics injected raw |
| No structured output validation for LLM | Medium | `diagnosis.py` | Free-form Markdown returned; no Pydantic schema enforcement |
| Full payload JSON in LLM user message | Low | `diagnosis.py` | `payload.model_dump_json()` — could include operator notes if extended |
| RAG reload requires restart | Low | `rag_engine.py` | No hot-reload on knowledge file changes |
| In-memory event store only | Low | `store.py` | 200-event cap; lost on restart |
| Duplicate diagnosis logic | Low | `main.py` vs `mqtt_worker.py` | `_ingest_diagnostic_event` vs inline MQTT handler — minor drift risk |
| Missing `docker/mosquitto.conf` in working tree | **High (demo)** | `docker/` | **Deleted locally**; still tracked in git HEAD — `docker compose up` fails |

### 3.3 Audio analysis module (working tree)

`audio_analysis.py` (155 LOC, **untracked**):

- Decodes WAV/FLAC via librosa @ 22.05 kHz mono
- STFT band-energy shares across 5 maintenance-oriented frequency bands
- Heuristic `acoustic_anomaly` from max band share, HF share, crest factor
- Maps to `AnomalyPayload` via `anomaly_payload_from_audio`
- Size cap enforced via `MAX_AUDIO_UPLOAD_BYTES` (default 25 MiB)

**Assessment:** Useful prototype extension for the maintenance story. Not in published commit; adds heavy deps (`librosa`, `numpy`, `soundfile`). Needs unit tests for band logic and upload limits.

### 3.4 Frontend

**Stack:** React 18, Vite 5, Tailwind 3, `react-markdown`

**Features:**

- WebSocket live feed with reconnect ping
- Demo scenario buttons (drive shaft, merge rotary)
- Machinery audio upload → `/api/audio/diagnose`
- Markdown-rendered diagnosis with retrieved chunk citations
- Work order stub display

**XSS note:** `react-markdown` renders LLM/template diagnosis without DOMPurify. Content is server-generated (not raw user HTML), but LLM output could theoretically include markdown/HTML tricks — low risk for local demo, worth sanitizing at T2+.

### 3.5 Knowledge base

| File | Topic | Chunks (approx.) |
|------|-------|------------------|
| `conveyance-drive-shaft-bearing-thermal.md` | Bearing housing thermal, preventive vs breakdown | 2–3 |
| `rotary-idler-shaft-acoustic.md` | Acoustic bands, idler bearing signatures | 2–3 |
| `line-shaft-alignment-pm.md` | Alignment PM program | 2–3 |

**Corpus size:** Small but **domain-aligned** — BM25 works for demo; production would need OEM manuals at scale (vector DB per product plan Phase 2).

---

## 4. Git and release state

### 4.1 Remote and history

| Field | Value |
|-------|-------|
| Remote | `origin` → `https://github.com/vgandhi1/factory-genius.git` |
| Commits | **1** (initial commit only on `main`) |
| Published | Yes — unlike sibling factory repos |

### 4.2 Working tree vs HEAD (2026-06-17)

Uncommitted changes detected:

| Path | Status |
|------|--------|
| `backend/app/audio_analysis.py` | **Added** (untracked) — full audio pipeline |
| `docker/mosquitto.conf` | **Deleted** locally — breaks Compose |
| `README.md`, `main.py`, `schemas.py`, `App.tsx`, … | Modified |
| `requirements.txt` | Modified (+ librosa, numpy, soundfile) |

**Recommendation:** Restore `docker/mosquitto.conf`, commit audio feature as a focused second commit, or document HTTP-only demo path until restored.

---

## 5. Governance and standards compliance

Measured against [`governance/standards/COMPLIANCE.md`](../../../governance/standards/COMPLIANCE.md):

| Requirement | Standard | Status |
|-------------|----------|:------:|
| `README.md` | T0+ | ✅ Strong |
| `.gitignore` | T0+ | ✅ Includes `.env` |
| `plan.md` at repo root | T1+ | ❌ Plan lives at `docs/product/plan.md` only |
| `.env.example` | T1+ (env vars used) | ❌ Template embedded in README only |
| CI `test.yml` | T1+ | ❌ |
| `tests/` directory | T1+ | ❌ |
| `LICENSE` | T2+ public | ❌ README says "Specify your organization's license" |
| `presentation.html` | T2+ public demo | ❌ |
| AI security (prompt delimiters, structured output) | T1+ AI projects | ⚠️ Partial |
| Logging security (no PII/secrets in logs) | All | ✅ No credential logging observed |

**Inferred tier:** **T0+ approaching T1** — excellent README and docs, missing mechanical compliance files.

Cross-reference: [`STANDARDS-COMPLIANCE-REPORT.md`](../../../STANDARDS-COMPLIANCE-REPORT.md) (2026-06-13) flagged Factory-genius as portfolio laggard: *no plan/CI/tests/env.example*.

---

## 6. Demo and operability

### 6.1 Quick start paths

| Path | Steps | Status |
|------|-------|--------|
| **HTTP demo (no MQTT)** | API + built `web/dist` → UI buttons or `curl /api/demo/ingest` | ✅ Works |
| **MQTT + simulator** | `docker compose up` → `edge_simulator.py` | ❌ **Blocked** — `docker/mosquitto.conf` missing locally |
| **Audio diagnose** | `POST /api/audio/diagnose` with WAV | ✅ Working tree only |
| **LLM mode** | Set `OPENAI_API_KEY` in `.env` | ✅ Optional |

### 6.2 Verified run prerequisites

```bash
cd Factory-genius
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
cd web && npm install && npm run build && cd ..
uvicorn backend.app.main:app --reload --port 8000
# → http://127.0.0.1:8000
```

---

## 7. AI and LLM guardrails assessment

Aligned with [`factory-ai-portfolio-guardrails.md`](../../../governance/Guardrails/specialized/factory-portfolio/factory-ai-portfolio-guardrails.md) **shared AI section** where applicable:

| Guardrail | Implementation | Gap |
|-----------|----------------|-----|
| Grounded citations | BM25 excerpts surfaced in UI | ✅ |
| Scope boundary / refusal | No explicit out-of-scope classifier | ❌ |
| Temperature control | LLM `temperature: 0.2` | ✅ |
| No speculative output as fact | System prompt: "Do not invent part numbers" | ⚠️ Partial |
| Prompt injection from stored data | Manual chunks in prompt without `<data>` wrappers | ❌ |
| Structured output enforcement | Template uses Markdown; LLM unstructured | ❌ |
| Cost controls | Single LLM call per event; no max_tokens set | ⚠️ |
| Human confirmation for writes | Read-only guidance; work order stub only | ✅ |

**Template mode** (no API key) is the safer default for demos — fully deterministic, cites retrieval, includes LOTO reminders.

---

## 8. Maturity scorecard

| Dimension | Score (1–10) | Notes |
|-----------|:------------:|-------|
| Product vision / docs | 8.5 | Clear OKRs, phased roadmap, honest prototype labels |
| Architecture clarity | 8.0 | Good separation; target vs built documented |
| Code quality | 7.5 | Small, readable; some duplication |
| Feature completeness (prototype) | 7.0 | Core loop works; audio adds value in WT |
| Test / CI coverage | 1.0 | None |
| Security hardening | 4.0 | Demo-appropriate; AI prompt hygiene gaps |
| Demo reliability | 5.5 | HTTP path OK; MQTT path broken locally |
| Governance compliance | 3.5 | Missing T1 mechanical files |
| Interview / portfolio signal | 8.0 | Strong maintenance-AI narrative distinct from OEE/VisionGuard |
| Production readiness | 2.0 | Explicitly not production safety software |

**Overall grade: B− as reference prototype; D+ on engineering hygiene.**

---

## 9. Comparison to sibling factory repos

| Attribute | Factory Genius | factory-ops | visionguard | factory-digital-twin |
|-----------|----------------|-------------|-------------|----------------------|
| Portfolio member | No | Yes | Yes | Yes |
| Git remote | ✅ Published | ❌ Local only | ❌ Local only | ❌ Local only |
| `plan.md` / SPEC | docs only | SPEC.md | SPEC.md | SPEC.md |
| CI | ❌ | ✅ test.yml | ✅ test.yml | ✅ test.yml |
| Tests | ❌ | ✅ | ✅ (partial) | ✅ |
| Docker Compose | MQTT only | Full stack | Full stack | NATS + sim |
| LLM feature | Maintenance copilot | OEE Copilot | N/A | N/A |
| Primary modality | Multimodal maintenance | Time-series ops | Vision | Synthetic events |

Factory Genius is **more publish-ready (has remote)** but **less engineering-complete (no CI/tests)** than the three-repo portfolio.

---

## 10. Priority roadmap

### Immediate (before next demo or commit)

- [ ] Restore `docker/mosquitto.conf` and verify `docker compose up` + MQTT simulator path
- [ ] Commit working-tree audio feature with updated README, or revert WT changes for clean HEAD
- [ ] Add root `plan.md` (symlink or move from `docs/product/plan.md` per [`05-PLANNING.md`](../../../governance/standards/05-PLANNING.md))
- [ ] Add `.env.example` extracted from README template

### Short term (T1 compliance)

- [ ] `.github/workflows/test.yml` — ruff + pytest on `audio_analysis`, `rag_engine`, `_maintenance_mode_hint`
- [ ] Unit tests: BM25 retrieval smoke, audio band shares, payload validation, thermal heuristic labels
- [ ] Wrap LLM context in `<data>` blocks per AI security standard
- [ ] Set `max_tokens` on OpenAI calls

### Medium term (T2 / public polish)

- [ ] Add `LICENSE` (MIT or Apache-2.0)
- [ ] `presentation.html` + GitHub Pages workflow
- [ ] Golden eval set for retrieval (nDCG / hit-rate on maintenance queries)
- [ ] Gate `/api/demo/ingest` behind `ENVIRONMENT=development`

### Long term (product vision — out of prototype scope)

- Embedding + vector DB (pgvector / Qdrant)
- VLM + spectrogram model serving on artifact refs
- EAM connector stubs → SAP PM / Maximo
- Jetson edge firmware and acoustic privacy band-pass

---

## 11. Interview talking points

### Lead with

1. **Maintenance copilot, not alarm dashboard** — fused evidence → cited procedures with preventive vs breakdown framing.
2. **Event-driven architecture** — MQTT anomaly topics + WebSocket dashboard; HTTP fallback for dev.
3. **Pragmatic AI stack** — BM25 first (no vector DB required for demo); optional LLM with template fallback.
4. **Honest prototype boundaries** — not production safety software; EAM stubbed; edge simulated.

### If probed on gaps

| Question | Honest answer |
|----------|---------------|
| "Why BM25 not embeddings?" | Prototype speed; product plan Phase 2 adds vector store. |
| "Where's the VLM?" | Target architecture documented; prototype uses text summaries + optional LLM. |
| "Is the audio classifier production-grade?" | No — STFT band-energy heuristic with explicit caveat; validates the ingest path. |
| "How does this relate to FactoryOps?" | Separate vertical — FactoryOps is OEE/downtime ops intelligence; Genius is asset maintenance guidance. |
| "Can I trust the LLM diagnosis?" | Template mode is fully retrieval-grounded; LLM mode requires API key and should be validated on site. |

---

## 12. Conclusion

Factory Genius is a **well-documented, conceptually strong maintenance-AI prototype** with a runnable guidance loop (RAG + optional LLM + live UI). It correctly sits **outside** the Factory AI three-repo portfolio while complementing that story for **reliability / maintenance** interviews.

The largest gaps are **engineering hygiene** (CI, tests, compliance files) and **working-tree inconsistency** (audio feature added, Mosquitto config removed). Fixing those and committing a second release would move the project from "strong README + one commit" to **auditable T1 dev baseline**.

---

*Report generated from static analysis of repository structure, source files, git metadata, and governance standards. Working-tree state reflects 2026-06-17 local checkout.*
