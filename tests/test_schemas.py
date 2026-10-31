import pytest
from src.schemas import (
    FlightSearchInput, CalendarBookingInput, WeatherLookupInput, UnitConversionInput,
    FlightSearchOutput, CalendarBookingOutput, WeatherLookupOutput, UnitConversionOutput
)
from pydantic import ValidationError

def test_flight_search_valid():
    data = {"origin":"NYC","destination":"LON","date":"2025-01-01"}
    m = FlightSearchInput(**data)
    assert m.origin == "NYC"

def test_flight_search_missing():
    with pytest.raises(ValidationError):
        FlightSearchInput(origin="A", destination="B")

def test_flight_search_empty_origin():
    with pytest.raises(ValidationError):
        FlightSearchInput(origin="  ", destination="B", date="2025-01-01")

def test_calendar_booking_positive_duration():
    m = CalendarBookingInput(event_title="X", start_time="2025-01-01T10:00:00", duration_minutes=1)
    assert m.duration_minutes == 1

def test_calendar_booking_zero_duration():
    with pytest.raises(ValidationError):
        CalendarBookingInput(event_title="X", start_time="2025-01-01T10:00:00", duration_minutes=0)

def test_weather_unit_enum():
    m = WeatherLookupInput(location="Paris", unit="C")
    assert m.unit == "C"
    with pytest.raises(ValidationError):
        WeatherLookupInput(location="Paris", unit="K")

def test_unit_conversion_finite():
    m = UnitConversionInput(value=1.5, from_unit="m", to_unit="km")
    assert m.value == 1.5

def test_unit_conversion_bool_rejected():
    # bool is subclass of int, should be rejected
    with pytest.raises(ValidationError):
        UnitConversionInput(value=True, from_unit="m", to_unit="km")

def test_output_models():
    out = FlightSearchOutput(status="success", flight_id="FL-AB", origin="A", destination="B", date="2025-01-01")
    assert out.status == "success"
