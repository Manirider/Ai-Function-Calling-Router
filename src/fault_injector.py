from contextvars import ContextVar
from typing import Callable, Any, Dict, Literal
from contextlib import contextmanager
from enum import Enum

class TimeoutErrorException(Exception):
    pass

class FaultDirective(Enum):
    NONE = "NONE"
    TIMEOUT = "TIMEOUT"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"

class FaultConfiguration:
    def __init__(self, directive: FaultDirective, persistence: Literal["once","always"] = "once"):
        self.directive = directive
        self.persistence = persistence

fault_config_var: ContextVar[FaultConfiguration] = ContextVar('fault_config', default=FaultConfiguration(FaultDirective.NONE, "once"))
counters_var: ContextVar[dict] = ContextVar('fault_counters', default={})
events_var: ContextVar[list] = ContextVar('fault_events', default=[])

def _parse_directive(type_str: str) -> FaultDirective:
    t = type_str.upper()
    if t in ("NONE",):
        return FaultDirective.NONE
    if t in ("TIMEOUT", "TIMEOUT_ONCE", "TIMEOUT_ALWAYS"):
        return FaultDirective.TIMEOUT
    if t in ("MALFORMED", "MALFORMED_RESPONSE", "MALFORMED_ONCE", "MALFORMED_ALWAYS"):
        return FaultDirective.MALFORMED_RESPONSE
    return FaultDirective.NONE

class FaultInjector:
    @classmethod
    def set_config(cls, config: dict):
        directive = _parse_directive(config.get("type", "NONE"))
        persistence = config.get("persistence", "once").lower()
        # Normalize aliases
        type_str = config.get("type", "NONE").upper()
        if type_str == "TIMEOUT_ONCE":
            persistence = "once"
        elif type_str == "TIMEOUT_ALWAYS":
            persistence = "always"
        elif type_str == "MALFORMED_ONCE":
            persistence = "once"
        elif type_str == "MALFORMED_ALWAYS":
            persistence = "always"
        cfg = FaultConfiguration(directive, persistence)
        fault_config_var.set(cfg)

    @classmethod
    def reset_counters(cls):
        counters_var.set({})

    @classmethod
    def get_config(cls) -> FaultConfiguration:
        return fault_config_var.get()

    @classmethod
    def _inc(cls, key: str):
        counters = counters_var.get()
        val = counters.get(key, 0)
        counters[key] = val + 1
        counters_var.set(counters)
        return val

    @classmethod
    @contextmanager
    def fault_context(cls, config: dict):
        # Save previous
        token_cfg = fault_config_var.set(FaultConfiguration(_parse_directive(config.get("type","NONE")), config.get("persistence","once").lower()))
        token_cnt = counters_var.set({})
        token_events = events_var.set([])
        try:
            yield
        finally:
            fault_config_var.reset(token_cfg)
            counters_var.reset(token_cnt)
            events_var.reset(token_events)

    @classmethod
    def apply(cls, tool_name: str, func: Callable[[dict], Any], args: dict) -> Any:
        cfg = cls.get_config()
        directive = cfg.directive
        persistence = cfg.persistence

        # Record event start
        events = events_var.get()
        attempt = len([e for e in events if e["tool_name"] == tool_name]) + 1

        if directive == FaultDirective.NONE:
            result = func(args)
            events.append({
                "request_id": None,
                "tool_name": tool_name,
                "fault_directive": "NONE",
                "execution_attempt": attempt,
                "injected_failure": False,
                "execution_outcome": "success"
            })
            events_var.set(events)
            return result

        # Determine if fault should trigger
        if directive == FaultDirective.TIMEOUT:
            should_trigger = persistence == "always" or cls._inc(f"{tool_name}_timeout") == 0
        elif directive == FaultDirective.MALFORMED_RESPONSE:
            should_trigger = persistence == "always" or cls._inc(f"{tool_name}_malformed") == 0
        else:
            should_trigger = False

        if directive == FaultDirective.TIMEOUT and should_trigger:
            events.append({
                "request_id": None,
                "tool_name": tool_name,
                "fault_directive": "TIMEOUT",
                "execution_attempt": attempt,
                "injected_failure": True,
                "execution_outcome": "timeout"
            })
            events_var.set(events)
            raise TimeoutErrorException(f"Injected timeout for {tool_name}")

        # Execute tool first
        result = func(args)

        if directive == FaultDirective.MALFORMED_RESPONSE and should_trigger:
            # Corrupt payload deterministically
            corrupted = dict(result)
            # Change status to invalid to ensure Pydantic rejection
            if "status" in corrupted:
                corrupted["status"] = "invalid"
            else:
                # fallback: remove first key
                first_key = next(iter(corrupted), None)
                if first_key:
                    corrupted.pop(first_key, None)
            events.append({
                "request_id": None,
                "tool_name": tool_name,
                "fault_directive": "MALFORMED_RESPONSE",
                "execution_attempt": attempt,
                "injected_failure": True,
                "execution_outcome": "malformed"
            })
            events_var.set(events)
            return corrupted

        # Normal success
        events.append({
            "request_id": None,
            "tool_name": tool_name,
            "fault_directive": directive.name,
            "execution_attempt": attempt,
            "injected_failure": False,
            "execution_outcome": "success"
        })
        events_var.set(events)
        return result
