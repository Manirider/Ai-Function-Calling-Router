from src.router import route_request
from src.fault_injector import FaultInjector

def test_empty_request():
    fixture = {"expected_tool":"FlightSearch","injected_fault":{"type":"NONE","persistence":"once"},"correct_args":{}}
    result, trace = route_request("adv1","c1","", fixture, recovery_enabled=True)
    # Should fail validation
    assert result["status"] == "error"

def test_unknown_tool():
    fixture = {"expected_tool":"UnknownTool","injected_fault":{"type":"NONE","persistence":"once"},"correct_args":{}}
    result, trace = route_request("adv2","c2","request", fixture, recovery_enabled=True)
    assert result["status"] == "error"
    assert trace.final_failure_reason == "unknown_tool"

def test_missing_field_unrecoverable():
    fixture = {
        "expected_tool":"FlightSearch",
        "injected_fault":{"type":"NONE","persistence":"once"},
        "correct_args":{"origin":"A","destination":"B"},  # date missing
        "initial_argument_fault":"missing_field"
    }
    result, trace = route_request("adv3","c3","request", fixture, recovery_enabled=True)
    assert result["status"] == "error"
    assert trace.final_failure_reason == "missing_field_unrecoverable"

def test_timeout_always_exhausts():
    fixture = {
        "expected_tool":"WeatherLookup",
        "injected_fault":{"type":"TIMEOUT","persistence":"always"},
        "correct_args":{"location":"Paris","unit":"C"}
    }
    result, trace = route_request("adv4","c4","request", fixture, recovery_enabled=True)
    assert result["status"] == "error"
    assert trace.final_failure_reason == "timeout_unrecoverable"
    assert trace.provider_call_count == 1

def test_concurrent_isolation():
    # Simulate two requests with different configs
    from src.fault_injector import FaultInjector, TimeoutErrorException
    from src.tools import TOOL_REGISTRY
    FaultInjector.reset_counters()
    FaultInjector.set_config({"type":"TIMEOUT","persistence":"once"})
    # First call should timeout
    try:
        FaultInjector.apply("A", TOOL_REGISTRY["FlightSearch"]["func"], {"origin":"A","destination":"B","date":"2025-01-01"})
        assert False, "Expected timeout"
    except TimeoutErrorException:
        pass
    # Second call with different tool should also timeout first time due to per-tool counter
    try:
        FaultInjector.apply("B", TOOL_REGISTRY["FlightSearch"]["func"], {"origin":"A","destination":"B","date":"2025-01-01"})
        assert False, "Expected timeout"
    except TimeoutErrorException:
        pass

def test_schema_repair_persistent_fails():
    fixture = {
        "expected_tool":"WeatherLookup",
        "injected_fault":{"type":"MALFORMED_RESPONSE","persistence":"always"},
        "correct_args":{"location":"Paris","unit":"C"}
    }
    result, trace = route_request("adv5","c5","request", fixture, recovery_enabled=True)
    assert result["status"] == "error"
    assert trace.final_failure_reason == "schema_repair_unrecoverable"
