# Requirement Traceability

| ID | Requirement | Implementation | Test | Status |
|----|-------------|----------------|------|--------|
| REQ-1 | Four Pydantic tool schemas input/output | src/schemas.py | tests/test_schemas.py | PASS |
| REQ-2 | Deterministic fault injection middleware | src/fault_injector.py | tests/test_fault_injector.py | PASS |
| REQ-3 | Happy-path routing with validation | src/router.py, src/llm_provider.py | tests/test_router.py::test_happy_path | PASS |
| REQ-4 | Missing-field recovery | src/recovery.py recover_missing_field, src/router.py | tests/test_recovery.py::test_missing_field_recoverable, tests/test_router.py::test_missing_field_recovery | PASS |
| REQ-5 | Wrong-type recovery | src/recovery.py recover_type_error | tests/test_recovery.py::test_type_error_recoverable | PASS |
| REQ-6 | Timeout recovery without LLM call | src/router.py, src/recovery.py | tests/test_router.py::test_timeout_recovery_no_provider_call | PASS |
| REQ-7 | Malformed-output schema repair | src/recovery.py recover_schema | tests/test_recovery.py::test_schema_repair_success | PASS |
| REQ-8 | Explicit failure after exhausted recovery | src/router.py | tests/test_contracts.py::test_explicit_failure_missing_field_unrecoverable | PASS |
| REQ-9 | Baseline vs recovery evaluation metrics | evaluate_router.py, src/evaluation.py | tests/test_evaluation.py | PASS |
| REQ-10 | Dockerized one-command evaluation | Dockerfile, docker-compose.yml | Manual | PASS |

## Mapping details
- Tool contracts: FlightSearch, CalendarBooking, WeatherLookup, UnitConversion defined in schemas with strict validation.
- Fault injection supports TIMEOUT/TIMEOUT_ONCE/TIMEOUT_ALWAYS and MALFORMED_RESPONSE/MALFORMED_ONCE/MALFORMED_ALWAYS with request-scoped counters.
- Provider abstraction allows offline and live modes, provider_call_count exposed for timeout verification.
- Recovery engine enforces one attempt per class via RecoveryContext flags.
- Metrics contract: output/metrics.json with baseline and recovery_active sections, completion_rate, silent_wrong_rate, mean_recovery_attempts.

## Gaps
None identified. Architecture aligns with assignment contract.
