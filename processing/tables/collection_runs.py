from calendar import monthrange
from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from pathlib import Path

from database.processed_tables import collection_runs as processed_runs
from database.staging_tables import (
    collection_runs as staging_runs,
)
from processing.helpers.dates import (
    parse_calendar_date_fields, 
    parse_utc_timestamp_fields,
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

    timestamps = parse_utc_timestamp_fields(
        row,
        (
            "started_at_utc",
            "ended_at_utc",
        )
    )
    started = timestamps["started_at_utc"]
    ended = timestamps["ended_at_utc"]

    if ended <= started:
        raise ValueError("started_at_utc doesn't precede ended_at_utc")

    dates = parse_calendar_date_fields(
        row,
        (
            "target_start_date",
            "target_end_date",
        )
    )
    start_date = dates["target_start_date"]
    end_date = dates["target_end_date"]

    if end_date <= start_date:
        raise ValueError("target_start_date doesn't precede target_end_date")

# ----------------------------------------------------------------------
# IMPORT_COLLECTION_RUNS
# ----------------------------------------------------------------------

def import_collection_runs(source, target, database_path):

    source_db = Path(database_path).name

    # Lookup table for mapping source collection_run_id 
    # to processed collection_run_id.
    run_id_map = {}

    for staging_row in source.execute(select(staging_runs)).mappings():

        # Convert the RowMapping to a dict in order to modify it.
        row = dict(staging_row)
        source_run_id = row["collection_run_id"]

        corrected_month = MONTH_SCOPE_CORRECTIONS.get((source_db, source_run_id))

        if corrected_month is not None:
            year, month = corrected_month

            # Use [1] to get the last day of the month, since monthrange returns 
            # a tuple (weekday of first day of the month, number of days in month)
            last_day = monthrange(year, month)[1]
            row["target_end_date"] = date(year, month, last_day).isoformat()

        # Validate the dates before inserting into the processed database.
        validate_collection_run_dates(row)

        run_values = {
            "request_started_at_utc": row["started_at_utc"],
            "request_ended_at_utc": row["ended_at_utc"],
            "target_start_date": row["target_start_date"],
            "target_end_date": row["target_end_date"],
            "status": row["status"],
            "status_reason": row["status_reason"],
        }

        # Inserts into the processed collection_runs table, using its
        # processed_runs alias to avoid confusion with the staging_runs table.
        stmt = insert(processed_runs).values(
            source_db=source_db,
            source_collection_run_id=source_run_id,
            **run_values
        )

        # Conflict resolution: if a row with the same source_db and 
        # source_collection_run_id exists, update it with the new values.
        stmt = stmt.on_conflict_do_update(
            # Identify the composite unique contstraints
            index_elements=[
                processed_runs.c.source_db,
                processed_runs.c.source_collection_run_id,
            ],
            # Update the existing row with the new values from run_values
            set_=run_values,
        ).returning(processed_runs.c.collection_run_id)

        processed_run_id = target.execute(stmt).scalar_one()
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