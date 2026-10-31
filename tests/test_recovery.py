from src.recovery import recover_missing_field, recover_type_error, recover_schema, RecoveryContext
from src.llm_provider import OfflineProvider

def make_provider():
    p = OfflineProvider()
    p.recovery_ctx = RecoveryContext()
    return p

def test_missing_field_recoverable():
    p = make_provider()
    args = {"origin":"A","destination":"B"}
    fixture = {"correct_args":{"origin":"A","destination":"B","date":"2025-01-01"}}
    new_args = recover_missing_field(p, "req", "FlightSearch", "date", args, fixture)
    assert new_args["date"] == "2025-01-01"
    assert p.recovery_ctx.missing_field_attempted

def test_missing_field_unrecoverable():
    p = make_provider()
    args = {"origin":"A"}
    fixture = {"correct_args":{"origin":"A","destination":"B"}} # date missing
    new_args = recover_missing_field(p, "req", "FlightSearch", "date", args, fixture)
    assert new_args is None

def test_type_error_recoverable():
    p = make_provider()
    args = {"value":"bad"}
    fixture = {"correct_args":{"value":10,"from_unit":"m","to_unit":"km"}}
    new_args = recover_type_error(p, "req", "UnitConversion", "value", "bad", args, fixture)
    assert new_args["value"] == 10

def test_schema_repair_success():
    p = make_provider()
    fixture = {}
    args = {"location":"Paris","unit":"C"}
    repaired = recover_schema(p, "WeatherLookup", {"invalid":1}, fixture, args)
    assert repaired is not None
    assert repaired["status"] == "success"

def test_schema_repair_unrecoverable():
    p = make_provider()
    fixture = {"schema_repair_unrecoverable": True}
    repaired = recover_schema(p, "WeatherLookup", {"invalid":1}, fixture, {})
    assert repaired is None
