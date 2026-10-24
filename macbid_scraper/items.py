# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

from dataclasses import dataclass
from scrapy.item import Item, Field

class CollectedRecordItem(Item):
    """API-derived record carrying response-level provenance.

    The collection run identifier is not stored in this Item. SQLite
    generates collection_run_id when the run begins, and the database
    pipeline adds that value when persisting the record.

    response_collected_at_utc records when the API response used to
    construct this Item was observed.
    """

    response_collected_at_utc = Field()


class AuctionRecordItem(CollectedRecordItem):
    """Auction-level fields collected from Endpoint 1.
    
    Endpoint:
        GET /auctions/{auction_number}?getItems=0

    One AuctionRecordItem is yielded for each successfully verified
    auction number. Endpoint 1 establishes the relationship between the
    human-readable auction_number and MAC.BID's numeric auction_id.

    The resulting record contains auction-wide dates, location
    identifiers, participation rules, and closing-time configuration.
    These values apply to the auction as a whole rather than to an
    individual lot.

    Endpoint 2 repeats much of this auction metadata. Those repeated
    values should be used for source validation rather than stored as a
    second auction record.

    Source fields ending in "_source" preserve values in the form needed
    by the staging pipeline. Dates, monetary values, and Boolean flags
    must be validated and normalized before insertion into the processed
    database.
    """


    # ------------------------------------------------------------------
    # Auction identifiers
    # ------------------------------------------------------------------

    # Primary key of the staging and processed auctions tables.
    # MAC.BID's numeric auction identifier.
    auction_id = Field()
    # Alphanumeric identifier used by Endpoint 1 and Endpoint 3.
    auction_number = Field()

    # ------------------------------------------------------------------
    # Auction dates
    # ------------------------------------------------------------------

    # Although returned in timestamp-shaped values, these fields are
    # treated as calendar dates for this project after validation.
    opening_date_source = Field()
    closing_date_source = Field()
    abandon_date_source = Field()

    # Human-readable pickup-date label, such as "Wednesday (02/04)".
    # This is not necessarily an ISO 8601 timestamp.
    pickup_date_source = Field()

    # Precise timestamp indicating when the auction became available.
    date_launched_source = Field()

    # ------------------------------------------------------------------
    # Auction location and type
    # ------------------------------------------------------------------

    # Identifier for the auction group, such as Henderson-A.
    location_id = Field()

    # Identifier for the physical warehouse, such as Henderson.
    building_id = Field()

    # Source label for the auction location, such as "Henderson - A".
    location_name = Field()

    # Numeric classification of the auction format.
    # Significance not yet determined.
    auction_type_id = Field()

    # ------------------------------------------------------------------
    # Auction-wide rules
    # ------------------------------------------------------------------

    # Boolean-like source flags. The pipeline must validate that each
    # value is 0, 1, or NULL before writing it to SQLite.
    allow_transfers_source = Field()
    free_transfers_source = Field()
    online_only_source = Field()
    members_only_source = Field()
    non_taxable_source = Field()
    immediate_settle_source = Field()

    # ------------------------------------------------------------------
    # Auction-wide closing configuration
    # ------------------------------------------------------------------

    # Timing rules measured in seconds.
    stagger_close_seconds = Field()
    extension_window_seconds = Field()
    time_extension_seconds = Field()

    # ------------------------------------------------------------------
    # Auction-wide fee overrides and lot totals
    # ------------------------------------------------------------------

    # Significance not yet determined.
    lot_fee_override_source = Field()
    buyers_premium_override_source = Field()

    # Source-reported lot total. It may be NULL and should be compared
    # with the number of lots actually collected through pagination.
    total_lots_source = Field()

class LotSummaryItem(CollectedRecordItem):
    """Fields collected from Endpoint 2's items[] array. 

    Endpoint:
        GET /auctions/{auction_id}?pg=…&ppg=…
    
    One LotSummaryItem is yielded for each object in the items[] array.
    Its fields are stored without cross-endpoint reconciliation in
    staging_lot_summaries.

    Endpoint 3 may provide some of the same fields. Those observations
    are stored separately in staging_lot_details and compared only during
    the later staging-to-processed transformation.

    Final-outcome fields are retained for outcomes and historical
    analysis, but they must not be used as prediction-time features for
    checkpoints occurring before the auction closes.
    """

    # ------------------------------------------------------------------
    # Lot identifiers
    # ------------------------------------------------------------------

    # Primary key of the integrated staging_auction_items table.
    lot_id = Field()

    # Foreign key to staging_auctions.auction_id.
    auction_id = Field()

    # Auction-relative identifier used by Endpoint 3.
    # The database should enforce uniqueness on:
    #     (auction_id, lot_number)
    lot_number = Field()

    # ------------------------------------------------------------------
    # Inventory and product identifiers
    # ------------------------------------------------------------------

    # Identifier for the underlying physical inventory record.
    # It may help identify an unsold physical item that was relisted,
    # but should not automatically be treated as a reusable product ID.
    inventory_id = Field()

    # Product barcode or identifier. Store as text because it may contain
    # letters, leading zeros, or other nonnumeric characters.
    product_upc = Field()

    # ------------------------------------------------------------------
    # Lot timestamps
    # ------------------------------------------------------------------

    # Source timestamps require validation and normalization before being
    # written to the processed database.
    date_created_source = Field()

    # The apparent timezone of this field must be normalized using the
    # project's established closing-time rules.
    closed_date_source = Field()

    # Expected close may differ from actual close because of extensions.
    expected_close_date_source = Field()

    # ------------------------------------------------------------------
    # Lot location and availability
    # ------------------------------------------------------------------

    # Lot-level current location. This may differ from the auction's
    # originating location after a transfer.
    current_location_id = Field()

    # Lot-specific Boolean-like source flags.
    is_transferable_source = Field()
    is_shippable_source = Field()
    is_partial_source = Field()

    # ------------------------------------------------------------------
    # Final auction outcomes
    # ------------------------------------------------------------------

    # Post-close outcomes. These can be response variables or descriptive
    # measures, but using them at earlier prediction checkpoints would
    # cause target leakage. 
    total_bids_source = Field()
    unique_bidders_source = Field()

    # Integer dollars
    winning_bid_amount_source = Field()

    # ------------------------------------------------------------------
    # Product characteristics
    # ------------------------------------------------------------------

    product_name = Field()
    dimensions_text = Field()
    quantity_source = Field()
    is_pallet_source = Field()

    # ------------------------------------------------------------------
    # Shipping and package measurements
    # ------------------------------------------------------------------

    # Endpoint-2-specific measurements. Their units and meaning must be
    # validated before they are added to the processed database.
    shipping_height_source = Field()
    shipping_width_source = Field()
    shipping_length_source = Field()
    shipping_weight_source = Field()
    case_packed_qty_source = Field()

    # ------------------------------------------------------------------
    # Product value, condition, and category
    # ------------------------------------------------------------------

    # Convert to integer cents before processed storage
    retail_price_source = Field()

    condition_name = Field()
    category_name = Field()

class LotDetailItem(CollectedRecordItem):
    """Lot fields collected from Endpoint 3. 

    Endpoint:
        GET /auction/{auction_number}/lot/{lot_number}

    One LotDetailItem is yielded for each successfully collected
    lot-detail response. Its fields are stored in staging_lot_details.

    Fields also observed in Endpoint 2 remain in this source-aligned
    staging table. They are not compared, discarded, or used to overwrite
    Endpoint 2 values during initial collection.
    """

    # ------------------------------------------------------------------
    # Record-matching identifiers
    # ------------------------------------------------------------------

    # Primary key of the integrated staging_auction_items table.
    # This identifies the existing row that Endpoint 3 will enrich.
    lot_id = Field()

    # Foreign key to staging_auctions.auction_id.
    # Compare with the auction_id previously returned by Endpoint 2.
    auction_id = Field()

    # Auction-relative lot identifier used in the Endpoint 3 URL.
    # Together with auction_id, this should identify one lot.
    lot_number = Field()

    # ------------------------------------------------------------------
    # Fields unique to Endpoint 3
    # ------------------------------------------------------------------

    # Potential catalog-level product identifier.
    product_id = Field()

    # Human-readable auction type, such as "standard".
    # Investigate its relationship to the auction-level auction_type_id.
    auction_type_source = Field()

    # Monetary source values. Remains integer dollars before insertion
    # into the processed database.
    instant_win_price_source = Field()
    buyers_assurance_cost_source = Field()

    # Additional product characteristics unavailable in Endpoint 2.
    product_model = Field()
    size_text = Field()
    box_count_source = Field()

    # Structured testing indicator.
    is_tested_source = Field()

    # Post-auction status (i.e., 'PICKED UP'). Useful for QA, 
    # but it should not be used as a feature.
    lot_status_source = Field()

    # Derived from free-text fields before those fields are discarded.
    has_update = Field()
    has_partial_note = Field()
    has_tested_note = Field()
    has_damage_note = Field()

    # Derived from image metadata. The URLs and image objects themselves
    # are discarded after these values are calculated.
    has_primary_image = Field()
    detail_image_count = Field()
    total_observed_image_count = Field()
    
    # ------------------------------------------------------------------
    # Fields shared with Endpoint 2
    # ------------------------------------------------------------------
    # These values are used to validate Endpoint 2 data. They should not
    # create a second set of columns in staging_auction_items.

    product_name = Field()
    product_upc = Field()
    category_name = Field()
    condition_name = Field()
    dimensions_text = Field()
    retail_price_source = Field()

    inventory_id = Field()
    date_created_source = Field()
    closed_date_source = Field()
    expected_close_date_source = Field()
    current_location_id = Field()

    is_transferable_source = Field()
    is_shippable_source = Field()
    is_partial_source = Field()

    total_bids_source = Field()
    winning_bid_amount_source = Field()
    unique_bidders_source = Field()

class LotBidHistoryItem(CollectedRecordItem):
    """Lot-level summary derived from an Endpoint 4 response.

    Endpoint:
        GET /auctions/lot/{lot_id}/bid-history

    Exactly one LotBidHistoryItem is produced for each successfully
    collected lot, including a valid response with an empty bids[] array.
    Its fields are stored in staging_lot_bid_histories. 
    """
    # Primary key of the bid-history summary table and foreign key to
    # staging_auction_items.lot_id.
    lot_id = Field()

    # Number of bid objects observed in the response's bids[] array.
    # Compare with total_bids_source from the lot record.
    observed_bid_record_count = Field()

class SingleBidItem(CollectedRecordItem):
    """One privacy-minimized bid event collected from Endpoint 4.

    Endpoint:
        GET /auctions/lot/{lot_id}/bid-history

    One SingleBidItem is yielded for each object in the response's
    bids[] array. Its fields are stored in staging_bid_events. 

    The API does not appear to provide an independent numeric bid-event
    identifier. The pipeline must therefore generate a deterministic
    bid_key from approved, nonidentifying event fields.

    The source fields anonId, isCurrentUser, and isCurrentWinner are not
    retained. anonId may be used transiently while processing one
    response to calculate cumulative_unique_bidder_count, but it must be
    discarded before persistence.

    Bid sequence and cumulative state must be calculated in chronological
    order so that each record represents the auction state immediately
    after that bid.
    """

    # ------------------------------------------------------------------
    # Bid and parent identifiers
    # ------------------------------------------------------------------

    # Deterministic primary key generated by the collection pipeline.
    bid_key = Field()

    # Foreign key to staging_auction_items.lot_id.
    lot_id = Field()

    # Derived chronological position of the bid within its lot.
    # Define whether counting begins at 1 and apply that rule consistently.
    bid_sequence = Field()

    # ------------------------------------------------------------------
    # Bid amount and timing
    # ------------------------------------------------------------------

    # Monetary source values retained as integer dollars.
    bid_amount_source = Field()
    displayed_bid_source = Field()

    # Timestamps at which the bid was placed and the lot bidding ends.
    bid_time_source = Field()
    lot_end_time_source = Field()

    # ------------------------------------------------------------------
    # Bid behavior
    # ------------------------------------------------------------------

    # Boolean indicating whether the bid matched a proxy bid.
    is_matched_proxy = Field()

    # Source bid classification, such as "manual".
    bid_type = Field()

    # Derived using anonId only while the response is held in memory.
    # The source bidder label itself must not be persisted.
    cumulative_unique_bidder_count = Field()