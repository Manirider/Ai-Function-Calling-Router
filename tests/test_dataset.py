import json
from src.evaluation import load_eval_dataset
from src.tools import TOOL_REGISTRY

def test_dataset_size():
    cases = load_eval_dataset(r'C:\Users\lenovo\Downloads\Ai-Function-Calling-Router\data\eval.jsonl')
    assert len(cases) >= 60

def test_dataset_unique_ids():
    cases = load_eval_dataset(r'C:\Users\lenovo\Downloads\Ai-Function-Calling-Router\data\eval.jsonl')
    ids = [c['id'] for c in cases]
    assert len(ids) == len(set(ids))

def test_dataset_tools_covered():
    cases = load_eval_dataset(r'C:\Users\lenovo\Downloads\Ai-Function-Calling-Router\data\eval.jsonl')
    tools = set(c['expected_tool'] for c in cases)
    for t in TOOL_REGISTRY:
        assert t in tools

def test_dataset_fault_directives():
    cases = load_eval_dataset(r'C:\Users\lenovo\Downloads\Ai-Function-Calling-Router\data\eval.jsonl')
    valid_types = {"NONE","TIMEOUT","MALFORMED_RESPONSE","MALFORMED","TIMEOUT_ONCE","TIMEOUT_ALWAYS","MALFORMED_ONCE","MALFORMED_ALWAYS"}
    for c in cases:
        ftype = c.get('injected_fault',{}).get('type')
        assert ftype in valid_types
