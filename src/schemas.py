from datetime import datetime, date
from enum import Enum
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Literal

class FlightSearchInput(BaseModel):
    model_config = ConfigDict(extra='forbid')

    origin: str = Field(min_length=1)
    destination: str = Field(min_length=1)
    date: date

    @field_validator('origin', 'destination')
    @classmethod
    def non_empty_str(cls, v):
        if not isinstance(v, str) or not v.strip():
            raise ValueError('must be non-empty string')
        return v.strip()

    @field_validator('date', mode='before')
    @classmethod
    def strict_iso_date(cls, v):
        # Accept only YYYY-MM-DD string or date object
        import re
        if isinstance(v, date):
            return v
        if isinstance(v, str):
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', v):
                raise ValueError('date must be ISO YYYY-MM-DD')
            return v
        raise ValueError('date must be ISO YYYY-MM-DD')

class FlightSearchOutput(BaseModel):
    model_config = ConfigDict(extra='forbid')

    status: Literal["success"]
    flight_id: str
    origin: str
    destination: str
    date: date

class CalendarBookingInput(BaseModel):
    model_config = ConfigDict(extra='forbid')

    event_title: str = Field(min_length=1)
    start_time: datetime
    duration_minutes: int = Field(gt=0)

    @field_validator('event_title')
    @classmethod
    def non_empty(cls, v):
        if not isinstance(v, str) or not v.strip():
            raise ValueError('must be non-empty')
        return v.strip()

    @field_validator('duration_minutes', mode='before')
    @classmethod
    def reject_bool_duration(cls, v):
        if isinstance(v, bool):
            raise ValueError('duration_minutes must be integer, not bool')
        return v

class CalendarBookingOutput(BaseModel):
    model_config = ConfigDict(extra='forbid')

    status: Literal["success"]
    booking_id: str
    event_title: str
    start_time: datetime
    duration_minutes: int

class UnitEnum(str, Enum):
    C = "C"
    F = "F"

class WeatherLookupInput(BaseModel):
    model_config = ConfigDict(extra='forbid')

    location: str = Field(min_length=1)
    unit: UnitEnum

    @field_validator('location')
    @classmethod
    def non_empty(cls, v):
        if not isinstance(v, str) or not v.strip():
            raise ValueError('must be non-empty')
        return v.strip()

class WeatherLookupOutput(BaseModel):
    model_config = ConfigDict(extra='forbid')

    status: Literal["success"]
    location: str
    temperature: float
    unit: UnitEnum

    @field_validator('temperature')
    @classmethod
    def finite(cls, v):
        import math
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v):
            raise ValueError('temperature must be finite number')
        return float(v)

class UnitConversionInput(BaseModel):
    model_config = ConfigDict(extra='forbid')

    value: float
    from_unit: str = Field(min_length=1)
    to_unit: str = Field(min_length=1)

    @field_validator('value', mode='before')
    @classmethod
    def finite_value(cls, v):
        import math
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError('value must be finite number')
        if not math.isfinite(v):
            raise ValueError('value must be finite number')
        return float(v)

    @field_validator('from_unit', 'to_unit')
    @classmethod
    def non_empty_unit(cls, v):
        if not isinstance(v, str) or not v.strip():
            raise ValueError('unit must be non-empty string')
        return v.strip()

class UnitConversionOutput(BaseModel):
    model_config = ConfigDict(extra='forbid')

    status: Literal["success"]
    original_value: float
    original_unit: str
    converted_value: float
    converted_unit: str

    @field_validator('original_value', 'converted_value')
    @classmethod
    def finite_vals(cls, v):
        import math
        if isinstance(v, bool) or not math.isfinite(v):
            raise ValueError('must be finite')
        return float(v)

# Standardized envelopes
class SuccessEnvelope(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: Literal["success"]
    data: dict

class FailureEnvelope(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: Literal["error"]
    reason: str
