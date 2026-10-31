# Requirement Traceability Matrix

| Requirement | Description | Implementation File | Test File | Status |
|-------------|-------------|---------------------|-----------|--------|
| REQ-1 | Four Pydantic tool schemas with input/output models | src/schemas.py | tests/test_schemas.py | Pending |
| REQ-2 | Deterministic fault-injection middleware | src/fault_injector.py | tests/test_fault_injector.py | Pending |
| REQ-3 | Happy-path routing with validation | src/router.py, src/llm_provider.py | tests/test_router.py | Pending |
| REQ-4 | Missing-field recovery | src/recovery.py, src/router.py | tests/test_recovery.py | Pending |
| REQ-5 | Wrong-type recovery | src/recovery.py, src/router.py | tests/test_recovery.py | Pending |
| REQ-6 | Timeout recovery without LLM call | src/recovery.py, src/router.py | tests/test_recovery.py | Pending |
| REQ-7 | Malformed-output schema repair | src/recovery.py, src/router.py | tests/test_recovery.py | Pending |
| REQ-8 | Explicit failure after exhausted recovery | src/router.py | tests/test_contracts.py | Pending |
| REQ-9 | Baseline vs recovery evaluation metrics | evaluate_router.py, src/evaluation.py | tests/test_evaluation.py | Pending |
| REQ-10 | Dockerized one-command evaluation | Dockerfile, docker-compose.yml | - | Pending |

Audit findings:
- Missing README.md
- Missing data/eval.jsonl (needs 60+ cases)
- tests/ directory empty
- Imports use bare module names, will fail when run as package
- Router schema repair returns dummy payload without validation
- Fault injector counters leak across requests
- Recovery functions use fixture correct_args instead of provider call
- Metrics merge logic may produce incomplete metrics.json
- Dockerfile uses user nobody which may lack write permission
