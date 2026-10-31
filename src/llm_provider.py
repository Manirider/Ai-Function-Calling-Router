from src.config import Config
from typing import Dict, Any, Tuple

class ProviderResult:
    def __init__(self, tool_name: str, args: dict, call_count: int):
        self.tool_name = tool_name
        self.args = args
        self.call_count = call_count

class BaseProvider:
    def extract(self, request: str, request_id: str, fixture: dict) -> ProviderResult:
        raise NotImplementedError

class OfflineProvider(BaseProvider):
    # simple deterministic mapping based on fixture hints
    def __init__(self):
        self.call_count = 0

    def extract(self, request: str, request_id: str, fixture: dict) -> ProviderResult:
        self.call_count += 1
        tool_name = fixture.get("expected_tool")
        if not tool_name:
            # fallback heuristic
            lower = request.lower()
            if "flight" in lower:
                tool_name = "FlightSearch"
            elif "calendar" in lower or "book" in lower:
                tool_name = "CalendarBooking"
            elif "weather" in lower:
                tool_name = "WeatherLookup"
            elif "convert" in lower:
                tool_name = "UnitConversion"
            else:
                tool_name = "Unknown"

        args = {}
        # use fixture initial_argument_fault to simulate extraction errors
        fault = fixture.get("initial_argument_fault")
        # base correct args from fixture hints
        correct_args = fixture.get("correct_args", {})
        if fault == "missing_field":
            # drop a required field
            # choose first key
            if correct_args:
                key = next(iter(correct_args))
                args = {k: v for k, v in correct_args.items() if k != key}
            else:
                args = {}
        elif fault == "type_error":
            # corrupt a field type
            args = correct_args.copy()
            if args:
                key = next(iter(args))
                val = args[key]
                if isinstance(val, str) and "date" in str(key):
                    args[key] = "not-a-date"
                elif isinstance(val, int):
                    args[key] = "not-an-int"
                else:
                    args[key] = 123
        else:
            args = correct_args.copy()

        return ProviderResult(tool_name, args, self.call_count)

class OpenAICompatibleProvider(BaseProvider):
    def __init__(self):
        self.call_count = 0
        self.api_key = Config.LLM_API_KEY
        self.model = Config.LLM_MODEL_ID

    def extract(self, request: str, request_id: str, fixture: dict) -> ProviderResult:
        if not self.api_key:
            raise RuntimeError("LLM_API_KEY not configured for live provider")
        self.call_count += 1
        # Simplified: in real implementation call OpenAI API, parse JSON
        # For now raise NotImplementedError to avoid silent fallback
        raise NotImplementedError("OpenAICompatibleProvider requires live API call")

class LiveProvider(BaseProvider):
    def extract(self, request: str, request_id: str, fixture: dict) -> ProviderResult:
        raise NotImplementedError("Live provider not implemented in offline mode")

def get_provider() -> BaseProvider:
    cfg = Config()
    cfg.validate()
    if cfg.PROVIDER_MODE == "live":
        return OpenAICompatibleProvider()
    return OfflineProvider()
