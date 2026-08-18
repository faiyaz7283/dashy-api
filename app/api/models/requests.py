"""API request models.

Pydantic models for validating incoming API requests.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class WeatherQuery(BaseModel):
    """Weather API request parameters.

    Attributes:
        units: Temperature units (imperial or metric).
    """

    units: Literal["imperial", "metric"] = Field(
        default="imperial",
        description="Temperature units: imperial (Fahrenheit) or metric (Celsius)",
    )


class CalendarQuery(BaseModel):
    """Calendar API request parameters.

    Attributes:
        start_date: Start date for calendar range (ISO format).
        end_date: End date for calendar range (ISO format).
    """

    start_date: date | None = Field(
        default=None,
        description="Start date for calendar range (ISO format, e.g., 2024-01-01)",
    )
    end_date: date | None = Field(
        default=None,
        description="End date for calendar range (ISO format, e.g., 2024-12-31)",
    )

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, v: date | None, info) -> date | None:
        """Validate that end_date is after start_date if both provided."""
        if v is not None and info.data.get("start_date") is not None:
            start = info.data["start_date"]
            if v < start:
                raise ValueError("end_date must be after start_date")
        return v


class CreateFamilyMemberRequest(BaseModel):
    """Request body for creating a new family member.

    Attributes:
        key: Unique identifier (lowercase, alphanumeric + underscores).
        name: Display name.
        email: Email address (also used as Google Calendar ID).
        color: Hex color code for UI color-coding.
        initial: Single character initial for display.
        date_of_birth: Optional date of birth.
        relation: Optional relationship label (e.g. "father", "daughter").
    """

    key: str = Field(pattern=r"^[a-z0-9_]+$", min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=255)
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    initial: str = Field(min_length=1, max_length=1)
    date_of_birth: date | None = None
    relation: str | None = Field(default=None, max_length=50)


class UpdateFamilyMemberRequest(BaseModel):
    """Request body for updating an existing family member.

    All fields are optional — only provided fields are updated.

    Attributes:
        name: Display name.
        email: Email address (also used as Google Calendar ID).
        color: Hex color code for UI color-coding.
        initial: Single character initial for display.
        date_of_birth: Optional date of birth.
        relation: Optional relationship label.
    """

    name: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = Field(default=None, min_length=3, max_length=255)
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    initial: str | None = Field(default=None, min_length=1, max_length=1)
    date_of_birth: date | None = None
    relation: str | None = Field(default=None, max_length=50)
