from src.recovery import recover_type_error, RecoveryContext
from src.llm_provider import OfflineProvider

def test_type_error_recoverable():
    provider = OfflineProvider()
    provider.recovery_ctx = RecoveryContext()
    request = "convert"
    tool_name = "UnitConversion"
    field_name = "value"
    bad_value = "bad"
    original_args = {"value":"bad","from_unit":"m","to_unit":"km"}
    fixture = {"correct_args":{"value":10,"from_unit":"m","to_unit":"km"}}
    new_args = recover_type_error(provider, request, tool_name, field_name, bad_value, original_args, fixture)
    assert new_args is not None
    assert new_args["value"] == 10
    assert provider.recovery_ctx.type_error_attempted

def test_type_error_unrecoverable():
    provider = OfflineProvider()
    provider.recovery_ctx = RecoveryContext()
    fixture = {"correct_args":{"from_unit":"m","to_unit":"km"}}
    new_args = recover_type_error(provider, "req","UnitConversion","value","bad",{"value":"bad"}, fixture)
    assert new_args is None

def test_type_error_max_one_attempt():
    provider = OfflineProvider()
    provider.recovery_ctx = RecoveryContext()
    fixture = {"correct_args":{"value":5}}
    recover_type_error(provider, "req","UnitConversion","value","bad",{"value":"bad"}, fixture)
    result = recover_type_error(provider, "req","UnitConversion","value","bad",{"value":"bad"}, fixture)
    assert result is None
