from src.router import route_request

def test_no_infinite_loop_missing_field():
    fixture = {
        "expected_tool":"FlightSearch",
        "injected_fault":{"type":"NONE","persistence":"once"},
        "correct_args":{"origin":"A","destination":"B","date":"2025-01-01"},
        "initial_argument_fault":"missing_field"
    }
    result, trace = route_request("id1","c1","Find flight", fixture, recovery_enabled=True)
    assert result["status"] == "success"
    assert trace.recovery_attempts == 1

def test_no_infinite_loop_timeout_always():
    fixture = {
        "expected_tool":"WeatherLookup",
        "injected_fault":{"type":"TIMEOUT","persistence":"always"},
        "correct_args":{"location":"Paris","unit":"C"}
    }
    result, trace = route_request("id2","c2","Weather", fixture, recovery_enabled=True)
    assert result["status"] == "error"
    assert trace.final_failure_reason == "timeout_unrecoverable"
    assert trace.tool_execution_attempts == 2  # initial + one retry
    assert trace.provider_call_count == 1

def test_exact_failure_reasons():
    fixture = {
        "expected_tool":"FlightSearch",
        "injected_fault":{"type":"NONE","persistence":"once"},
        "correct_args":{"origin":"A","destination":"B"},
        "initial_argument_fault":"missing_field"
    }
    result, trace = route_request("id3","c3","Find", fixture, recovery_enabled=True)
    assert trace.final_failure_reason == "missing_field_unrecoverable"
