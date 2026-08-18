"""Calendar domain value objects.

Immutable value objects representing calendar data concepts.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Literal


class EventStatus(Enum):
    """Calendar event status."""

    CONFIRMED = "confirmed"
    TENTATIVE = "tentative"
    CANCELLED = "cancelled"


class ResponseStatus(Enum):
    """Attendee response status."""

    ACCEPTED = "accepted"
    DECLINED = "declined"
    TENTATIVE = "tentative"
    NEEDS_ACTION = "needsAction"


@dataclass(frozen=True)
class DateRange:
    """Date range for calendar queries.

    Attributes:
        start: Start datetime (inclusive).
        end: End datetime (inclusive).
    """

    start: datetime
    end: datetime

    def overlaps(self, other: "DateRange") -> bool:
        """Check if this range overlaps with another.

        Args:
            other: Another DateRange to check.

        Returns:
            True if ranges overlap, False otherwise.
        """
        return self.start <= other.end and other.start <= self.end

    def contains(self, dt: datetime) -> bool:
        """Check if datetime falls within this range.

        Args:
            dt: Datetime to check.

        Returns:
            True if datetime is within range, False otherwise.
        """
        return self.start <= dt <= self.end


@dataclass(frozen=True)
class RecurrenceRule:
    """Recurrence rule for repeating events.

    Attributes:
        frequency: Recurrence frequency (DAILY, WEEKLY, MONTHLY, YEARLY).
        interval: Interval between recurrences (e.g., every 2 weeks).
        by_day: Specific days of week (MO, TU, WE, TH, FR, SA, SU).
        count: Number of occurrences (mutually exclusive with until).
        until: End date for recurrence (mutually exclusive with count).
    """

    frequency: Literal["DAILY", "WEEKLY", "MONTHLY", "YEARLY"]
    interval: int = 1
    by_day: tuple[str, ...] = ()
    count: int | None = None
    until: datetime | None = None

    @classmethod
    def from_rrule_string(cls, rrule: str) -> "RecurrenceRule":
        """Parse RRULE string into RecurrenceRule.

        Args:
            rrule: RRULE string (e.g., "RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR").

        Returns:
            RecurrenceRule instance.
        """
        # Remove "RRULE:" prefix if present
        if rrule.startswith("RRULE:"):
            rrule = rrule[6:]

        parts = rrule.split(";")
        freq = "WEEKLY"
        interval = 1
        by_day = []
        count = None
        until = None

        for part in parts:
            key, value = part.split("=")
            if key == "FREQ":
                freq = value
            elif key == "INTERVAL":
                interval = int(value)
            elif key == "BYDAY":
                by_day = value.split(",")
            elif key == "COUNT":
                count = int(value)
            elif key == "UNTIL":
                # Parse date/datetime string
                if "T" in value:
                    until = datetime.fromisoformat(value.replace("Z", "+00:00"))
                else:
                    until = datetime.strptime(value, "%Y%m%d")

        return cls(
            frequency=freq,  # type: ignore
            interval=interval,
            by_day=tuple(by_day),
            count=count,
            until=until,
        )

    def to_rrule_string(self) -> str:
        """Convert to RRULE string format.

        Returns:
            RRULE string (e.g., "RRULE:FREQ=WEEKLY;BYDAY=MO,WE").
        """
        parts = [f"FREQ={self.frequency}"]

        if self.interval != 1:
            parts.append(f"INTERVAL={self.interval}")

        if self.by_day:
            parts.append(f"BYDAY={','.join(self.by_day)}")

        if self.count is not None:
            parts.append(f"COUNT={self.count}")
        elif self.until is not None:
            until_str = self.until.strftime("%Y%m%dT%H%M%SZ")
            parts.append(f"UNTIL={until_str}")

        return "RRULE:" + ";".join(parts)
