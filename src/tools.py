from datetime import date, datetime
from src.schemas import (
    FlightSearchInput, FlightSearchOutput,
    CalendarBookingInput, CalendarBookingOutput,
    WeatherLookupInput, WeatherLookupOutput,
    UnitConversionInput, UnitConversionOutput
)

def flight_search_impl(args: dict):
    inp = FlightSearchInput(**args)
    flight_id = f"FL-{inp.origin[:2].upper()}{inp.destination[:2].upper()}-{inp.date.isoformat()}"
    return FlightSearchOutput(
        status="success",
        flight_id=flight_id,
        origin=inp.origin,
        destination=inp.destination,
        date=inp.date
    ).model_dump(mode='python')

def calendar_booking_impl(args: dict):
    inp = CalendarBookingInput(**args)
    booking_id = f"BK-{abs(hash(inp.event_title + inp.start_time.isoformat())) % 100000:05d}"
    return CalendarBookingOutput(
        status="success",
        booking_id=booking_id,
        event_title=inp.event_title,
        start_time=inp.start_time,
        duration_minutes=inp.duration_minutes
    ).model_dump(mode='python')

def weather_lookup_impl(args: dict):
    inp = WeatherLookupInput(**args)
    # deterministic fake temperature based on location hash
    base = abs(hash(inp.location)) % 30 + 10
    temp = float(base + (5 if inp.unit == "F" else 0))
    return WeatherLookupOutput(
        status="success",
        location=inp.location,
        temperature=temp,
        unit=inp.unit
    ).model_dump(mode='python')

def unit_conversion_impl(args: dict):
    inp = UnitConversionInput(**args)
    # simple deterministic conversion: just echo with *1.1 factor
    converted = inp.value * 1.1
    return UnitConversionOutput(
        status="success",
        original_value=inp.value,
        original_unit=inp.from_unit,
        converted_value=round(converted, 4),
        converted_unit=inp.to_unit
    ).model_dump(mode='python')

TOOL_REGISTRY = {
    "FlightSearch": {
        "input_model": FlightSearchInput,
        "output_model": FlightSearchOutput,
        "func": flight_search_impl,
        "description": "Search for flights"
    },
    "CalendarBooking": {
        "input_model": CalendarBookingInput,
        "output_model": CalendarBookingOutput,
        "func": calendar_booking_impl,
        "description": "Book calendar event"
    },
    "WeatherLookup": {
        "input_model": WeatherLookupInput,
        "output_model": WeatherLookupOutput,
        "func": weather_lookup_impl,
        "description": "Lookup weather"
    },
    "UnitConversion": {
        "input_model": UnitConversionInput,
        "output_model": UnitConversionOutput,
        "func": unit_conversion_impl,
        "description": "Convert units"
    }
}
