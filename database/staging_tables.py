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

metadata = MetaData()

schema_metadata = Table(
    "schema_metadata",
    metadata,

    Column(
        "schema_name",
        Text,
        primary_key=True,
    ),
    Column(
        "schema_version",
        Text,
        nullable=False,
    ),
    Column(
        "created_at_utc",
        Text,
        nullable=False,
    ),
)

collection_runs = Table(
    "collection_runs",
    metadata,

    Column(
        "collection_run_id",
        Integer,
        primary_key=True,
        autoincrement=True,
    ),
    Column(
        "started_at_utc",
        Text,
        nullable=False,
    ),
    Column(
        "ended_at_utc",
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
        "target_building_ids",
        Text,
        nullable=False,
    ),

    Column(
        "scraper_version",
        Text,
        nullable=False,
    ),
    Column(
        "schema_version",
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

staging_auctions = Table(
    "staging_auctions",
    metadata,

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

    # Collection provenance
    #
    # These values are supplied by the pipeline rather than being
    # retrieved from AuctionRecordItem.
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
    Column("opening_date_source", Text),
    Column("closing_date_source", Text),
    Column("pickup_date_source", Text),
    Column("abandon_date_source", Text),
    Column("date_launched_source", Text),

    # Location and auction type
    Column("location_id", Integer),
    Column("building_id", Integer),
    Column("location_name", Text),
    Column("auction_type_id", Integer),

    # Auction-wide Boolean-like values
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

# --------------------------------------------------------------
# Staging Lot Summaries
# --------------------------------------------------------------

staging_lot_summaries = Table(
    "staging_lot_summaries",
    metadata,

    # Primary key supplied by MAC.BID.
    Column(
        "lot_id",
        Integer,
        primary_key=True,
    ),

    # Numeric identifier of the auction containing this lot.
    # Cross-endpoint relationships are validated during processing,
    # so this is not a staging foreign key.
    Column(
        "auction_id",
        Integer,
        nullable=False,
    ),

    # Auction-relative lot identifier used by Endpoint 3.
    Column(
        "lot_number",
        Text,
        nullable=False,
    ),

    # Collection Provenance
    #
    # Added by the pipeline rather than collected from the API.
    Column(
        "collection_run_id",
        Integer,
        ForeignKey(
            "collection_runs.collection_run_id"
        ),
        nullable=False,
    ),

    # Carried by CollectedRecordItem.
    Column(
        "response_collected_at_utc",
        Text,
        nullable=False,
    ),

    # Inventory and product identifiers
    Column(
        "inventory_id",
        Integer,
    ),
    Column(
        "product_upc",
        Text,
    ),

    # Source timestamps
    Column(
        "date_created_source",
        Text,
    ),
    Column(
        "closed_date_source",
        Text,
    ),
    Column(
        "expected_close_date_source",
        Text,
    ),

    # Location and Boolean-like source values
    Column(
        "current_location_id",
        Integer,
    ),
    Column(
        "is_transferable_source",
        Integer,
    ),
    Column(
        "is_shippable_source",
        Integer,
    ),
    Column(
        "is_partial_source",
        Integer,
    ),


    # Final auction outcomes
    Column(
        "total_bids_source",
        Integer,
    ),

    # Kept as source-oriented text until monetary conversion occurs
    # during staging-to-processed transformation.
    Column(
        "winning_bid_amount_source",
        Text,
    ),

    Column(
        "unique_bidders_source",
        Integer,
    ),

    # Product characteristics
    Column(
        "product_name",
        Text,
    ),
    Column(
        "dimensions_text",
        Text,
    ),
    Column(
        "quantity_source",
        Integer,
    ),
    Column(
        "is_pallet_source",
        Integer,
    ),

    # Shipping and package measurements
    #
    # These remain source-oriented until their units are established.
    Column(
        "shipping_height_source",
        Text,
    ),
    Column(
        "shipping_width_source",
        Text,
    ),
    Column(
        "shipping_length_source",
        Text,
    ),
    Column(
        "shipping_weight_source",
        Text,
    ),
    Column(
        "case_packed_qty_source",
        Integer,
    ),

    # Value, condition, and category
    Column(
        "retail_price_source",
        Text,
    ),
    Column(
        "condition_name",
        Text,
    ),
    Column(
        "category_name",
        Text,
    ),
)

# --------------------------------------------------------------
# Staging Lot Details
# --------------------------------------------------------------
staging_lot_details = Table(
    "staging_lot_details",
    metadata,

    # One Endpoint 3 detail observation per lot.
    Column(
        "lot_id",
        Integer,
        primary_key=True,
    ),
    Column(
        "auction_id",
        Integer,
        nullable=False,
    ),
    Column(
        "lot_number",
        Text,
        nullable=False,
    ),

    # Collection provenance
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

    # --------------------------------------------------------------
    # Fields unique to Endpoint 3
    # --------------------------------------------------------------
    
    Column(
        "product_id",
        Integer,
    ),
    Column(
        "auction_type_source",
        Text,
    ),

    Column(
        "instant_win_price_source",
        Text,
    ),
    Column(
        "buyers_assurance_cost_source",
        Text,
    ),

    Column(
        "product_model",
        Text,
    ),
    Column(
        "size_text",
        Text,
    ),
    Column(
        "box_count_source",
        Integer,
    ),

    Column(
        "is_tested_source",
        Integer,
    ),

    # Post-auction operational field retained for QA rather than
    # prediction-time modeling.
    Column(
        "lot_status_source",
        Text,
    ),

    # Full description provided in lot details listing. May result
    # in derived columns.
    Column(
        "description_source",
        Text,
        nullable=True,
    ),

    # Nullable free-text values copied from Endpoint 3 without deriving
    # processed flags during collection. Derived columns created before
    # saving to processed database.
    Column(
        "update_text_source",
        Text,
        nullable=True,
    ),
    Column(
        "partial_note_source",
        Text,
        nullable=True,
    ),
    Column(
        "tested_note_source",
        Text,
        nullable=True,
    ),
    Column(
        "damaged_note_source",
        Text,
        nullable=True,
    ),

    # Privacy-minimized image derivatives
    #
    # Image URLs and image objects are not retained.
    Column(
        "has_primary_image",
        Integer,
    ),
    Column(
        "detail_image_count",
        Integer,
    ),
    Column(
        "total_observed_image_count",
        Integer,
    ),

    # --------------------------------------------------------------
    # Fields also observed in Endpoint 2
    # --------------------------------------------------------------
    #
    # These remain separate from Endpoint 2's observations until the
    # staging-to-processed transformation compares them.

    Column(
        "inventory_id",
        Integer,
    ),
    Column(
        "product_upc",
        Text,
    ),

    Column(
        "date_created_source",
        Text,
    ),
    Column(
        "closed_date_source",
        Text,
    ),
    Column(
        "expected_close_date_source",
        Text,
    ),

    Column(
        "current_location_id",
        Integer,
    ),
    Column(
        "is_transferable_source",
        Integer,
    ),
    Column(
        "is_shippable_source",
        Integer,
    ),
    Column(
        "is_partial_source",
        Integer,
    ),

    Column(
        "total_bids_source",
        Integer,
    ),
    Column(
        "winning_bid_amount_source",
        Text,
    ),
    Column(
        "unique_bidders_source",
        Integer,
    ),

    Column(
        "product_name",
        Text,
    ),
    Column(
        "dimensions_text",
        Text,
    ),
    Column(
        "retail_price_source",
        Text,
    ),
    Column(
        "condition_name",
        Text,
    ),
    Column(
        "category_name",
        Text,
    ),
)

# --------------------------------------------------------------
# Staging Lot Bid Histories
# --------------------------------------------------------------
staging_lot_bid_histories = Table(
    "staging_lot_bid_histories",
    metadata,

    # One successful Endpoint 4 response summary per lot.
    Column(
        "lot_id",
        Integer,
        primary_key=True,
    ),

    # Collection provenance
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

    # Response-level derived information
    #
    # Number of objects observed in the response's bids[] array.
    # Zero represents a successfully collected empty array.
    Column(
        "observed_bid_record_count",
        Integer,
        nullable=False,
    ),
)

# --------------------------------------------------------------
# Staging Bid Events
# --------------------------------------------------------------
staging_bid_events = Table(
    "staging_bid_events",
    metadata,

    # Deterministic privacy-safe identifier generated because the API
    # does not provide an independent bid-event ID.
    Column(
        "bid_key",
        Text,
        primary_key=True,
    ),

    # Numeric identifier of the lot that received the bid.
    # This is validated against the other staging tables later.
    Column(
        "lot_id",
        Integer,
        nullable=False,
    ),

    # Chronological position of the bid within its lot.
    Column(
        "bid_sequence",
        Integer,
        nullable=False,
    ),

    # Collection provenance
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

    # Source bid values
    Column(
        "bid_amount_source",
        Integer,
    ),
    Column(
        "displayed_bid_source",
        Integer,
    ),
    Column(
        "bid_time_source",
        Text,
    ),

    # In the observed response, lot_end_time occurs inside every bid
    # object. Preserve every observation for later comparison.
    Column(
        "lot_end_time_source",
        Text,
    ),

    # Bid behavior
    Column(
        "is_matched_proxy",
        Integer,
    ),
    Column(
        "bid_type",
        Text,
    ),

    # Calculated transiently using anonId. The source bidder label is
    # discarded before the Item reaches persistent storage.
    Column(
        "cumulative_unique_bidder_count",
        Integer,
    ),

    # A lot cannot have two bids at the same derived chronological
    # sequence position.
    UniqueConstraint(
        "lot_id",
        "bid_sequence",
        name="uq_staging_bid_lot_sequence",
    ),
)