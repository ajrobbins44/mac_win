import re

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert

from database.staging_tables import staging_auctions
from database.processed_tables import auctions as processed_auctions
from database.processed_tables import collection_runs as processed_runs

from processing.helpers.dates import (
    HENDERSON_TIMEZONE, 
    parse_utc_timestamp_fields, 
    normalize_henderson_timestamp_fields,
)
from processing.helpers.validation import (
    verify_keys_match,
    validate_positive_integers,
    validate_nonempty_text,
)

# ----------------------------------------------------------------------
# VALIDATE_PICKUP_DEADLINE
# ----------------------------------------------------------------------

def validate_pickup_deadline(
    pickup_deadline_at_local: str,
    scheduled_close_at_local: str,
) -> None:
    """Validate local offsets and the proposed three-/four-day pickup window."""
    timestamps = {}

    for field, value in (
        ("pickup_deadline_at_local", pickup_deadline_at_local),
        ("scheduled_close_at_local", scheduled_close_at_local),
    ):
        try:
             # Parse to a datetime object for date comparison.
            timestamp = datetime.fromisoformat(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid {field}: {value!r}") from exc

        if timestamp.utcoffset() is None:
            raise ValueError(f"{field} requires a UTC offset: {value!r}")

        henderson_time = timestamp.astimezone(HENDERSON_TIMEZONE)

        if timestamp.utcoffset() != henderson_time.utcoffset():
            raise ValueError(
                f"{field} requires a Henderson UTC offset: {value!r}"
            )

        timestamps[field] = timestamp

    closing = timestamps["scheduled_close_at_local"]
    deadline = timestamps["pickup_deadline_at_local"]

    # Apply the proposed calendar-day rule, counting from the day after closing.
    # Monday=0, Friday=4, Saturday=5.
    pickup_days = 4 if closing.weekday() in (4, 5) else 3
    expected_date = closing.date() + timedelta(days=pickup_days)

    if deadline.date() != expected_date:
        raise ValueError(
            f"Pickup deadline date {deadline.date()} does not match "
            f"expected date {expected_date}; "
            f"scheduled close was {scheduled_close_at_local}"
        )
    
# ----------------------------------------------------------------------
# IMPORT_AUCTIONS
# ----------------------------------------------------------------------

def import_auctions(
    source, 
    target, 
    database_path, 
    run_id_map, 
    *, 
    excluded_auction_ids,
):
    source_db = Path(database_path).name
    imported_count = 0

    stmt = (
        select(staging_auctions)
        .where(
            staging_auctions.c.auction_id.not_in(excluded_auction_ids)
        )
        .order_by(staging_auctions.c.auction_id)
    )

    for row in source.execute(stmt).mappings():
        auction_id = row["auction_id"]
        source_run_id = row["collection_run_id"]

        if source_run_id not in run_id_map:
            raise ValueError(
                f"{source_db}, auction {auction_id}: "
                f"no processed mapping for collection run {source_run_id}"
            )

        try:

            validate_nonempty_text(row, ("auction_number",))
            auction_number = row["auction_number"].strip()

            timestamps = parse_utc_timestamp_fields(
                row,
                (
                    "response_collected_at_utc",
                    "opening_date_source",
                    "closing_date_source",
                ),
            )
            response_utc = timestamps["response_collected_at_utc"]
            opened_utc = timestamps["opening_date_source"]
            closed_utc = timestamps["closing_date_source"]

            # Validate the source text timestamps before comparing their order.
            if closed_utc < opened_utc:
                raise ValueError("Scheduled close precedes scheduled opening")

            if opened_utc >= datetime.now(timezone.utc):
                raise ValueError("Scheduled opening must be before the current time")

            if closed_utc >= datetime.now(timezone.utc):
                raise ValueError("Scheduled closing must be before the current time")

            # Calls parse_utc_timestamp internally to validate the UTC timestamp
            # before reurning the adjusted timestamp in Henderson time.
            local_timestamps = normalize_henderson_timestamp_fields(
                row,
                (
                    "opening_date_source",
                    "closing_date_source",
                    "abandon_date_source",
                    "date_launched_source",
                )
            )

            opened_local = local_timestamps["opening_date_source"]
            closed_local = local_timestamps["closing_date_source"]

            pickup_deadline_local = local_timestamps["abandon_date_source"]
            launched_local = local_timestamps["date_launched_source"]

            # Keep these required identifiers available for scope and grouping.
            identifiers = validate_positive_integers(
                row,
                ("building_id", "location_id"),
            )

            auction_values = {
                "auction_number": auction_number, 
                "collection_run_id": run_id_map[source_run_id],
                "response_collected_at_utc": response_utc,
                "scheduled_open_at_local": local_timestamps["opening_date_source"],
                "scheduled_close_at_local": local_timestamps["closing_date_source"],
                "launched_at_local": local_timestamps["date_launched_source"],
                "pickup_deadline_at_local": local_timestamps["abandon_date_source"],
                "building_id": identifiers["building_id"],
                "location_id": identifiers["location_id"],
            }

        except ValueError as exc:
            raise ValueError(
                f"{source_db}, auction {auction_id}: {exc}"
            ) from exc

        # Insert a new auction or refresh the existing row with this ID.
        upsert = insert(processed_auctions).values(
            auction_id=auction_id,
            **auction_values,
        )

        upsert = upsert.on_conflict_do_update(
            index_elements=[processed_auctions.c.auction_id],
            set_=auction_values,
        )

        target.execute(upsert)
        imported_count += 1

    return imported_count

# ----------------------------------------------------------------------
# VERIFY_AUCTION_IMPORT
# ----------------------------------------------------------------------
def verify_auction_import(
    source, 
    target, 
    database_path, 
    *, 
    excluded_auction_ids
):
    source_db = Path(database_path).name

    expected_ids = source.execute(
        select(staging_auctions.c.auction_id)
        .where(
            staging_auctions.c.auction_id.not_in(excluded_auction_ids)
        )
    ).scalars()

    actual_ids = target.execute(
        select(processed_auctions.c.auction_id)
        .join(
            processed_runs,
            processed_auctions.c.collection_run_id
            == processed_runs.c.collection_run_id,
        )
        .where(processed_runs.c.source_db == source_db)
    ).scalars()


    verify_keys_match(
        expected_ids,
        actual_ids,
        context=f"{source_db}: auctions",
    )