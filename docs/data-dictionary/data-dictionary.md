# Data Dictionary

**Last Updated:** October 14, 2026
**Status:** Pre-collection schema planning
**Schema Version:** 0.1

## Purpose

This data dictionary documents the fields currently expected to be retained in the project’s SQLite database. It records each field’s intended name, SQLite storage type, whether it's a derived or original field, nullability, constraints, and analytical meaning.

The [data field inventory](../compliance/data-field-inventory.md) documents all fields observed in the source responses, including fields that will not be retained. This data dictionary is limited to fields currently planned for storage.

## A work in progress

This document doesn't represent the final database schema at this time. The current definitions are based on API response samples and preliminary research findings.

The tables may therefore be expanded, reorganized, or revised over the next several weeks.

## Conventions

### SQLite storage data types

Data recovered from the API is initially decoded into Python objects. When the data is inserted into SQLite, the `sqlite3` module automatically binds supported Python data types to SQLite storage classes. For example, Python integers are stored as INTEGER, strings as TEXT, floats as REAL, byte data as BLOB, and None as NULL.

SQLite does not have storage classes that map directly to other Python data types - including booleans, dates, datetimes, and fixed-precision decimal values. These values must therefore be represented using one of SQLite’s supported storage classes. The following table defines how these logical data types are represented within the project database.


| Logical value | SQLite type | Storage convention |
|---|---|---|
| Identifiers | `INTEGER` or `TEXT` | Numeric identifiers use `INTEGER`, while alphanumeric identifiers use `TEXT`. |
| Boolean | `INTEGER` | Store `0` for false and `1` for true. |
| Money | `INTEGER` | Convert dollar amounts to integer cents before storage. |
| Count | `INTEGER` | Store whole-number counts without conversion. |
| Duration | `INTEGER` | Store durations in the unit named by the column, normally seconds, but potentially milliseconds. |
| Ratio or rate | `REAL` | Use only for noncurrency calculations such as ratios and averages. |
| Timestamp | `TEXT` | Store normalized ISO 8601 timestamps with UTC offsets. |
| Calendar date | `TEXT` | Store as `YYYY-MM-DD`. |
| Category | `TEXT` | Preserve the source value initially; standardize through documented transformations. |
| Missing value | `NULL` | Never replace missing values with zero, an empty string, or `"unknown"` unless that value has a distinct documented meaning. |

## Validation and transformations

Some fields must be validated and/or transformed before being inserted into SQLite. Validation ensures that a field value follows the expected rules. Transformations change values into the representation selected for the database, such as converting dollar amounts into integer cents so it's bound as an INTEGER rather than a REAL. 

After these steps are complete, the sqlite3 module automatically binds that value to the corresponding SQLite storage class. These validation and transformation rules help preserve data integrity and ensure that values are stored consistently throughout the database.

| Field | API value | Python after parsing | Transformation | SQLite type |
|---|---|---|---|---|
| `auction_id` | `71841` | `int` | None | `INTEGER` |
| `auction_number` | `"HEA2602-01-A1"` | `str` | None | `TEXT` |
| `is_shippable` | `0` | `int` | Validate and convert to Boolean | `INTEGER` |
| `retail_price_cents` | `104.99` | `float` | Decimal dollars → integer cents | `INTEGER` |
| `bid_at_source_utc` | ISO timestamp | `str` | Validate and normalize | `TEXT` |
| `total_lots` | `null` | `None` | None | `NULL` in an `INTEGER` column |

## Database Schema

### Table: `collection_runs`

One row represents one successful data collection run.

| Important column | SQLite type | Purpose |
|---|---|---|
| `collection_run_id` | `INTEGER` | Primary key |
| `started_at_utc` | `TEXT` | Collection run began timestamp |
| `completed_at_utc` | `TEXT` | Collection run completed timestamp |
| `target_start_date` | `TEXT` | Earliest authorized auction date (`YYYY-MM-DD`) |
| `target_end_date` | `TEXT` | Latest authorized auction date (`YYYY-MM-DD`) |
| `target_building_ids` | `TEXT` | Documented location scope |
| `scraper_version` | `TEXT` | Web scraper version used during run |
| `schema_version` | `TEXT` | Database schema version used during run |
| `status` | `TEXT` | `running`, `completed`, `stopped`, or `failed` |
| `stop_reason` | `TEXT` | Reason for interruption (rate limiting, no data found, etc.) |

### Table: `endpoint_fetches`

Tracks each request and its outcome. 

| Important column | SQLite type | Purpose |
|---|---|---|
| `endpoint_fetch_id` | `INTEGER` | Primary key |
| `collection_run_id` | `INTEGER` | Foreign key |
| `endpoint_type` | `TEXT` | `auction_lookup`, `auction_items`, `item_details`, or `bid_history` |
| `auction_id` | `INTEGER` | Associated auction when applicable |
| `lot_id` | `INTEGER` | Associated lot when applicable |
| `page_number` | `INTEGER` | Page for paginated requests |
| `requested_at_utc` | `TEXT` | Request timestamp |
| `completed_at_utc` | `TEXT` | Response timestamp |
| `http_status` | `INTEGER` | HTTP response status |
| `result_status` | `TEXT` | `success`, `not_found`, `failed` |
| `retry_count` | `INTEGER` | Number of retries |
| `served_from_cache` | `INTEGER` | Boolean cache indicator |
| `error_message` | `TEXT` | Error information provided in response |

###  Table: `auctions`

One row represents one auction. The stored data is shared by all items in the auction.

| Column | SQLite type | Origin | Source or formula | Nullable | Key or constraint | Description |
|---|---|---|---|---:|---|---|
| `auction_id` | `INTEGER` | Original | `id` | No | Primary key | Numeric auction identifier. |
| `auction_number` | `TEXT` | Original | `auction_number` | No | Unique | Alphanumeric auction identifier. |
| `auction_opens_date` | `TEXT` | Derived | `opening_date` | Yes | "YYYY-MM-DD" | Scheduled auction opening date. |
| `auction_closes_date` | `TEXT` | Derived | `closing_date` | Yes | "YYYY-MM-DD" | Scheduled auction closing date. |
| `auction_launched_at_utc` | `TEXT` | Original | `date_launched` | Yes | ISO 8601 timestamp | Time the auction was launched. |
| `pickup_date_text` | `TEXT` | Original | `pickup_date` | Yes | Provisional | Pickup date formatted as day of the week (MM/DD). |
| `abandon_date` | `TEXT` | Derived | `abandon_date` | Yes | "YYYY-MM-DD" | Reported deadline associated with abandoned purchases. |
| `scheduled_duration_seconds` | `INTEGER` | Derived | Closing time minus opening time | Yes | — | Scheduled duration of the auction. |
| `launch_to_close_seconds` | `INTEGER` | Derived | Closing time minus launch time | Yes | — | Time from launch until scheduled closing. |
| `building_id` | `INTEGER` | Original | `building_id` | No | Indexed | Warehouse identifier used to define project scope. |
| `location_id` | `INTEGER` | Original | `location_id` | No | — | The item's location. One building_id can have many location_id's attached to it. |
| `location_name` | `TEXT` | Original | `location_name` | No | — | Readable version of warehouse and auction group. |
| `auction_type_id` | `INTEGER` | Original | `auction_type_id` | Yes | — | Numeric auction-type identifier. |
| `allows_transfers` | `INTEGER` | Original | `allow_transfers` | Yes | Boolean check | Whether transfers are allowed in general. |
| `allows_free_transfers` | `INTEGER` | Original | `free_transfers` | Yes | Boolean check | Whether transfers are free in general. |
| `is_online_only` | `INTEGER` | Original | `online_only` | Yes | Boolean check | Whether the auction is online-only. |
| `is_members_only` | `INTEGER` | Original | `members_only` | Yes | Boolean check | Whether participation is restricted to members. |
| `is_non_taxable` | `INTEGER` | Original | `non_taxable` | Yes | Boolean check | Whether the auction is designated as non-taxable. |
| `is_immediate_settlement` | `INTEGER` | Original | `immediate_settle` | Yes | Boolean check | Whether immediate settlement is enabled. |
| `stagger_close_seconds` | `INTEGER` | Original | `stagger_close_seconds` | Yes | Nonnegative | Interval between scheduled lot closings. |
| `extension_window_seconds` | `INTEGER` | Original | `extension_window_seconds` | Yes | Nonnegative | Time window in which a late bid triggers an extension. |
| `time_extension_seconds` | `INTEGER` | Original | `time_extension_seconds` | Yes | Nonnegative | Duration added when an extension is triggered. |
| `lot_fee_override_cents` | `INTEGER` | Original | `lot_fee_override × 100` | Yes | Units require validation | Auction-level lot-fee override. |
| `reported_total_lots` | `INTEGER` | Original | `total_lots` | Yes | Nonnegative | Total lot count reported by the API. |
| `observed_lot_count` | `INTEGER` | Derived | Count of retrieved unique lot IDs | Yes | Nonnegative | Number of distinct lots actually retrieved for the auction. |
| `collection_run_id` | `INTEGER` | Operational | Collector | No | Foreign key | Collection run that created or most recently refreshed the record. |
| `collected_at_utc` | `TEXT` | Operational | Collector clock | No | ISO 8601 timestamp | Time this auction response was collected. |

`buyers_premium_override` cannot be added until figuring out whether the source value represents a currency amount, percentage, or decimal rate.

## Table: `auction_items`

One row represents one auction lot item. While many of the same fields can be fetched from items[], using the single-item checkpoint fetches additional item-specific fields. 

| Column | SQLite type | Origin | Source or formula | Nullable | Key or constraint | Description |
|---|---|---|---|---:|---|---|
| `lot_id` | `INTEGER` | Original | `id` | No | Primary key | Numeric lot identifier. |
| `auction_id` | `INTEGER` | Original | `auction_id` | No | Foreign key | Auction containing the lot. |
| `lot_number` | `TEXT` | Original | `lot_number` | No | Unique with `auction_id` | Alphanumeric lot identifier. |
| `product_id` | `INTEGER` | Original | `product_id` | Yes | Indexed | Potential catalog-level identifier for repeated products. |
| `inventory_id` | `INTEGER` | Original | `inventory_id` | Yes | — | Identifier for the physical inventory record. |
| `current_location_id` | `INTEGER` | Original | `current_location_id` | Yes | — | Current location associated with the lot. The value can differ from its auctions.location_id value. |
| `lot_closed_expected_utc` | `TEXT` | Original | `expected_close_date` | Yes | Under validation | Expected closing time reported by the item endpoint. |
| `lot_closed_actual_utc` | `TEXT` | Original | `closed_date` | Yes | Under validation | Actual closing time reported by the item endpoint. |
| `bid_history_end_at_source_utc` | `TEXT` | Original | Bid-history `lot_end_time` | Yes | Under validation | End time reported by the bid-history endpoint. |
| `product_name` | `TEXT` | Original | `product_name` | Yes | — | Product name used internally for product matching. |
| `product_model` | `TEXT` | Original | `model` | Yes | — | Product model when available. |
| `product_identifier` | `TEXT` | Original | `upc` | Yes | Indexed | Source product identifier; stored as text because values may be nonnumeric. |
| `category_name` | `TEXT` | Original | `category` or `category_name` | Yes | — | Standardized product category. |
| `condition_name` | `TEXT` | Original | `condition_name` | Yes | — | Structured condition category. |
| `dimensions_text` | `TEXT` | Original | `dimensions` | Yes | Provisional | Unparsed source dimensions. |
| `size_text` | `TEXT` | Original | `size` | Yes | Provisional | Unparsed source size. |
| `quantity` | `INTEGER` | Original | `quantity` | Yes | Requires validation | Item quantity reported by the auction-items endpoint. |
| `box_count` | `INTEGER` | Original | `boxes` | Yes | Nonnegative | Number of boxes reported for the lot. |
| `retail_price_cents` | `INTEGER` | Original | `retail_price × 100` | Yes | Nonnegative | Reported retail price. |
| `instant_win_price_cents` | `INTEGER` | Original | `instant_win_price × 100` | Yes | Nonnegative | Immediate-purchase price when available. |
| `buyers_assurance_cost_cents` | `INTEGER` | Original | `buyers_assurance_cost × 100` | Yes | Nonnegative | Reported buyer-assurance cost. |
| `winning_bid_amount_cents` | `INTEGER` | Target | `winning_bid_amount × 100` | Yes | Nonnegative | Final winning bid amount and principal prediction target. |
| `reported_total_bid_count` | `INTEGER` | Original | `total_bids` | Yes | Nonnegative | Final bid count reported by the item endpoint. |
| `reported_unique_bidder_count` | `INTEGER` | Original | `unique_bidders` | Yes | Nonnegative | Final unique-bidder count reported by the item endpoint. |
| `is_transferable` | `INTEGER` | Original | `is_transferrable` | Yes | Boolean check | Whether the lot can be transferred. Can only be true if auctions.allows_transfers is true. |
| `is_shippable` | `INTEGER` | Original | `is_shippable` | Yes | Boolean check | Whether shipping is available. |
| `is_pallet` | `INTEGER` | Original | `is_pallet` | Yes | Boolean check | Whether the lot is a pallet. |
| `is_partial` | `INTEGER` | Original | `is_partial` | Yes | Boolean check | Whether the lot is identified as partial or incomplete. |
| `is_tested` | `INTEGER` | Original | `is_tested` | Yes | Boolean check | Whether the item was tested. |
| `is_as_is` | `INTEGER` | Derived | Predefined description rule | Yes | Boolean check | Whether approved source text explicitly identifies the item as “As-Is.” |
| `has_partial_note` | `INTEGER` | Derived | Nonempty `partial_note` | Yes | Boolean check | Whether a partial-item note was present. |
| `has_tested_note` | `INTEGER` | Derived | Nonempty `tested_note` | Yes | Boolean check | Whether a testing note was present. |
| `has_damage_note` | `INTEGER` | Derived | Nonempty `damaged_note` | Yes | Boolean check | Whether a damage note was present. |
| `observed_bid_record_count` | `INTEGER` | Derived | Count of retrieved bid records | Yes | Nonnegative | Number of bid events returned by the bid-history endpoint. |
| `bid_count_difference` | `INTEGER` | Derived | Reported bid count minus observed bid records | Yes | — | Difference between the two bid-count measures. |
| `end_time_difference_seconds` | `INTEGER` | Derived | Bid-history end time minus item close time | Yes | — | Used to identify timestamp inconsistencies. |
| `winning_to_retail_ratio` | `REAL` | Derived | Winning bid divided by retail price | Yes | Nonnegative | Final bid as a proportion of reported retail price. |
| `discount_rate` | `REAL` | Derived | `1 - winning_to_retail_ratio` | Yes | — | Proportion below reported retail price. |
| `collection_run_id` | `INTEGER` | Operational | Collector | No | Foreign key | Collection run associated with the record. |
| `collected_at_utc` | `TEXT` | Operational | Collector clock | No | ISO 8601 timestamp | Time the lot response was collected. |

## Table: `bid_events`

One row represents one bid event returned by the public bid-history endpoint.

The API’s anonymous bidder label is used transiently while calculating bidder-based features but is not retained in this table.

| Column | SQLite type | Origin | Source or formula | Nullable | Key or constraint | Description |
|---|---|---|---|---:|---|---|
| `bid_event_id` | `INTEGER` | Operational | Locally generated | No | Primary key | Surrogate key for the stored bid event. |
| `lot_id` | `INTEGER` | Original | `lot_id` | No | Foreign key | Lot associated with the bid. |
| `source_position` | `INTEGER` | Operational | Position in API array | No | Nonnegative | Original response position for audit purposes. |
| `bid_sequence` | `INTEGER` | Derived | Chronological order after sorting | No | Unique with `lot_id` | One-based chronological sequence within the lot. |
| `bid_amount_cents` | `INTEGER` | Original | `bid_amount × 100` | No | Nonnegative | Bid amount returned for the event. |
| `displayed_bid_cents` | `INTEGER` | Original | `displayedBid × 100` | Yes | Nonnegative | Publicly displayed bid following the event. |
| `bid_at_source_utc` | `TEXT` | Original | `bid_time` | No | Under timestamp validation | Bid timestamp reported by the API. |
| `lot_end_at_source_utc` | `TEXT` | Original | `lot_end_time` | Yes | Under timestamp validation | Lot end time repeated in the bid-history response. |
| `bid_type` | `TEXT` | Original | `bidType` | Yes | Controlled category | Bid mechanism, such as `manual`. |
| `is_matched_proxy` | `INTEGER` | Original | `isMatchedProxy` | Yes | Boolean check | Whether the event is marked as a matched proxy event. |
| `milliseconds_before_end` | `INTEGER` | Derived | Lot end time minus bid time | Yes | — | Time remaining when the bid occurred. |
| `milliseconds_since_previous_bid` | `INTEGER` | Derived | Current bid time minus preceding bid time | Yes | Nonnegative | Gap between consecutive returned bid records. |
| `bid_increment_cents` | `INTEGER` | Derived | Current displayed bid minus previous displayed bid | Yes | — | Change in displayed price from the previous event. |

## Table: `lot_checkpoint_features`

One row represents the state of one lot at one predefined prediction checkpoint.
