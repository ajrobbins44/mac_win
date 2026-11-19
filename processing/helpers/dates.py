import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

# Require UTC timestamps with exactly three millisecond digits and a trailing Z.
UTC_TIMESTAMP = r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z"

# Require calendar dates in YYYY-MM-DD format.
CALENDAR_DATE = r"[0-9]{4}-[0-9]{2}-[0-9]{2}"

# Set the timezone for Henderson, NV, which is in the Pacific Time Zone.
# Features like scheduled open and close times are based on this timezone, 
# so they must be converted from UTC to Henderson time for validation and processing.
HENDERSON_TIMEZONE = ZoneInfo("America/Los_Angeles")

# ----------------------------------------------------------------------
# PARSE_UTC_TIMESTAMP
# ----------------------------------------------------------------------

def parse_utc_timestamp(value, field):

    if not isinstance(value, str) or not re.fullmatch(UTC_TIMESTAMP, value):
        raise ValueError(f"{field}: expected YYYY-MM-DDTHH:MM:SS.sssZ, got {value!r}")
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{field}: invalid timestamp {value!r}")

# ----------------------------------------------------------------------
# PARSE_UTC_TIMESTAMP_FIELDS
# ----------------------------------------------------------------------

def parse_utc_timestamp_fields(row, fields) -> dict[str, datetime]:
    """Wrapper function to validate and parse the specified UTC timestamp fields."""
    return {
        field: parse_utc_timestamp(row[field], field)
        for field in fields
    }

# ----------------------------------------------------------------------
# PARSE_CALENDAR_DATE
# ----------------------------------------------------------------------

def parse_calendar_date(value, field):

    if not isinstance(value, str) or not re.fullmatch(CALENDAR_DATE, value):
        raise ValueError(f"{field}: expected YYYY-MM-DD, got {value!r}")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{field}: invalid date {value!r}")

# ----------------------------------------------------------------------
# PARSE_CALENDAR_DATE_FIELDS
# ----------------------------------------------------------------------

def parse_calendar_date_fields(row, fields) -> dict[str, date]:
    """Wrapper function to validate and parse the specified calendar-date fields."""
    return {
        field: parse_calendar_date(row[field], field)
        for field in fields
    }

# ----------------------------------------------------------------------
# NORMALIZE_HENDERSON_TIMESTAMP
# ----------------------------------------------------------------------

def normalize_henderson_timestamp(value: str, field: str = "timestamp") -> str:
    """
    Convert a UTC timestamp to Henderson, Nevada local time.

    Return an ISO 8601 timestamp with millisecond precision and a
    numeric UTC offset, using America/Los_Angeles daylight-saving rules.

    Example:
        2025-12-25T03:00:00.000Z -> 2025-12-24T19:00:00.000-08:00
    """
    timestamp = parse_utc_timestamp(value, field)

    if timestamp.tzinfo is None:
        raise ValueError(f"Timestamp has no time-zone offset: {value!r}")

    return timestamp.astimezone(HENDERSON_TIMEZONE).isoformat(
        timespec="milliseconds"
    )

# ----------------------------------------------------------------------
# NORMALIZE_HENDERSON_TIMESTAMP_FIELDS
# ----------------------------------------------------------------------

def normalize_henderson_timestamp_fields(row, fields) -> dict[str, str]:
    """Convert the specified UTC fields to Henderson timestamp strings."""
    return {
        field: normalize_henderson_timestamp(row[field], field)
        for field in fields
    }