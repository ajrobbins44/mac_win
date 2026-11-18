from pathlib import Path
from sqlalchemy import select
import pytest

from database.staging_tables import collection_runs as staging_runs
from database.processed_tables import collection_runs as processed_runs
from processing.tables.collection_runs import (
    import_collection_runs,
    verify_collection_run_import,
)

@pytest.fixture
def run_values():
    """Return a fresh, valid staging run dictionary for each test."""
    # February avoids triggering the filename-specific January correction.
    return {
        "collection_run_id": 1,
        "started_at_utc": "2026-11-01T10:00:00.000Z",
        "ended_at_utc": "2026-11-01T12:00:00.000Z",
        "target_start_date": "2026-02-01",
        "target_end_date": "2026-02-28",
        "target_building_ids": "[24]",
        "scraper_version": "1.0.0",
        "schema_version": "1.0.0",
        "status": "completed",
        "status_reason": "finished",
    }

# ----------------------------------------------------------------------
# TEST_IMPORT_COPIES_VALUES_AND_RETURNS_PROCESSED_ID
# ----------------------------------------------------------------------

def test_import_copies_values_and_returns_processed_id(databases, run_values):
    """Verify field mappings and the returned source-to-processed ID map."""
    staging_engine, processed_engine = databases

    # The source connection still reads the temporary database 
    # given by the fixture in conftest.py, but the filename is 
    # used to identify the source in the processed table.
    source_path = Path("macbid_staging_02.sqlite")

    # Populate the staging table with a single row from the run_values fixture. 
    with staging_engine.begin() as source:
        source.execute(staging_runs.insert().values(**run_values))

    # Import and verify the row in one processing transaction. 
    with (
        staging_engine.connect() as source,
        processed_engine.begin() as target,
    ):
        run_id_map = import_collection_runs(source, target, source_path)
        verify_collection_run_import(source, target, source_path)

    # Read after commit to confirm the row was actually saved.
    with processed_engine.connect() as target:
        saved = target.execute(select(processed_runs)).mappings().one()

    # Confirm that the source ID maps to the newly-generated processed ID. 
    assert run_id_map == {1: saved["collection_run_id"]}

    assert saved["source_db"] == source_path.name
    assert saved["source_collection_run_id"] == 1
    assert saved["request_started_at_utc"] == run_values["started_at_utc"]
    assert saved["request_ended_at_utc"] == run_values["ended_at_utc"]
    assert saved["target_start_date"] == "2026-02-01"
    assert saved["target_end_date"] == "2026-02-28"
    assert saved["status"] == "completed"
    assert saved["status_reason"] == "finished"

# ----------------------------------------------------------------------
# TEST_REIMPORT_UPDATES_EXISTING_ROW_AND_PRESERVES_ID
# ----------------------------------------------------------------------

def test_reimport_updates_existing_row_and_preserves_id(databases, run_values):
    """Verify that an upsert refreshes values and preserves the processed ID."""
    staging_engine, processed_engine = databases
    source_path = Path("macbid_staging_02.sqlite")

    # Create another instance of run_values with a running status
    # but no ended_at_utc and status_reason to simulate a running collection run.
    run_values.update(
        ended_at_utc=None,
        status="running",
        status_reason=None,
    )

    with staging_engine.begin() as source:
        source.execute(staging_runs.insert().values(**run_values))

    # Save the initial processed ID and confirm that NULL is preserved.
    with (
        staging_engine.connect() as source,
        processed_engine.begin() as target,
    ):
        first_map = import_collection_runs(source, target, source_path)
        saved = target.execute(select(processed_runs)).mappings().one()
        assert saved["request_ended_at_utc"] is None

    # Update the staging row to have an ended_at_utc and a completed status.
    with staging_engine.begin() as source:
        source.execute(
            staging_runs.update()
            .where(staging_runs.c.collection_run_id == 1)
            .values(
                ended_at_utc="2026-11-01T12:00:00.000Z",
                status="completed",
                status_reason="finished",
            )
        )

    # Re-import the same source row to update the processed row.
    with (
        staging_engine.connect() as source,
        processed_engine.begin() as target,
    ):
        second_map = import_collection_runs(source, target, source_path)
        verify_collection_run_import(source, target, source_path)

    with processed_engine.connect() as target:
        # one() fails if the rerun created a duplicate row.
        saved = target.execute(select(processed_runs)).mappings().one()

    # Confirm that the processed ID is preserved and the values are updated.
    assert second_map == first_map
    assert saved["request_ended_at_utc"] == "2026-11-01T12:00:00.000Z"
    assert saved["status"] == "completed"
    assert saved["status_reason"] == "finished"

# ----------------------------------------------------------------------
# TEST_SAME_SOURCE_RUN_ID_FROM_DIFFERENT_FILES_GETS_SEPARATE_IDS
# ----------------------------------------------------------------------

def test_same_source_run_id_from_different_files_gets_separate_ids(databases, run_values):
    """Verify that the source filename distinguishes otherwise identical run IDs."""
    staging_engine, processed_engine = databases

    with staging_engine.begin() as source:
        source.execute(staging_runs.insert().values(**run_values))

    # Populate the staging table with a second row that has the same source run ID but a
    # different source filename to check the integrity of the composite unique constraint.
    with (
        staging_engine.connect() as source,
        processed_engine.begin() as target,
    ):
        february_map = import_collection_runs(
            source, target, Path("macbid_staging_02.sqlite")
        )
        another_map = import_collection_runs(
            source, target, Path("another_staging.sqlite")
        )

    # Confirm that the same source run ID from different files 
    # maps to different processed IDs.
    assert february_map[1] != another_map[1]

    with processed_engine.connect() as target:
        filenames = set(
            target.execute(select(processed_runs.c.source_db)).scalars()
        )

    assert filenames == {
        "macbid_staging_02.sqlite",
        "another_staging.sqlite",
    }

# ----------------------------------------------------------------------
# TEST_JANUARY_CORRECTION_PRESERVES_STAGING_VALUE
# ----------------------------------------------------------------------

def test_january_correction_preserves_staging_value(databases, run_values):
    """Verify the January end date scope correction and preservation of its source value."""
    staging_engine, processed_engine = databases

    # This filename and staging run ID 1 match MONTH_SCOPE_CORRECTIONS
    # found in processing/tables/collection_runs.py, which corrects the 
    # end date to January 31.
    source_path = Path("macbid_staging_01.sqlite")
    run_values.update(
        target_start_date="2026-01-01",
        target_end_date="2026-02-01",
    )

    with staging_engine.begin() as source:
        source.execute(staging_runs.insert().values(**run_values))

    with (
        staging_engine.connect() as source,
        processed_engine.begin() as target,
    ):
        import_collection_runs(source, target, source_path)

    # Read each database separately to compare the processed end date with 
    # the original, incorrect staging end date.
    with processed_engine.connect() as target:
        processed_end = target.execute(
            select(processed_runs.c.target_end_date)
        ).scalar_one()

    with staging_engine.connect() as source:
        staging_end = source.execute(
            select(staging_runs.c.target_end_date)
        ).scalar_one()

    assert processed_end == "2026-01-31"
    assert staging_end == "2026-02-01"

# ----------------------------------------------------------------------
# TEST_INVALID_RUN_ROLLS_BACK_EARLIER_INSERT
# ----------------------------------------------------------------------

def test_invalid_run_rolls_back_earlier_insert(databases, run_values):
    """Verify that validation failure rolls back an earlier successful insert."""
    staging_engine, processed_engine = databases
    source_path = Path("macbid_staging_02.sqlite")

    with staging_engine.begin() as source:
        source.execute(staging_runs.insert().values(**run_values))

    # The validation error should roll back the earlier insert made
    # during the same processing transaction.
    with pytest.raises(ValueError, match="ended_at_utc precedes"):
        with processed_engine.begin() as target:
            with staging_engine.connect() as source:
                import_collection_runs(source, target, source_path)

            # The staging reader has closed. Commit an invalid end time
            # to the temporary staging database before reading it again.
            with staging_engine.begin() as source:
                source.execute(
                    staging_runs.update()
                    .where(staging_runs.c.collection_run_id == 1)
                    .values(ended_at_utc="2026-11-01T09:00:00.000Z")
                )

            # Reuse the still-open processed transaction. Validation fails
            # because the end time is earlier than the 10:00 start time.
            with staging_engine.connect() as source:
                import_collection_runs(source, target, source_path)

    # A new connection confirms the earlier processed insert was rolled back.
    with processed_engine.connect() as target:
        saved_ids = target.execute(
            select(processed_runs.c.collection_run_id)
        ).scalars().all()

    assert saved_ids == []
