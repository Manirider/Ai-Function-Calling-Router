from datetime import datetime
from pydantic import ValidationError
from typing import Dict, Any, Tuple
import time
from src.config import Config
from src.schemas import SuccessEnvelope, FailureEnvelope
from src.tools import TOOL_REGISTRY
from src.fault_injector import FaultInjector, TimeoutErrorException
from src.llm_provider import get_provider, ProviderResult
from src.recovery import (
    recover_missing_field,
    recover_type_error,
    recover_timeout,
    recover_schema,
    RecoveryContext
)
from src.telemetry import Trace

def _run_tool(tool_name: str, args: dict) -> Tuple[Any, bool]:
    registry = TOOL_REGISTRY.get(tool_name)
    if not registry:
        return None, False
    try:
        result = FaultInjector.apply(tool_name, registry["func"], args)
        # Validate output
        output_model = registry["output_model"]
        # If result is malformed marker
        if isinstance(result, dict) and "invalid" in result:
            # malformed
            return result, False
        # Validate via model
        output_model(**result)
        return result, True
    except TimeoutErrorException as e:
        raise e
    except ValidationError as ve:
        return {"validation_error": ve.errors()}, False
    except Exception as e:
        return {"exception": str(e)}, False

def route_request(request_id: str, dataset_case_id: str, request: str, fixture: dict, recovery_enabled: bool) -> Tuple[Dict[str, Any], Trace]:
    start = time.time()
    provider = get_provider()
    # attach recovery context
    provider.recovery_ctx = RecoveryContext()
    provider_call_count = 0

    # Extract
    prov_res: ProviderResult = provider.extract(request, request_id, fixture)
    provider_call_count = prov_res.call_count
    tool_name = prov_res.tool_name
    args = prov_res.args
    selected_tool = tool_name if tool_name in TOOL_REGISTRY else "Unknown"

    validation_result = "pending"
    failure_class = None
    recovery_policy = None
    recovery_attempts = 0
    tool_execution_attempts = 0
    output_validation_passed = False
    final_status = "error"
    final_failure_reason = None

    # Input validation
    registry = TOOL_REGISTRY.get(tool_name)
    if not registry:
        final_status = "error"
        final_failure_reason = "unknown_tool"
        duration_ms = (time.time() - start) * 1000
        trace = Trace(
            request_id=request_id,
            dataset_case_id=dataset_case_id,
            selected_tool=tool_name,
            provider_mode=Config.PROVIDER_MODE,
            validation_result="invalid_tool",
            failure_class="unknown_tool",
            recovery_policy=None,
            recovery_attempts=0,
            tool_execution_attempts=0,
            provider_call_count=provider_call_count,
            final_status=final_status,
            final_failure_reason=final_failure_reason,
            output_validation_passed=False,
            duration_ms=duration_ms
        )
        return {"status": "error", "reason": final_failure_reason}, trace

    input_model = registry["input_model"]
    try:
        validated = input_model(**args)
        validation_result = "passed"
    except ValidationError as ve:
        validation_result = "failed"
        errors = ve.errors()
        # Determine failure class
        missing = [e for e in errors if e.get("type") in ("missing", "missing_required_field")]
        type_err = [e for e in errors if e.get("type") not in ("missing", "missing_required_field")]
        if missing:
            failure_class = "missing_field"
            field_name = missing[0].get("loc")[0]
        elif type_err:
            failure_class = "type_error"
            field_name = type_err[0].get("loc")[0]
        else:
            failure_class = "validation_error"

        if recovery_enabled and failure_class == "missing_field":
            recovery_policy = "missing_field"
            recovery_attempts += 1
            new_args = recover_missing_field(provider, request, tool_name, field_name, args, fixture)
            if new_args:
                try:
                    validated = input_model(**new_args)
                    validation_result = "passed"
                    args = new_args
                    failure_class = None
                except ValidationError:
                    final_failure_reason = "missing_field_unrecoverable"
            else:
                final_failure_reason = "missing_field_unrecoverable"
        elif recovery_enabled and failure_class == "type_error":
            recovery_policy = "type_error"
            recovery_attempts += 1
            bad_val = args.get(field_name)
            new_args = recover_type_error(provider, request, tool_name, field_name, bad_val, args, fixture)
            if new_args:
                try:
                    validated = input_model(**new_args)
                    validation_result = "passed"
                    args = new_args
                    failure_class = None
                except ValidationError:
                    final_failure_reason = "type_error_unrecoverable"
            else:
                final_failure_reason = "type_error_unrecoverable"
        else:
            final_failure_reason = f"{failure_class}_unrecoverable"

    # Tool execution
    if validation_result == "passed":
        # set fault config
        fault_cfg = fixture.get("injected_fault", {})
        FaultInjector.reset_counters()
        FaultInjector.set_config({
            "type": fault_cfg.get("type", "NONE"),
            "persistence": fault_cfg.get("persistence", "once")
        })
        try:
            tool_execution_attempts += 1
            result, valid = _run_tool(tool_name, args)
            output_validation_passed = valid
            if valid:
                final_status = "success"
                final_failure_reason = None
            else:
                # malformed response
                failure_class = "malformed_response"
                if recovery_enabled:
                    recovery_policy = "schema_repair"
                    recovery_attempts += 1
                    repaired = recover_schema(provider, tool_name, result, fixture, args)
                    if repaired:
                        # Validate repaired payload
                        output_model = registry["output_model"]
                        try:
                            output_model(**repaired)
                            output_validation_passed = True
                            final_status = "success"
                            final_failure_reason = None
                            result = repaired
                        except ValidationError:
                            final_failure_reason = "schema_repair_unrecoverable"
                    else:
                        final_failure_reason = "schema_repair_unrecoverable"
                else:
                    final_failure_reason = "malformed_response"
        except TimeoutErrorException:
            failure_class = "timeout"
            if recovery_enabled:
                recovery_policy = "timeout"
                recovery_attempts += 1
                # retry without provider call
                # Do not reset config to preserve fault counters for once-persistence
                # attempt retry
                try:
                    tool_execution_attempts += 1
                    result, valid = _run_tool(tool_name, args)
                    output_validation_passed = valid
                    if valid:
                        final_status = "success"
                        final_failure_reason = None
                    else:
                        # still malformed?
                        final_failure_reason = "timeout_unrecoverable"
                except TimeoutErrorException:
                    final_failure_reason = "timeout_unrecoverable"
            else:
                final_failure_reason = "timeout"
        except Exception as e:
            final_failure_reason = "execution_error"

    duration_ms = (time.time() - start) * 1000
    trace = Trace(
        request_id=request_id,
        dataset_case_id=dataset_case_id,
        selected_tool=selected_tool,
        provider_mode=Config.PROVIDER_MODE,
        validation_result=validation_result,
        failure_class=failure_class,
        recovery_policy=recovery_policy,
        recovery_attempts=recovery_attempts,
        tool_execution_attempts=tool_execution_attempts,
        provider_call_count=provider_call_count,
        final_status=final_status,
        final_failure_reason=final_failure_reason,
        output_validation_passed=output_validation_passed,
        duration_ms=duration_ms
    )

    if final_status == "success":
        output_data = result if 'result' in locals() else None
        return {"status": "success", "data": {"tool": tool_name, "output": output_data}}, trace
    else:
        return {"status": "error", "reason": final_failure_reason or "unknown"}, trace

def process_request(request: str, use_recovery: bool = True, fixture: dict = None):
    import uuid
    request_id = str(uuid.uuid4())
    dataset_case_id = "cli"
    fixture = fixture or {}
    result, trace = route_request(request_id, dataset_case_id, request, fixture, use_recovery)
    return {
        "request_id": request_id,
        "original_request": request,
        "selected_tool": trace.selected_tool,
        "raw_arguments": None,
        "validated_arguments": None,
        "provider_call_count": trace.provider_call_count,
        "routing_status": trace.final_status,
        "validation_errors": trace.failure_class,
        "execution_status": "success" if trace.final_status == "success" else "error",
        "result": result,
        "trace": trace.to_dict()
    }
