import re
from datetime import date, datetime

# Require UTC timestamps with exactly three millisecond digits and a trailing Z.
UTC_TIMESTAMP = r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z"

# Require calendar dates in YYYY-MM-DD format.
CALENDAR_DATE = r"[0-9]{4}-[0-9]{2}-[0-9]{2}"

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
# PARSE_CALENDAR_DATE
# ----------------------------------------------------------------------

def parse_calendar_date(value, field):

    if not isinstance(value, str) or not re.fullmatch(CALENDAR_DATE, value):
        raise ValueError(f"{field}: expected YYYY-MM-DD, got {value!r}")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{field}: invalid date {value!r}")
