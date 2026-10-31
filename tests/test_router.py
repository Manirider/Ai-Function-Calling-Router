from src.router import route_request

def test_happy_path():
    request = "Find flight from A to B on 2025-01-01"
    fixture = {
        "expected_tool":"FlightSearch",
        "injected_fault":{"type":"NONE","persistence":"once"},
        "correct_args":{"origin":"A","destination":"B","date":"2025-01-01"}
    }
    result, trace = route_request("r1","c1",request,fixture, recovery_enabled=True)
    assert result["status"] == "success"
    assert trace.final_status == "success"
    assert trace.provider_call_count == 1
    assert trace.recovery_attempts == 0

def test_missing_field_recovery():
    request = "Find flight from A to B"
    fixture = {
        "expected_tool":"FlightSearch",
        "injected_fault":{"type":"NONE","persistence":"once"},
        "correct_args":{"origin":"A","destination":"B","date":"2025-01-01"},
        "initial_argument_fault":"missing_field"
    }
    result, trace = route_request("r2","c2",request,fixture, recovery_enabled=True)
    assert result["status"] == "success"
    assert trace.recovery_policy == "missing_field"
    assert trace.recovery_attempts == 1
    assert trace.provider_call_count == 1  # no extra provider call

def test_timeout_recovery_no_provider_call():
    request = "Weather in Paris in C"
    fixture = {
        "expected_tool":"WeatherLookup",
        "injected_fault":{"type":"TIMEOUT","persistence":"once"},
        "correct_args":{"location":"Paris","unit":"C"}
    }
    result, trace = route_request("r3","c3",request,fixture, recovery_enabled=True)
    assert result["status"] == "success"
    assert trace.recovery_policy == "timeout"
    assert trace.provider_call_count == 1
    assert trace.tool_execution_attempts == 2  # initial + retry

def test_unknown_tool():
    request = "Do something weird"
    fixture = {"expected_tool":"Unknown","injected_fault":{"type":"NONE","persistence":"once"},"correct_args":{}}
    result, trace = route_request("r4","c4",request,fixture, recovery_enabled=True)
    assert result["status"] == "error"
    assert trace.final_failure_reason == "unknown_tool"
