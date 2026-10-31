import json, os
from pathlib import Path

def test_metrics_contract():
    path = Path('output/metrics.json')
    assert path.exists()
    data = json.loads(path.read_text())
    assert "baseline" in data
    assert "recovery_active" in data
    for key in ["completion_rate","silent_wrong_rate","mean_recovery_attempts"]:
        assert key in data["baseline"]
        assert key in data["recovery_active"]
    # rates between 0 and 1
    for section in ["baseline","recovery_active"]:
        assert 0 <= data[section]["completion_rate"] <= 1
        assert 0 <= data[section]["silent_wrong_rate"] <= 1
    # baseline mean recovery attempts zero
    assert data["baseline"]["mean_recovery_attempts"] == 0

def test_recovery_improves_completion():
    path = Path('output/metrics.json')
    data = json.loads(path.read_text())
    assert data["recovery_active"]["completion_rate"] >= data["baseline"]["completion_rate"]
