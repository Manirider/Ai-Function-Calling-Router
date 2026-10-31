from src.router import route_request

def test_missing_field_recovery_integration():
    fixture = {
        "expected_tool":"CalendarBooking",
        "injected_fault":{"type":"NONE","persistence":"once"},
        "correct_args":{"event_title":"Meeting","start_time":"2025-01-01T10:00:00","duration_minutes":60},
        "initial_argument_fault":"missing_field"
    }
    result, trace = route_request("i1","c1","Book meeting", fixture, recovery_enabled=True)
    assert result["status"] == "success"
    assert trace.recovery_policy == "missing_field"

def test_type_error_recovery_integration():
    fixture = {
        "expected_tool":"UnitConversion",
        "injected_fault":{"type":"NONE","persistence":"once"},
        "correct_args":{"value":10,"from_unit":"m","to_unit":"km"},
        "initial_argument_fault":"type_error"
    }
    result, trace = route_request("i2","c2","Convert", fixture, recovery_enabled=True)
    assert result["status"] == "success"
    assert trace.recovery_policy == "type_error"

def test_timeout_recovery_integration():
    fixture = {
        "expected_tool":"FlightSearch",
        "injected_fault":{"type":"TIMEOUT","persistence":"once"},
        "correct_args":{"origin":"A","destination":"B","date":"2025-01-01"}
    }
    result, trace = route_request("i3","c3","Find flight", fixture, recovery_enabled=True)
    assert result["status"] == "success"
    assert trace.recovery_policy == "timeout"
    assert trace.provider_call_count == 1

def test_schema_repair_integration():
    fixture = {
        "expected_tool":"WeatherLookup",
        "injected_fault":{"type":"MALFORMED_RESPONSE","persistence":"once"},
        "correct_args":{"location":"Paris","unit":"C"}
    }
    result, trace = route_request("i4","c4","Weather", fixture, recovery_enabled=True)
    assert result["status"] == "success"
    assert trace.recovery_policy == "schema_repair"
