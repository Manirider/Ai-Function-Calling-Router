from src.recovery import recover_missing_field, RecoveryContext
from src.llm_provider import OfflineProvider

def test_missing_field_recoverable():
    provider = OfflineProvider()
    provider.recovery_ctx = RecoveryContext()
    request = "Find flight"
    tool_name = "FlightSearch"
    missing_field = "date"
    original_args = {"origin":"A","destination":"B"}
    fixture = {"correct_args":{"origin":"A","destination":"B","date":"2025-01-01"}}
    new_args = recover_missing_field(provider, request, tool_name, missing_field, original_args, fixture)
    assert new_args is not None
    assert new_args["date"] == "2025-01-01"
    assert new_args["origin"] == "A"
    assert provider.recovery_ctx.missing_field_attempted

def test_missing_field_unrecoverable():
    provider = OfflineProvider()
    provider.recovery_ctx = RecoveryContext()
    request = "Find flight"
    tool_name = "FlightSearch"
    missing_field = "date"
    original_args = {"origin":"A"}
    fixture = {"correct_args":{"origin":"A","destination":"B"}}
    new_args = recover_missing_field(provider, request, tool_name, missing_field, original_args, fixture)
    assert new_args is None

def test_missing_field_max_one_attempt():
    provider = OfflineProvider()
    provider.recovery_ctx = RecoveryContext()
    fixture = {"correct_args":{"origin":"A","destination":"B","date":"2025-01-01"}}
    recover_missing_field(provider, "req","FlightSearch","date",{"origin":"A"}, fixture)
    # second attempt should be blocked
    result = recover_missing_field(provider, "req","FlightSearch","date",{"origin":"A"}, fixture)
    assert result is None
