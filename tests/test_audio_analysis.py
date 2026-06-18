import numpy as np
import pytest

from backend.app.audio_analysis import analyze_audio_bytes


def _sine_wav_bytes(duration_s: float = 0.5, sr: int = 22050, freq: float = 1000.0) -> bytes:
    import io
    import wave

    n = int(duration_s * sr)
    t = np.linspace(0, duration_s, n, endpoint=False)
    y = (0.3 * np.sin(2 * np.pi * freq * t) * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(y.tobytes())
    return buf.getvalue()


def test_rejects_empty_upload():
    with pytest.raises(ValueError, match="Empty"):
        analyze_audio_bytes(b"", max_bytes=1024)


def test_rejects_oversized_upload():
    data = _sine_wav_bytes()
    with pytest.raises(ValueError, match="size limit"):
        analyze_audio_bytes(data, max_bytes=len(data) - 1)


def test_analyzes_short_sine_wave():
    result = analyze_audio_bytes(_sine_wav_bytes(), max_bytes=1024 * 1024)
    assert result.duration_sec > 0
    assert result.sample_rate == 22050
    assert len(result.bands) >= 1
    assert result.dominant_band_hz
