import pytest
from src.tool_registry import get_tool, list_tools, validate_arguments, execute_tool, ToolRegistryError
from pydantic import ValidationError

def test_list_tools():
    tools = list_tools()
    assert set(tools) == {"FlightSearch","CalendarBooking","WeatherLookup","UnitConversion"}

def test_get_tool_known():
    t = get_tool("FlightSearch")
    assert "input_model" in t
    assert "output_model" in t
    assert "func" in t

def test_get_tool_unknown():
    with pytest.raises(ToolRegistryError):
        get_tool("NonExistent")

def test_validate_arguments_success():
    args = {"origin":"A","destination":"B","date":"2025-01-01"}
    m = validate_arguments("FlightSearch", args)
    assert m.origin == "A"

def test_validate_arguments_fail():
    with pytest.raises(ValidationError):
        validate_arguments("FlightSearch", {"origin":"A"})

def test_execute_tool_success():
    args = {"location":"Paris","unit":"F"}
    out = execute_tool("WeatherLookup", args)
    assert out["status"] == "success"
    assert out["location"] == "Paris"

def test_execute_tool_invalid_output():
    # Monkey patch to produce invalid output
    from src import tools
    original = tools.weather_lookup_impl
    def bad_impl(args):
        return {"status":"success"}  # missing fields
    tools.TOOL_REGISTRY["WeatherLookup"]["func"] = bad_impl
    try:
        with pytest.raises(ValidationError):
            execute_tool("WeatherLookup", {"location":"Paris","unit":"C"})
    finally:
        tools.TOOL_REGISTRY["WeatherLookup"]["func"] = original
