from pathlib import Path

import pytest
from sqlalchemy import select

from database.processed_tables import auctions as processed_auctions
from database.staging_tables import (
    collection_runs as staging_runs,
    staging_auctions,
)
from processing.tables.auctions import (
    import_auctions,
    verify_auction_import,
)
from processing.tables.collection_runs import import_collection_runs


SOURCE_PATH = Path("macbid_staging_02.sqlite")


@pytest.fixture
def auction_values():
    """Return a fresh auction with historical, valid source timestamps."""
    return {
        "auction_id": 100,
        "auction_number": "HEA2602-01-A1",
        "collection_run_id": 1,
        "response_collected_at_utc": "2026-10-29T22:24:20.553Z",
        "opening_date_source": "2026-01-25T03:00:00.000Z",
        "closing_date_source": "2026-02-01T22:00:00.000Z",
        "date_launched_source": "2026-01-25T21:35:54.000Z",
        "pickup_date_source": "Wednesday (02/04)",
        "abandon_date_source": "2026-02-04T00:00:00.000Z",
        "building_id": 24,
        "location_id": 54,
        "location_name": "Henderson - A",
    }


@pytest.fixture
def prepared_databases(databases):
    """Populate the source run and obtain its processed ID mapping."""
    staging_engine, processed_engine = databases

    with staging_engine.begin() as source:
        source.execute(
            staging_runs.insert().values(
                collection_run_id=1,
                started_at_utc="2026-10-29T22:24:19.399Z",
                ended_at_utc="2026-10-31T13:35:49.913Z",
                target_start_date="2026-02-01",
                target_end_date="2026-02-28",
                target_building_ids="[24]",
                scraper_version="1.0.0",
                schema_version="1.0.0",
                status="completed",
                status_reason="finished",
            )
        )

    with (
        staging_engine.connect() as source,
        processed_engine.begin() as target,
    ):
        run_id_map = import_collection_runs(source, target, SOURCE_PATH)

    return staging_engine, processed_engine, run_id_map


def test_import_maps_fields_and_converts_timestamps(
    prepared_databases,
    auction_values,
):
    """Check the stored values, including local date rollover and provenance."""
    staging_engine, processed_engine, run_id_map = prepared_databases

    with staging_engine.begin() as source:
        source.execute(staging_auctions.insert().values(**auction_values))

    with (
        staging_engine.connect() as source,
        processed_engine.begin() as target,
    ):
        count = import_auctions(
            source,
            target,
            SOURCE_PATH,
            run_id_map,
            excluded_auction_ids=set(),
        )
        verify_auction_import(
            source,
            target,
            SOURCE_PATH,
            excluded_auction_ids=set(),
        )

    with processed_engine.connect() as target:
        saved = target.execute(
            select(processed_auctions)
        ).mappings().one()

    assert count == 1
    assert saved["auction_id"] == 100
    assert saved["auction_number"] == "HEA2602-01-A1"
    assert saved["collection_run_id"] == run_id_map[1]
    assert saved["response_collected_at_utc"] == (
        auction_values["response_collected_at_utc"]
    )

    # UTC-to-Henderson conversion moves the opening to the previous day.
    assert saved["scheduled_open_at_local"] == (
        "2026-01-24T19:00:00.000-08:00"
    )
    assert saved["scheduled_close_at_local"] == (
        "2026-02-01T14:00:00.000-08:00"
    )
    assert saved["launched_at_local"] == (
        "2026-01-25T13:35:54.000-08:00"
    )

    # Preserve the converted source deadline without imposing a pickup window.
    assert saved["pickup_deadline_at_local"] == (
        "2026-02-03T16:00:00.000-08:00"
    )
    assert saved["building_id"] == 24
    assert saved["location_id"] == 54

    # Reading again confirms processing left the source value intact.
    with staging_engine.connect() as source:
        source_deadline = source.execute(
            select(staging_auctions.c.abandon_date_source)
        ).scalar_one()

    assert source_deadline == auction_values["abandon_date_source"]


def test_excluded_auction_is_not_imported(
    prepared_databases,
    auction_values,
):
    """Import only the eligible auction and verify the filtered coverage."""
    staging_engine, processed_engine, run_id_map = prepared_databases

    excluded = {
        **auction_values,
        "auction_id": 101,
        "auction_number": "HEA2602-02-A1",
    }

    with staging_engine.begin() as source:
        source.execute(
            staging_auctions.insert(),
            [auction_values, excluded],
        )

    with (
        staging_engine.connect() as source,
        processed_engine.begin() as target,
    ):
        count = import_auctions(
            source,
            target,
            SOURCE_PATH,
            run_id_map,
            excluded_auction_ids={101},
        )
        verify_auction_import(
            source,
            target,
            SOURCE_PATH,
            excluded_auction_ids={101},
        )

    with processed_engine.connect() as target:
        saved_ids = target.execute(
            select(processed_auctions.c.auction_id)
        ).scalars().all()

    assert count == 1
    assert saved_ids == [100]


def test_reimport_updates_existing_auction(
    prepared_databases,
    auction_values,
):
    """Refresh an existing auction without inserting another row."""
    staging_engine, processed_engine, run_id_map = prepared_databases

    with staging_engine.begin() as source:
        source.execute(staging_auctions.insert().values(**auction_values))

    with (
        staging_engine.connect() as source,
        processed_engine.begin() as target,
    ):
        import_auctions(
            source,
            target,
            SOURCE_PATH,
            run_id_map,
            excluded_auction_ids=set(),
        )

    with staging_engine.begin() as source:
        source.execute(
            staging_auctions.update()
            .where(staging_auctions.c.auction_id == 100)
            .values(location_id=80, location_name="Henderson - B")
        )

    with (
        staging_engine.connect() as source,
        processed_engine.begin() as target,
    ):
        import_auctions(
            source,
            target,
            SOURCE_PATH,
            run_id_map,
            excluded_auction_ids=set(),
        )

    with processed_engine.connect() as target:
        # one() also catches accidental duplicate inserts.
        saved = target.execute(
            select(processed_auctions)
        ).mappings().one()

    assert saved["auction_id"] == 100
    assert saved["location_id"] == 80
    assert saved["collection_run_id"] == run_id_map[1]


@pytest.mark.parametrize(
    "field, invalid_value",
    [
        ("auction_number", "   "),
        ("building_id", 0),
        ("location_id", -1),
        ("opening_date_source", "invalid timestamp"),
        ("closing_date_source", "2026-01-01T22:00:00.000Z"),
        ("opening_date_source", "2099-01-01T03:00:00.000Z"),
        ("closing_date_source", "2099-02-01T22:00:00.000Z"),
    ],
)
def test_invalid_auction_prevents_import(
    prepared_databases,
    auction_values,
    field,
    invalid_value,
):
    """Reject invalid input and leave the processed auction table empty."""
    staging_engine, processed_engine, run_id_map = prepared_databases
    auction_values[field] = invalid_value

    with staging_engine.begin() as source:
        source.execute(staging_auctions.insert().values(**auction_values))

    with pytest.raises(ValueError):
        with (
            staging_engine.connect() as source,
            processed_engine.begin() as target,
        ):
            import_auctions(
                source,
                target,
                SOURCE_PATH,
                run_id_map,
                excluded_auction_ids=set(),
            )

    with processed_engine.connect() as target:
        saved_ids = target.execute(
            select(processed_auctions.c.auction_id)
        ).scalars().all()

    assert saved_ids == []


def test_missing_run_mapping_prevents_import(
    prepared_databases,
    auction_values,
):
    """Reject an auction when its staging run has no processed ID mapping."""
    staging_engine, processed_engine, _ = prepared_databases

    with staging_engine.begin() as source:
        source.execute(staging_auctions.insert().values(**auction_values))

    with pytest.raises(ValueError, match="no processed mapping"):
        with (
            staging_engine.connect() as source,
            processed_engine.begin() as target,
        ):
            import_auctions(
                source,
                target,
                SOURCE_PATH,
                {},
                excluded_auction_ids=set(),
            )


def test_verification_detects_missing_auction(
    prepared_databases,
    auction_values,
):
    """Detect a source auction that has not reached processed."""
    staging_engine, processed_engine, _ = prepared_databases

    with staging_engine.begin() as source:
        source.execute(staging_auctions.insert().values(**auction_values))

    with pytest.raises(ValueError, match="1 missing"):
        with (
            staging_engine.connect() as source,
            processed_engine.begin() as target,
        ):
            verify_auction_import(
                source,
                target,
                SOURCE_PATH,
                excluded_auction_ids=set(),
            )