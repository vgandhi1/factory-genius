# Factory Genius — Comprehensive Review Report

**Review date:** 2026-06-17 (initial) · **Last updated:** 2026-06-17 (post T1 cleanup)  
**Repository:** `factory-genius/` (top-level repo, sibling of `factory-system-AI/`) · **Remote (canonical):** [`github.com/vgandhi1/factory-genius`](https://github.com/vgandhi1/factory-genius)  
**Branch:** `main` · **HEAD:** `0ce7e65` — *chore(license): add MIT LICENSE for public release readiness*  
**Reviewed against:** [`governance/standards/COMPLIANCE.md`](https://github.com/vgandhi1/standards/blob/main/COMPLIANCE.md), [`08-AI-SECURITY.md`](https://github.com/vgandhi1/standards/blob/main/08-AI-SECURITY.md), `factory-ai-portfolio-guardrails.md`

---

## Naming and GitHub sync

| Label | Value |
|-------|-------|
| **Product name** | Factory Genius |
| **GitHub repo** | [`vgandhi1/factory-genius`](https://github.com/vgandhi1/factory-genius) |
| **Local folder** | `factory-genius/` (top-level sibling of `factory-system-AI/`; matches repo name) |
| **Portfolio membership** | **None** — separate reliability vertical |

There is **no second project** with this name. The perceived conflict is usually (1) folder was previously `Factory-genius` (capital F) vs GitHub `factory-genius`, or (2) GitHub shows the **initial commit** while local has **3+ unpushed commits**. **Fix:** `git push origin main`.

---

## Executive summary

**Factory Genius** is a **standalone reference prototype** for a generative-AI **maintenance copilot** (conveyors, stamping presses, CNC). It sits **outside** the three-repo Factory AI portfolio documented in [`factory-system-AI/portfolio/`](https://github.com/vgandhi1/factory-system-AI/tree/main/portfolio/).

| Dimension | Assessment (updated) |
|-----------|----------------------|
| **Concept clarity** | Strong — alarms → cited fix guidance; preventive vs breakdown framing |
| **Implementation maturity** | Reference prototype — runnable E2E, not production safety software |
| **Code quality** | Good — ~1,000 LOC Python backend, focused React UI |
| **Documentation** | Strong README + architecture + root `plan.md` + this report |
| **Demo readiness** | ✅ **HTTP, MQTT, and audio paths operational** (`docker/mosquitto.conf` restored) |
| **Governance tier** | **T1 Dev** — CI, tests, `.env.example`, root `plan.md`; **MIT LICENSE** (T2 partial) |
| **Portfolio guardrails** | Out of scope for three-repo map; allowed as separate reliability vertical |

**Verdict:** Credible **maintenance-copilot baseline** with BM25 RAG, optional LLM synthesis, MQTT ingest, machinery audio STFT analysis, and technician dashboard. Engineering hygiene moved from **D+ → B+ / A−** after the June 2026 cleanup commits. Remaining gap for full T2: `presentation.html` + retrieval golden eval.

---

## 1. Product identity and scope

### 1.1 What it ships today

| Layer | Status | Notes |
|-------|:------:|-------|
| Edge fusion (Jetson / real sensors) | ❌ | `scripts/edge_simulator.py` |
| MQTT transport | ✅ | Mosquitto via `docker compose up` |
| BM25 RAG over Markdown | ✅ | `backend/app/rag_engine.py` |
| Optional OpenAI text LLM | ✅ | Template fallback; `<data>` delimiters |
| Machinery audio STFT | ✅ | `backend/app/audio_analysis.py` — **committed** |
| React technician dashboard | ✅ | WebSocket + demo inject + audio upload |
| VLM + spectrogram model | ❌ | Roadmap (Phase 2) |
| EAM integration | ❌ | Work order stub only |

### 1.2 Portfolio relationship

Per [`factory-system-AI/README.md`](https://github.com/vgandhi1/factory-system-AI/blob/main/README.md): **not** part of Digital Twin / FactoryOps / VisionGuard. Complements that story as a **reliability / maintenance** vertical.

---

## 2. Architecture

### 2.1 Data flow

```text
edge_simulator.py ──MQTT──> Mosquitto ──> mqtt_worker.py
POST /api/demo/ingest  ──────────────────> FastAPI main.py
POST /api/audio/*      ──────────────────> audio_analysis.py ──> AnomalyPayload
                                              │
                                              v
                                    ManualRAG (BM25) + diagnosis.py
                                              │
                              EventStore + WebSocket /ws/events
                                              │
                                    React dashboard (web/dist)
```

### 2.2 Repository layout (current)

```text
factory-genius/
├── backend/app/              # FastAPI (~1k LOC)
│   ├── audio_analysis.py     # STFT band-energy heuristics
│   ├── diagnosis.py          # RAG + LLM with <data> blocks
│   ├── main.py               # REST, WebSocket, audio routes
│   ├── mqtt_worker.py
│   ├── rag_engine.py
│   └── ...
├── data/knowledge/           # 3 maintenance Markdown sources
├── docker/mosquitto.conf     # Restored — MQTT demo path
├── tests/                    # 7 pytest cases
├── .github/workflows/test.yml
├── plan.md                   # Canonical status (T1)
├── .env.example
├── LICENSE                   # MIT
└── web/                      # Vite + React 18 + Tailwind 3
```

---

## 3. Implementation review

### 3.1 Strengths

- Clean separation: RAG, diagnosis, MQTT, HTTP share one pipeline
- Graceful degradation: no broker → HTTP ingest; LLM fail → template
- Preventive vs breakdown heuristics in `_maintenance_mode_hint()`
- AI security: LLM context wrapped in `<data type="metrics">` and `<data type="manual_excerpts">`; `max_tokens: 1000`
- Generic client errors on audio failures; no credential logging
- Thread-safe event store; MQTT → asyncio queue bridge

### 3.2 Remaining gaps

| Issue | Severity | Notes |
|-------|----------|-------|
| No API authentication | Medium (demo OK) | Required before network exposure |
| Open `POST /api/demo/ingest` | Low | Gate on `ENVIRONMENT=development` at T2 |
| No structured LLM output schema | Medium | Free-form Markdown today |
| In-memory event store (200 cap) | Low | Restart loses history |
| No retrieval golden eval | Medium | Manual dashboard review only |
| `presentation.html` missing | Low (T2) | Only remaining public-demo artifact |

### 3.3 Tests and CI

| Artifact | Status |
|----------|--------|
| `tests/test_diagnosis.py` | ✅ Maintenance mode + query building |
| `tests/test_rag_engine.py` | ✅ BM25 smoke on knowledge corpus |
| `tests/test_audio_analysis.py` | ✅ Upload limits + sine-wave STFT |
| `.github/workflows/test.yml` | ✅ ruff critical + pytest on push/PR |
| Last local run | **7 passed** |

---

## 4. Git history

| Commit | Message |
|--------|---------|
| `0ce7e65` | chore(license): add MIT LICENSE |
| `df91970` | chore(governance): T1 compliance — CI, plan, env, tests, mosquitto, LLM `<data>` |
| `2681574` | feat(ai): STFT audio band analysis |
| `81c1185` | Initial commit |

**Remote:** published at `vgandhi1/factory-genius` · **3 commits ahead** of origin at last local check (push when ready).

---

## 5. Governance compliance

| Requirement | Status |
|-------------|:------:|
| `README.md` | ✅ |
| `.gitignore` + `.env` ignored | ✅ |
| Root `plan.md` | ✅ |
| `.env.example` | ✅ |
| CI `test.yml` | ✅ |
| `tests/` | ✅ (7 cases) |
| `LICENSE` (MIT) | ✅ |
| LLM `<data>` delimiters | ✅ |
| `presentation.html` | ❌ (T2) |
| Logging security | ✅ |

**Inferred tier:** **T1 Dev** → **T2 partial** (LICENSE present; presentation pending).

---

## 6. Demo paths

| Path | Status |
|------|:------:|
| HTTP demo ingest | ✅ |
| MQTT + `edge_simulator.py` | ✅ (`docker compose up` verified) |
| Audio diagnose (`/api/audio/diagnose`) | ✅ |
| Optional LLM (`OPENAI_API_KEY`) | ✅ |

```bash
docker compose up -d
uvicorn backend.app.main:app --reload --port 8000
python scripts/edge_simulator.py --scenario drive_shaft
# → http://127.0.0.1:8000
```

---

## 7. AI guardrails

| Guardrail | Status |
|-----------|:------:|
| Grounded citations in UI | ✅ |
| Temperature 0.2 | ✅ |
| `max_tokens` cap | ✅ |
| `<data>` prompt delimiters | ✅ |
| Scope refusal classifier | ❌ |
| Structured LLM output validation | ❌ |
| Human confirmation before writes | ✅ (read-only guidance) |

---

## 8. Maturity scorecard (updated)

| Dimension | Before cleanup | After cleanup |
|-----------|:--------------:|:-------------:|
| Test / CI coverage | 1.0 | **7.5** |
| Governance compliance | 3.5 | **8.0** |
| Demo reliability | 5.5 | **8.5** |
| Security hardening | 4.0 | **6.5** |
| Feature completeness | 7.0 | **8.0** |

**Overall grade: B+ / A−** on engineering hygiene; **B+** as reference prototype overall.

---

## 9. Comparison to sibling repos

| Attribute | Factory Genius | factory-ops | visionguard | factory-digital-twin |
|-----------|:--------------:|:-----------:|:-----------:|:--------------------:|
| Portfolio member | No | Yes | Yes | Yes |
| Git remote | ✅ | ❌ local | ❌ local | ❌ local |
| CI + tests | ✅ | ✅ | ✅ | ✅ |
| LICENSE | ✅ MIT | ❌ | ❌ | ❌ |
| Primary focus | Maintenance RAG | OEE Copilot | Vision MLOps | Synthetic events |

Factory Genius is now **the most governance-complete** repo in the container (only one with LICENSE + published remote).

---

## 10. Priority roadmap

### Done ✅

- [x] Restore `docker/mosquitto.conf`
- [x] Commit audio STFT pipeline
- [x] Root `plan.md`, `.env.example`, CI, tests
- [x] LLM `<data>` delimiters + `max_tokens`
- [x] MIT LICENSE

### Next (T2)

- [ ] `presentation.html` + GitHub Pages workflow
- [ ] Retrieval golden eval (nDCG / hit-rate)
- [ ] Gate demo ingest behind `ENVIRONMENT=development`

### Deferred (product vision)

- [ ] Vector DB (pgvector / Qdrant)
- [ ] VLM + spectrogram model on artifact refs
- [ ] EAM connectors (SAP PM / Maximo)

---

## 11. Interview talking points

1. **Maintenance copilot** — fused evidence → cited procedures with preventive vs breakdown framing  
2. **Event-driven** — MQTT + WebSocket; HTTP fallback for dev  
3. **Pragmatic AI** — BM25 first; optional LLM with template fallback and prompt-injection guards  
4. **Engineering hygiene** — T1 compliance: CI, tests, MIT license, published repo  

---

## 12. Conclusion

Factory Genius evolved from a **strong concept with weak repo hygiene** to an **auditable T1 baseline** in one cleanup sprint. The maintenance-AI story is distinct from OEE (FactoryOps) and defect inspection (VisionGuard), and the codebase now backs that narrative with tests, CI, and governance artifacts.

Next increment of value: **T2 public polish** (`presentation.html`) and a **retrieval eval harness** so reviewers who won't run the demo can still trust the RAG quality claims.

---

*Updated after commits `2681574`, `df91970`, `0ce7e65`. Prior sections on working-tree drift and missing mosquitto config are **resolved**.*
