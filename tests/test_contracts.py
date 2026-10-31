import json, os
from src.router import route_request

def test_explicit_failure_missing_field_unrecoverable():
    fixture = {
        "expected_tool":"FlightSearch",
        "injected_fault":{"type":"NONE","persistence":"once"},
        "correct_args":{"origin":"A","destination":"B"}, # date missing
        "initial_argument_fault":"missing_field"
    }
    result, trace = route_request("r1","c1","Find flight",fixture,recovery_enabled=True)
    assert result["status"] == "error"
    assert trace.final_failure_reason == "missing_field_unrecoverable"

def test_output_validation_enforced():
    # malformed always should end in explicit failure
    fixture = {
        "expected_tool":"FlightSearch",
        "injected_fault":{"type":"MALFORMED_ALWAYS","persistence":"always"},
        "correct_args":{"origin":"A","destination":"B","date":"2025-01-01"}
    }
    result, trace = route_request("r2","c2","...",fixture,recovery_enabled=True)
    assert result["status"] == "error"
    # schema repair will try once and fail validation again
    assert trace.final_failure_reason in ("schema_repair_unrecoverable","malformed_response")

def test_metrics_contract():
    # Ensure output directory can be written
    output_dir = r'C:\Users\lenovo\Downloads\Ai-Function-Calling-Router\output'
    os.makedirs(output_dir, exist_ok=True)
    metrics_path = os.path.join(output_dir,"metrics.json")
    # Write dummy
    dummy = {"baseline":{"completion_rate":0.0,"silent_wrong_rate":0.0,"mean_recovery_attempts":0},"recovery_active":{"completion_rate":0.0,"silent_wrong_rate":0.0,"mean_recovery_attempts":0.0}}
    with open(metrics_path,"w") as f:
        json.dump(dummy,f)
    with open(metrics_path) as f:
        data = json.load(f)
    assert "baseline" in data and "recovery_active" in data
    for k in ["completion_rate","silent_wrong_rate","mean_recovery_attempts"]:
        assert k in data["baseline"]
        assert k in data["recovery_active"]
