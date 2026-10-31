import json
import os
import hashlib
from datetime import datetime
from src.evaluation import load_eval_dataset, compute_checksum
from src.router import route_request
from src.config import Config
from src.tools import TOOL_REGISTRY

def validate_dataset(cases):
    ids = set()
    for c in cases:
        if not c.get("id"):
            raise ValueError("Missing id")
        if c["id"] in ids:
            raise ValueError(f"Duplicate id {c['id']}")
        ids.add(c["id"])
        if not c.get("request"):
            raise ValueError(f"Empty request for {c['id']}")
        tool = c.get("expected_tool")
        if tool not in TOOL_REGISTRY and tool != "Unknown":
            raise ValueError(f"Unknown tool {tool} in {c['id']}")
        fault = c.get("injected_fault", {})
        if not isinstance(fault, dict) or "type" not in fault:
            raise ValueError(f"Invalid fault in {c['id']}")
    return True

def run_mode(mode, cases, output_dir):
    successes = 0
    silent_wrongs = 0
    total_recovery_attempts = 0
    total_tool_exec = 0
    total_provider_calls = 0
    latencies = []
    per_case = []
    failure_dist = {}
    recovery_dist = {}
    per_tool = {t: {"total":0,"success":0} for t in TOOL_REGISTRY}
    per_tool["Unknown"] = {"total":0,"success":0}

    for case in cases:
        request_id = case.get("id")
        dataset_id = case.get("id")
        request = case.get("request")
        fixture = {
            "expected_tool": case.get("expected_tool"),
            "injected_fault": case.get("injected_fault", {"type":"NONE","persistence":"once"}),
            "correct_args": case.get("correct_args", {}),
            "initial_argument_fault": case.get("initial_argument_fault"),
            "schema_repair_unrecoverable": case.get("schema_repair_unrecoverable", False)
        }
        result, trace = route_request(request_id, dataset_id, request, fixture, recovery_enabled=(mode=="recovery"))
        total_recovery_attempts += trace.recovery_attempts
        total_tool_exec += trace.tool_execution_attempts
        total_provider_calls += trace.provider_call_count
        latencies.append(trace.duration_ms)
        tool_key = trace.selected_tool if trace.selected_tool in per_tool else "Unknown"
        per_tool[tool_key]["total"] += 1
        if trace.final_status == "success":
            successes += 1
            per_tool[tool_key]["success"] += 1
        # silent wrong detection
        silent = False
        if result.get("status") == "success" and not trace.output_validation_passed:
            silent = True
            silent_wrongs += 1
        # failure distribution
        fc = trace.failure_class or "none"
        failure_dist[fc] = failure_dist.get(fc,0)+1
        rp = trace.recovery_policy or "none"
        recovery_dist[rp] = recovery_dist.get(rp,0)+1
        per_case.append({
            "id": request_id,
            "mode": mode,
            "selected_tool": trace.selected_tool,
            "final_status": trace.final_status,
            "final_failure_reason": trace.final_failure_reason,
            "validation_result": trace.validation_result,
            "failure_class": trace.failure_class,
            "recovery_policy": trace.recovery_policy,
            "recovery_attempts": trace.recovery_attempts,
            "tool_execution_attempts": trace.tool_execution_attempts,
            "provider_call_count": trace.provider_call_count,
            "output_validation_passed": trace.output_validation_passed,
            "duration_ms": trace.duration_ms,
            "silent_wrong": silent
        })

    total = len(cases)
    completion_rate = successes/total if total else 0
    silent_wrong_rate = silent_wrongs/total if total else 0
    mean_recovery_attempts = total_recovery_attempts/total if total else 0
    return {
        "completion_rate": completion_rate,
        "silent_wrong_rate": silent_wrong_rate,
        "mean_recovery_attempts": mean_recovery_attempts,
        "total": total,
        "successes": successes,
        "silent_wrongs": silent_wrongs,
        "per_case": per_case,
        "failure_dist": failure_dist,
        "recovery_dist": recovery_dist,
        "per_tool": per_tool,
        "latencies": latencies,
        "total_tool_exec": total_tool_exec,
        "total_provider_calls": total_provider_calls
    }

def write_atomic(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        if isinstance(data, dict):
            json.dump(data, f, indent=2)
        else:
            json.dump(data, f)
    os.replace(tmp, path)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="data/eval.jsonl")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--provider-mode", default=None)
    parser.add_argument("--reference-date", default=None)
    args = parser.parse_args()
    cfg = Config()
    output_dir = args.output_dir or cfg.OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)
    cases = load_eval_dataset(args.dataset)
    validate_dataset(cases)
    checksum = compute_checksum(cases)
    # baseline
    base_res = run_mode("baseline", cases, output_dir)
    rec_res = run_mode("recovery", cases, output_dir)
    # metrics
    metrics = {
        "baseline": {
            "completion_rate": base_res["completion_rate"],
            "silent_wrong_rate": base_res["silent_wrong_rate"],
            "mean_recovery_attempts": 0.0
        },
        "recovery_active": {
            "completion_rate": rec_res["completion_rate"],
            "silent_wrong_rate": rec_res["silent_wrong_rate"],
            "mean_recovery_attempts": rec_res["mean_recovery_attempts"]
        }
    }
    write_atomic(os.path.join(output_dir, "metrics.json"), metrics)
    # supplemental artifacts
    # dataset coverage
    from collections import Counter
    tools = Counter(c.get("expected_tool") for c in cases)
    faults = Counter(json.dumps(c.get("injected_fault",{}), sort_keys=True) for c in cases)
    coverage = {
        "dataset_size": len(cases),
        "checksum_sha256": checksum,
        "tool_distribution": dict(tools),
        "fault_distribution": {k: v for k,v in faults.items()},
        "reference_date": cfg.EVALUATION_REFERENCE_DATE
    }
    write_atomic(os.path.join(output_dir, "dataset_coverage.json"), coverage)
    # per case results
    all_cases = base_res["per_case"] + rec_res["per_case"]
    with open(os.path.join(output_dir, "per_case_results.jsonl"), "w", encoding="utf-8") as f:
        for c in all_cases:
            f.write(json.dumps(c)+"\n")
    # recovery breakdown
    breakdown = {
        "baseline": {
            "failure_distribution": base_res["failure_dist"],
            "recovery_distribution": base_res["recovery_dist"],
            "per_tool_completion": {k: (v["success"]/v["total"] if v["total"] else 0) for k,v in base_res["per_tool"].items()}
        },
        "recovery_active": {
            "failure_distribution": rec_res["failure_dist"],
            "recovery_distribution": rec_res["recovery_dist"],
            "per_tool_completion": {k: (v["success"]/v["total"] if v["total"] else 0) for k,v in rec_res["per_tool"].items()}
        }
    }
    write_atomic(os.path.join(output_dir, "recovery_breakdown.json"), breakdown)
    # evaluation report
    lat = rec_res["latencies"]
    p50 = sorted(lat)[len(lat)//2] if lat else 0
    p95 = sorted(lat)[int(len(lat)*0.95)] if lat else 0
    report = {
        "dataset_size": len(cases),
        "checksum_sha256": checksum,
        "baseline_completion_rate": base_res["completion_rate"],
        "recovery_completion_rate": rec_res["completion_rate"],
        "baseline_silent_wrong_rate": base_res["silent_wrong_rate"],
        "recovery_silent_wrong_rate": rec_res["silent_wrong_rate"],
        "mean_recovery_attempts": rec_res["mean_recovery_attempts"],
        "total_provider_calls": rec_res["total_provider_calls"],
        "total_tool_executions": rec_res["total_tool_exec"],
        "p50_latency_ms": p50,
        "p95_latency_ms": p95,
        "generated_at": datetime.utcnow().isoformat()+"Z"
    }
    write_atomic(os.path.join(output_dir, "evaluation_report.json"), report)
    print(json.dumps(metrics, indent=2))

if __name__ == "__main__":
    main()
