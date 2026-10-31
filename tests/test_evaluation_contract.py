import json, os
from pathlib import Path

def test_artifacts_exist():
    base = Path('output')
    assert (base/'metrics.json').exists()
    assert (base/'evaluation_report.json').exists()
    assert (base/'per_case_results.jsonl').exists()
    assert (base/'recovery_breakdown.json').exists()
    assert (base/'dataset_coverage.json').exists()

def test_dataset_coverage():
    data = json.loads(Path('output/dataset_coverage.json').read_text())
    assert data['dataset_size'] >= 60
    assert 'checksum_sha256' in data
    assert len(data['checksum_sha256']) == 64
