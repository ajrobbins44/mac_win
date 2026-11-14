from pathlib import Path

from sqlalchemy import(
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint
)

from config import (
    STAGING_DATABASE_PATHS,
)

from processing.constants import (
    TABLES_TO_AUDIT,
    SHARED_LOT_FIELDS,
)

processed_metadata = MetaData()

collection_runs = Table(
    "collection_runs",
    processed_metadata,

    Column(
        "collection_run_id",
        Integer,
        primary_key=True,
        autoincrement=True,
    ),
    Column(
        "source_db",
        Text,
        nullable=False,
    ),
    Column(
        "source_collection_run_id",
        Integer,
        nullable=False,
    ),
    UniqueConstraint(
        "source_db",
        "source_collection_run_id",
        name="uq_collection_runs_source",
    ),
    Column(
        "request_started_at_utc",
        Text,
        nullable=False,
    ),
    Column(
        "request_ended_at_utc",
        Text,
    ),

    Column(
        "target_start_date",
        Text,
        nullable=False,
    ),
    Column(
        "target_end_date",
        Text,
        nullable=False,
    ),

    Column(
        "status",
        Text,
        nullable=False,
    ),
    Column(
        "status_reason",
        Text,
    ),
)

# ----------------------------------------------------------------------
# Auction records
# ----------------------------------------------------------------------

auctions = Table(
    "auctions",
    processed_metadata,

    # Primary and alternate identifiers
    Column(
        "auction_id",
        Integer,
        primary_key=True,
    ),
    Column(
        "auction_number",
        Text,
        nullable=False,
        unique=True,
    ),

    # Provenance columns
    Column(
        "collection_run_id",
        Integer,
        ForeignKey(
            "collection_runs.collection_run_id"
        ),
        nullable=False,
    ),
    Column(
        "response_collected_at_utc",
        Text,
        nullable=False,
    ),

    # Auction dates
    Column(
        "scheduled_open_date",
        Text,
        nullable=False,
    ),
    Column(
        "launched_at_utc",
        Text,
        nullable=False,
    ),
    Column(
        "scheduled_close_date",
        Text,
        nullable=False,
    ),
    Column(
        "pickup_date",
        Text,
        nullable=False,
    ),
    Column(
        "scheduled_abandon_date",
        Text,
        nullable=False,
    ),

    # Building and location values
    Column("building_id", Integer, nullable=False),
    Column("location_id", Integer, nullable=False),
    Column("location_name", Text),
    
    # Auction-wide Boolean-like values
    Column("auction_type_id", Integer),
    Column("allow_transfers_source", Integer),
    Column("free_transfers_source", Integer),
    Column("online_only_source", Integer),
    Column("members_only_source", Integer),
    Column("non_taxable_source", Integer),
    Column("immediate_settle_source", Integer),

    # Auction-wide timing rules
    Column("stagger_close_seconds", Integer),
    Column("extension_window_seconds", Integer),
    Column("time_extension_seconds", Integer),

    # Auction-wide fee overrides and lot totals
    #
    # Unknown fields remain TEXT in staging until their source
    # meanings are established.
    Column("lot_fee_override_source", Text),
    Column("buyers_premium_override_source", Text),
    Column("total_lots_source", Integer),
)
