import json
from typing import List, Dict

def load_eval_dataset(path: str) -> List[Dict]:
    with open(path, 'r', encoding='utf-8') as f:
        cases = [json.loads(line) for line in f if line.strip()]
    return cases

def compute_checksum(cases: List[Dict]) -> str:
    import hashlib
    s = json.dumps(cases, sort_keys=True).encode()
    return hashlib.sha256(s).hexdigest()
