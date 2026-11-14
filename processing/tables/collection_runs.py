from calendar import calendar
from datetime import date

from sqlalchemy import select
from pathlib import Path

from database.processed_tables import collection_runs as processed_runs
from database.staging_tables import (
    collection_runs as staging_runs,
)
from processing.helpers.normalize import (
    parse_calendar_date, 
    parse_utc_timestamp,
)
from processing.helpers.validation import (
    verify_keys_match,
)

# (Staging filename, staging run ID) -> (intended year, intended month)
MONTH_SCOPE_CORRECTIONS = {
    ("macbid_staging_01.sqlite", 1): (2026, 1),
}

# ----------------------------------------------------------------------
# VALIDATE_COLLECTION_RUN_DATES
# ----------------------------------------------------------------------

def validate_collection_run_dates(row):

    started = parse_utc_timestamp(row["started_at_utc"], "started_at_utc")

    if row["ended_at_utc"] is not None:
        ended = parse_utc_timestamp(row["ended_at_utc"], "ended_at_utc")
        if ended < started:
            raise ValueError("ended_at_utc precedes started_at_utc")

    start_date = parse_calendar_date(row["target_start_date"], "target_start_date")
    end_date = parse_calendar_date(row["target_end_date"], "target_end_date")

    if end_date < start_date:
        raise ValueError("target_end_date precedes target_start_date")

# ----------------------------------------------------------------------
# IMPORT_COLLECTION_RUNS
# ----------------------------------------------------------------------

def import_collection_runs(source, target, database_path):

    source_db = Path(database_path).name
    run_id_map = {}

    for staging_row in source.execute(select(staging_runs)).mappings():
        row = dict(staging_row)
        source_run_id = row["collection_run_id"]

        corrected_month = MONTH_SCOPE_CORRECTIONS.get((source_db, source_run_id))

        if corrected_month is not None:
            year, month = corrected_month
            last_day = calendar.monthrange(year, month)[1]
            row["target_end_date"] = date(year, month, last_day).isoformat()

    result = target.execute(
        processed_runs.insert().values(
            source_db=source_db,
            source_collection_run_id=source_run_id,
            request_started_at_utc=row["started_at_utc"],
            request_ended_at_utc=row["ended_at_utc"],
            target_start_date=row["target_start_date"],
            target_end_date=row["target_end_date"],
            target_building_ids=row["target_building_ids"],
            status=row["status"],
            status_reason=row["status_reason"],
        )
    )
    processed_run_id = result.inserted_primary_key[0]
    run_id_map[source_run_id] = processed_run_id

    return run_id_map

# ----------------------------------------------------------------------
# VERIFY_COLLECTION_RUN_IMPORT
# ----------------------------------------------------------------------

def verify_collection_run_import(source, target, database_path):
    source_db = Path(database_path).name

    expected_ids = source.execute(
        select(staging_runs.c.collection_run_id)
    ).scalars()

    actual_ids = target.execute(
        select(processed_runs.c.source_collection_run_id)
        .where(processed_runs.c.source_db == source_db)
    ).scalars()

    verify_keys_match(
        expected_ids,
        actual_ids,
        context=f"{source_db}: collection_runs",
    )