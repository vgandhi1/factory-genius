from __future__ import annotations

import json
import logging
import re

import httpx

from .config import settings
from .rag_engine import ManualRAG
from .schemas import AnomalyPayload, RetrievedChunk

logger = logging.getLogger(__name__)


def build_retrieval_query(payload: AnomalyPayload) -> str:
    parts = [
        payload.machine_id,
        payload.trigger_reason or "",
        payload.rgb_summary or "",
        payload.acoustic_band_hz or "",
        "conveyance conveyor shaft rotary idler pulley roller bearing alignment lubrication preventive breakdown acoustic thermal",
    ]
    if payload.thermal_c is not None:
        parts.append(f"thermal {payload.thermal_c}C")
    return " ".join(p for p in parts if p)


def _maintenance_mode_hint(payload: AnomalyPayload) -> tuple[str, str]:
    """Heuristic label for whether work fits a preventive window vs breakdown response."""
    thermal = payload.thermal_c
    base = payload.thermal_baseline_c
    delta = (thermal - base) if thermal is not None and base is not None else None

    if thermal is not None and thermal >= 85:
        return (
            "Breakdown / immediate response",
            "Thermal at or above a critical shaft/bearing threshold—stop and inspect per site policy before restart.",
        )
    if delta is not None and delta >= 25:
        return (
            "Breakdown / immediate response",
            "Large step above baseline suggests an acute fault on the rotary train; treat as failure-in-progress.",
        )
    if payload.acoustic_anomaly and (delta is None or delta < 15) and (thermal is None or thermal < 75):
        return (
            "Preventive / condition-based window",
            "Acoustic change with limited thermal rise—plan inspection, alignment, or bearing service before peak production.",
        )
    if delta is not None and 8 <= delta < 25:
        return (
            "Preventive / condition-based window",
            "Thermal elevation—schedule greasing, alignment verification, and bearing assessment in a planned window.",
        )
    return (
        "Assess on site",
        "Trend and context are ambiguous—confirm speed/load, compare adjacent stations, and inspect physically.",
    )


def retrieve_chunks(rag: ManualRAG, payload: AnomalyPayload, top_k: int = 5) -> list[RetrievedChunk]:
    q = build_retrieval_query(payload)
    ranked = rag.retrieve(q, top_k=top_k)
    out: list[RetrievedChunk] = []
    for chunk, score in ranked:
        excerpt = _excerpt(chunk.body, limit=420)
        out.append(
            RetrievedChunk(
                doc_id=chunk.doc_id,
                title=chunk.title,
                excerpt=excerpt,
                score=score,
            )
        )
    return out


def _excerpt(text: str, limit: int) -> str:
    t = re.sub(r"\s+", " ", text).strip()
    if len(t) <= limit:
        return t
    return t[: limit - 1] + "…"


def synthesize_diagnosis(payload: AnomalyPayload, retrieved: list[RetrievedChunk]) -> tuple[str, str]:
    if settings.openai_api_key:
        return _openai_diagnosis(payload, retrieved)
    return _template_diagnosis(payload, retrieved)


def _template_diagnosis(payload: AnomalyPayload, retrieved: list[RetrievedChunk]) -> tuple[str, str]:
    title = f"Conveyance / rotary — {payload.machine_id}"
    mode_label, mode_detail = _maintenance_mode_hint(payload)
    lines = [
        f"**Trigger:** {payload.trigger_reason or 'threshold breach'}",
        f"**Maintenance mode (heuristic):** **{mode_label}** — {mode_detail}",
    ]
    if payload.thermal_c is not None:
        base = payload.thermal_baseline_c
        lines.append(
            f"**Thermal:** {payload.thermal_c:.1f}°C"
            + (f" (baseline ~{base:.1f}°C)" if base is not None else "")
        )
    if payload.acoustic_anomaly:
        lines.append(
            f"**Acoustic:** anomaly flagged"
            + (f" in band {payload.acoustic_band_hz}" if payload.acoustic_band_hz else "")
        )
    if payload.rgb_summary:
        lines.append(f"**Visual summary:** {payload.rgb_summary}")
    lines.append("")
    lines.append("**Retrieved maintenance context (BM25):**")
    if not retrieved:
        lines.append("- No local manual chunks matched. Add knowledge under `data/knowledge/`.")
    else:
        for r in retrieved[:3]:
            lines.append(f"- *{r.title}* — {r.excerpt[:220]}…" if len(r.excerpt) > 220 else f"- *{r.title}* — {r.excerpt}")
    lines.append("")
    lines.append(
        "**Next steps:** Confirm line speed and load vs baseline, apply **LOTO** before touching rotating equipment, "
        "and use the retrieved excerpts to choose **preventive** (scheduled/condition-based) vs **breakdown** "
        "(immediate stop and repair) actions per your OEM and site standard."
    )
    return title, "\n".join(lines)


def _openai_diagnosis(payload: AnomalyPayload, retrieved: list[RetrievedChunk]) -> tuple[str, str]:
    context = "\n\n".join(f"### {r.title}\n{r.excerpt}" for r in retrieved[:6])
    user = (
        "You are an expert reliability engineer for conveyance systems (shafts, pulleys, idlers, rotary modules). "
        "Using ONLY the retrieved manual excerpts and the metrics: (1) state likely failure modes on the rotary train, "
        "(2) explicitly recommend **preventive / condition-based** vs **breakdown / immediate** response with justification, "
        "(3) give numbered steps. If data is insufficient, say what to measure next.\n\n"
        f"**Metrics:** {payload.model_dump_json()}\n\n**Retrieved excerpts:**\n{context}"
    )
    try:
        with httpx.Client(timeout=60.0) as client:
            r = client.post(
                f"{settings.openai_base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.openai_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Respond in Markdown. Do not invent part numbers; cite uncertainty. "
                                "Always separate preventive vs breakdown guidance when both could apply."
                            ),
                        },
                        {"role": "user", "content": user},
                    ],
                    "temperature": 0.2,
                },
            )
            r.raise_for_status()
            data = r.json()
        content = data["choices"][0]["message"]["content"]
        title = f"LLM diagnosis — {payload.machine_id}"
        return title, content
    except (httpx.HTTPError, KeyError, json.JSONDecodeError) as e:
        logger.warning("OpenAI diagnosis failed; falling back to template: %s", type(e).__name__)
        return _template_diagnosis(payload, retrieved)
