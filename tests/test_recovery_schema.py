from src.recovery import recover_schema, RecoveryContext
from src.llm_provider import OfflineProvider

def test_schema_repair_success():
    provider = OfflineProvider()
    provider.recovery_ctx = RecoveryContext()
    fixture = {}
    args = {"location":"Paris","unit":"C"}
    repaired = recover_schema(provider, "WeatherLookup", {"invalid":1}, fixture, args)
    assert repaired is not None
    assert repaired["status"] == "success"

def test_schema_repair_unrecoverable_flag():
    provider = OfflineProvider()
    provider.recovery_ctx = RecoveryContext()
    fixture = {"schema_repair_unrecoverable": True}
    repaired = recover_schema(provider, "WeatherLookup", {"invalid":1}, fixture, {})
    assert repaired is None

def test_schema_repair_max_one_attempt():
    provider = OfflineProvider()
    provider.recovery_ctx = RecoveryContext()
    fixture = {}
    args = {"location":"Paris","unit":"C"}
    recover_schema(provider, "WeatherLookup", {"invalid":1}, fixture, args)
    result = recover_schema(provider, "WeatherLookup", {"invalid":1}, fixture, args)
    assert result is None
