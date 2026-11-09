from config import (
    STAGING_DATABASE_PATHS,
)

STAGING_DATABASES = {
    "month_01": STAGING_DATABASE_PATHS[1],
    "month_02": STAGING_DATABASE_PATHS[2],
    "month_03": STAGING_DATABASE_PATHS[3],
}

TABLES_TO_AUDIT = (
    "staging_auctions",
    "staging_lot_summaries",
    "staging_lot_details",
    "staging_lot_bid_histories",
    "staging_bid_events",
)

# Fields shared by staging_lot_summaries and staging_lot_details.
# Excludes lot_id because it is the join key, not a comparison field.
SHARED_LOT_FIELDS = (
    "auction_id",
    "lot_number",
    "inventory_id",
    "product_upc",
    "date_created_source",
    "closed_date_source",
    "expected_close_date_source",
    "current_location_id",
    "is_transferable_source",
    "is_shippable_source",
    "is_partial_source",
    "total_bids_source",
    "winning_bid_amount_source",
    "unique_bidders_source",
    "product_name",
    "dimensions_text",
    "retail_price_source",
    "condition_name",
    "category_name",
)