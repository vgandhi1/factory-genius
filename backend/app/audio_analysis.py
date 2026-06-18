"""Heuristic machinery audio analysis: STFT band energy for maintenance-oriented RAG queries.

This is a reference signal-processing path (not a trained classifier). Prefer WAV/FLAC
for predictable decoding; other formats depend on system codecs.
"""

from __future__ import annotations

import io
import logging
from typing import Sequence

import librosa
import numpy as np

from .schemas import AnomalyPayload, AudioAnalysisResult, AudioBandShare

logger = logging.getLogger(__name__)

_ANALYSIS_METHOD = "stft_band_energy_v1"

_CAVEAT = (
    "Heuristic spectral summary only—not a certified fault classifier. "
    "Validate with qualified personnel, vibration, and thermal data."
)

# (hz_low, hz_high, short label for hypothesis text)
_BAND_DEFS: tuple[tuple[float, float, str], ...] = (
    (0.0, 200.0, "very low / structural or imbalance-type content"),
    (200.0, 800.0, "low-frequency rotational or looseness-type content"),
    (800.0, 2500.0, "mid band often tied to belts, mesh, or roller modulation"),
    (2500.0, 6000.0, "mid-high band often tied to bearings, idlers, or chatter"),
    (6000.0, 12000.0, "high band often tied to hiss, leak-like air paths, or blade-like tones"),
)


def _nyquist(sr: int) -> float:
    return 0.49 * float(sr)


def _band_edges_for_sr(sr: int) -> list[tuple[float, float, str]]:
    nyq = _nyquist(sr)
    out: list[tuple[float, float, str]] = []
    for lo, hi, label in _BAND_DEFS:
        if lo >= nyq:
            break
        out.append((lo, min(hi, nyq), label))
    if not out:
        out.append((0.0, nyq, "broadband"))
    return out


def _band_shares(y: np.ndarray, sr: int) -> tuple[list[AudioBandShare], np.ndarray]:
    n_fft = 4096
    hop = 1024
    s = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop, window="hann", center=True)) ** 2
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    edges = _band_edges_for_sr(sr)
    powers: list[float] = []
    shares_models: list[AudioBandShare] = []
    for lo, hi, _label in edges:
        mask = (freqs >= lo) & (freqs < hi)
        p = float(s[mask, :].sum()) if np.any(mask) else 0.0
        powers.append(p)
    total = float(np.sum(powers)) + 1e-12
    raw = np.array(powers, dtype=np.float64) / total
    for (lo, hi, _label), sh in zip(edges, raw.tolist(), strict=True):
        shares_models.append(AudioBandShare(hz_low=lo, hz_high=hi, energy_share=float(sh)))
    return shares_models, raw


def _crest_factor(y: np.ndarray) -> float:
    rms = float(np.sqrt(np.mean(np.square(y))) + 1e-12)
    peak = float(np.max(np.abs(y)) + 1e-12)
    return peak / rms


def _dominant_hypothesis(edges: Sequence[tuple[float, float, str]], shares: np.ndarray) -> tuple[int, str, str]:
    i = int(np.argmax(shares))
    lo, hi, label = edges[i]
    band_hz = f"{lo:.0f}-{hi:.0f}"
    hyp = (
        f"Strongest STFT band energy in {band_hz} Hz ({label}); "
        "use as a retrieval hint—confirm with root-cause checks on site."
    )
    return i, band_hz, hyp


def analyze_audio_bytes(data: bytes, max_bytes: int) -> AudioAnalysisResult:
    if not data:
        raise ValueError("Empty upload.")
    if len(data) > max_bytes:
        raise ValueError("Audio file exceeds the configured size limit.")

    try:
        y, sr = librosa.load(io.BytesIO(data), sr=22_050, mono=True)
    except Exception as e:
        logger.info("librosa failed to decode audio: %s", type(e).__name__)
        raise ValueError("Could not decode audio. Try a mono or stereo WAV/FLAC clip.") from e

    if y.size == 0:
        raise ValueError("Decoded audio is empty.")
    min_samples = int(0.25 * sr)
    if y.size < min_samples:
        raise ValueError("Clip too short; record at least about 0.25 seconds.")

    y = y.astype(np.float64, copy=False)
    edges = _band_edges_for_sr(int(sr))
    bands, share_arr = _band_shares(y, int(sr))
    _idx, band_hz, hypothesis = _dominant_hypothesis(edges, share_arr)
    crest = _crest_factor(y)

    max_share = float(np.max(share_arr)) if share_arr.size else 0.0
    # HF emphasis: bands whose low edge >= 2500 Hz in our default table
    hf_mask = np.array([e[0] >= 2500.0 for e in edges], dtype=np.float64)
    hf_share = float(np.sum(share_arr * hf_mask)) if share_arr.size else 0.0

    acoustic_anomaly = (max_share >= 0.42) or (hf_share >= 0.35) or (crest >= 14.0)

    duration_sec = float(y.size / float(sr))
    return AudioAnalysisResult(
        duration_sec=duration_sec,
        sample_rate=int(sr),
        bands=bands,
        dominant_band_hz=band_hz,
        acoustic_band_hz=band_hz,
        acoustic_anomaly=acoustic_anomaly,
        edge_hypothesis=hypothesis,
        crest_factor=float(crest),
        method=_ANALYSIS_METHOD,
        caveat=_CAVEAT,
    )


def anomaly_payload_from_audio(
    machine_id: str,
    analysis: AudioAnalysisResult,
    *,
    asset_class: str | None = None,
    thermal_c: float | None = None,
    thermal_baseline_c: float | None = None,
    rgb_summary: str | None = None,
) -> AnomalyPayload:
    return AnomalyPayload(
        machine_id=machine_id,
        asset_class=asset_class,
        thermal_c=thermal_c,
        thermal_baseline_c=thermal_baseline_c,
        acoustic_anomaly=analysis.acoustic_anomaly,
        acoustic_band_hz=analysis.acoustic_band_hz,
        rgb_summary=rgb_summary,
        trigger_reason="machinery_audio_spectral_analysis",
        edge_hypothesis=analysis.edge_hypothesis,
        notes=f"{analysis.method}; crest_factor={analysis.crest_factor:.2f}",
    )
