import json
from pathlib import Path
from src.schemas import FlightSearchInput, FlightSearchOutput
from src.fault_injector import FaultDirective
from src.router import route_request

def test_req1_pydantic_schemas():
    # schemas exist and validate
    FlightSearchInput(origin="A", destination="B", date="2025-01-01")
    FlightSearchOutput(status="success", flight_id="FL-AB-2025-01-01", origin="A", destination="B", date="2025-01-01")

def test_req2_fault_injection():
    from src.fault_injector import FaultInjector, TimeoutErrorException
    FaultInjector.reset_counters()
    FaultInjector.set_config({"type":"TIMEOUT","persistence":"once"})
    try:
        FaultInjector.apply("T", lambda a: {"ok":True}, {})
        assert False
    except TimeoutErrorException:
        pass

def test_req3_happy_path():
    fixture = {"expected_tool":"FlightSearch","injected_fault":{"type":"NONE","persistence":"once"},"correct_args":{"origin":"A","destination":"B","date":"2025-01-01"}}
    result, trace = route_request("r","c","req", fixture, recovery_enabled=True)
    assert result["status"] == "success"

def test_req4_missing_field_recovery():
    fixture = {"expected_tool":"FlightSearch","injected_fault":{"type":"NONE","persistence":"once"},"correct_args":{"origin":"A","destination":"B","date":"2025-01-01"},"initial_argument_fault":"missing_field"}
    result, trace = route_request("r","c","req", fixture, recovery_enabled=True)
    assert result["status"] == "success"
    assert trace.recovery_policy == "missing_field"

def test_req5_type_error_recovery():
    fixture = {"expected_tool":"UnitConversion","injected_fault":{"type":"NONE","persistence":"once"},"correct_args":{"value":10,"from_unit":"m","to_unit":"km"},"initial_argument_fault":"type_error"}
    result, trace = route_request("r","c","req", fixture, recovery_enabled=True)
    assert result["status"] == "success"
    assert trace.recovery_policy == "type_error"

def test_req6_timeout_no_provider_call():
    fixture = {"expected_tool":"WeatherLookup","injected_fault":{"type":"TIMEOUT","persistence":"once"},"correct_args":{"location":"Paris","unit":"C"}}
    result, trace = route_request("r","c","req", fixture, recovery_enabled=True)
    assert result["status"] == "success"
    assert trace.provider_call_count == 1

def test_req7_schema_repair():
    fixture = {"expected_tool":"WeatherLookup","injected_fault":{"type":"MALFORMED_RESPONSE","persistence":"once"},"correct_args":{"location":"Paris","unit":"C"}}
    result, trace = route_request("r","c","req", fixture, recovery_enabled=True)
    assert result["status"] == "success"
    assert trace.recovery_policy == "schema_repair"

def test_req8_explicit_failure():
    fixture = {"expected_tool":"WeatherLookup","injected_fault":{"type":"TIMEOUT","persistence":"always"},"correct_args":{"location":"Paris","unit":"C"}}
    result, trace = route_request("r","c","req", fixture, recovery_enabled=True)
    assert result["status"] == "error"
    assert trace.final_failure_reason == "timeout_unrecoverable"

def test_req9_evaluation():
    metrics = json.loads(Path('output/metrics.json').read_text())
    assert "baseline" in metrics
    assert "recovery_active" in metrics
    assert metrics["baseline"]["mean_recovery_attempts"] == 0

def test_req10_docker_files():
    assert Path('Dockerfile').exists()
    assert Path('docker-compose.yml').exists()
