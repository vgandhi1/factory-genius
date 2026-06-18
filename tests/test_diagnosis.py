from backend.app.diagnosis import _maintenance_mode_hint, build_retrieval_query
from backend.app.schemas import AnomalyPayload


def test_breakdown_on_critical_thermal():
    payload = AnomalyPayload(
        machine_id="conveyance-main-drive-1",
        thermal_c=86.0,
        thermal_baseline_c=48.0,
    )
    label, _ = _maintenance_mode_hint(payload)
    assert "Breakdown" in label


def test_preventive_on_acoustic_only():
    payload = AnomalyPayload(
        machine_id="merge-table-rotary-2",
        thermal_c=62.0,
        thermal_baseline_c=55.0,
        acoustic_anomaly=True,
        acoustic_band_hz="500-1200",
    )
    label, _ = _maintenance_mode_hint(payload)
    assert "Preventive" in label


def test_retrieval_query_includes_asset_class():
    payload = AnomalyPayload(
        machine_id="cnc-hmc-7",
        asset_class="cnc",
        trigger_reason="spindle_chatter",
    )
    q = build_retrieval_query(payload)
    assert "cnc" in q
    assert "spindle_chatter" in q
