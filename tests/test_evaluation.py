import json, os
from src.evaluation import load_eval_dataset, compute_checksum

def test_load_dataset():
    path = r'C:\Users\lenovo\Downloads\Ai-Function-Calling-Router\data\eval.jsonl'
    cases = load_eval_dataset(path)
    assert len(cases) >= 60
    for c in cases:
        assert "id" in c
        assert "request" in c
        assert "expected_tool" in c
        assert "injected_fault" in c

def test_checksum_stable():
    path = r'C:\Users\lenovo\Downloads\Ai-Function-Calling-Router\data\eval.jsonl'
    cases = load_eval_dataset(path)
    cs1 = compute_checksum(cases)
    cs2 = compute_checksum(cases)
    assert cs1 == cs2
    assert len(cs1) == 64
