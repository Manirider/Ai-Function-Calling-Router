from src.router import route_request

def run_case(case):
    fixture = {
        "expected_tool": case.get("expected_tool"),
        "injected_fault": case.get("injected_fault", {"type":"NONE","persistence":"once"}),
        "correct_args": case.get("correct_args", {}),
        "initial_argument_fault": case.get("initial_argument_fault"),
        "schema_repair_unrecoverable": case.get("schema_repair_unrecoverable", False)
    }
    result, trace = route_request(case["id"], case["id"], case["request"], fixture, recovery_enabled=True)
    return result, trace

def test_flight_search_semantic():
    case = {
        "id": "sem_flight",
        "request": "Find flight",
        "expected_tool": "FlightSearch",
        "injected_fault": {"type":"NONE","persistence":"once"},
        "correct_args": {"origin":"NYC","destination":"LAX","date":"2025-01-01"}
    }
    result, trace = run_case(case)
    assert result["status"] == "success"
    output = result["data"]["output"]
    assert output["origin"] == "NYC"
    assert output["destination"] == "LAX"
    assert str(output["date"]) == "2025-01-01"

def test_calendar_booking_semantic():
    case = {
        "id": "sem_cal",
        "request": "Book",
        "expected_tool": "CalendarBooking",
        "injected_fault": {"type":"NONE","persistence":"once"},
        "correct_args": {"event_title":"Meeting","start_time":"2025-01-01T10:00:00","duration_minutes":30}
    }
    result, trace = run_case(case)
    assert result["status"] == "success"
    output = result["data"]["output"]
    assert output["event_title"] == "Meeting"
    assert output["duration_minutes"] == 30

def test_weather_lookup_semantic():
    case = {
        "id": "sem_weather",
        "request": "Weather",
        "expected_tool": "WeatherLookup",
        "injected_fault": {"type":"NONE","persistence":"once"},
        "correct_args": {"location":"Paris","unit":"C"}
    }
    result, trace = run_case(case)
    assert result["status"] == "success"
    output = result["data"]["output"]
    assert output["location"] == "Paris"
    assert output["unit"] == "C"

def test_unit_conversion_semantic():
    case = {
        "id": "sem_conv",
        "request": "Convert",
        "expected_tool": "UnitConversion",
        "injected_fault": {"type":"NONE","persistence":"once"},
        "correct_args": {"value":10,"from_unit":"m","to_unit":"km"}
    }
    result, trace = run_case(case)
    assert result["status"] == "success"
    output = result["data"]["output"]
    assert output["original_value"] == 10
    assert output["original_unit"] == "m"
    assert output["converted_unit"] == "km"
    # 10 * 1.1 = 11.0
    assert abs(output["converted_value"] - 11.0) < 1e-6
