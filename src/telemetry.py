from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

@dataclass
class Trace:
    request_id: str
    dataset_case_id: str
    selected_tool: str
    provider_mode: str
    validation_result: str
    failure_class: Optional[str]
    recovery_policy: Optional[str]
    recovery_attempts: int
    tool_execution_attempts: int
    provider_call_count: int
    final_status: str
    final_failure_reason: Optional[str]
    output_validation_passed: bool
    duration_ms: float

    def to_dict(self):
        return asdict(self)
