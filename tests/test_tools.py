import pytest
from src.tools import flight_search_impl, calendar_booking_impl, weather_lookup_impl, unit_conversion_impl
from src.schemas import FlightSearchInput, CalendarBookingInput, WeatherLookupInput, UnitConversionInput
from pydantic import ValidationError

def test_flight_search_impl_valid():
    args = {"origin":"NYC","destination":"LON","date":"2025-01-01"}
    out = flight_search_impl(args)
    assert out["status"] == "success"
    assert out["origin"] == "NYC"
    assert out["destination"] == "LON"

def test_flight_search_impl_invalid_date():
    with pytest.raises(ValidationError):
        flight_search_impl({"origin":"A","destination":"B","date":"2025-13-01"})

def test_calendar_booking_impl_valid():
    args = {"event_title":"Meeting","start_time":"2025-01-01T10:00:00","duration_minutes":30}
    out = calendar_booking_impl(args)
    assert out["status"] == "success"
    assert out["duration_minutes"] == 30

def test_calendar_booking_impl_bool_duration():
    with pytest.raises(ValidationError):
        calendar_booking_impl({"event_title":"X","start_time":"2025-01-01T10:00:00","duration_minutes":True})

def test_weather_lookup_impl_valid():
    args = {"location":"Paris","unit":"C"}
    out = weather_lookup_impl(args)
    assert out["status"] == "success"
    assert out["unit"] == "C"

def test_unit_conversion_impl_valid():
    args = {"value":10,"from_unit":"m","to_unit":"km"}
    out = unit_conversion_impl(args)
    assert out["status"] == "success"
    assert out["original_value"] == 10.0

def test_unit_conversion_impl_bool_value():
    with pytest.raises(ValidationError):
        unit_conversion_impl({"value":True,"from_unit":"m","to_unit":"km"})

def test_unit_conversion_impl_nan():
    import math
    with pytest.raises(ValidationError):
        unit_conversion_impl({"value":float('nan'),"from_unit":"m","to_unit":"km"})
