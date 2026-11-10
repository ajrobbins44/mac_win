# Data Field Inventory

Status: Post-collection staging inventory  
Source evidence: Endpoint samples captured 2026-10-16 and the January–March staging audit

## Purpose: 

This inventory records JSON fields observed in samples from the four public, unauthenticated MAC.BID endpoints used by this project. It documents each field's disposition at the API-to-staging boundary. The inventory reflects observed responses and may expand as new response shapes are encountered.

**Staging disposition.** “Stored in staging” means the source value is represented in staging, possibly under a different column name. “Not stored in staging” means the field is omitted from the staging records. “Expanded” means selected child values are written to staging rows. “Verify staging mapping” marks a documentation gap that requires a check against the existing collector and table definitions. Observed JSON types and sample nulls describe the response sample. SQLite types, nullability, and constraints come from the staging schema.

### Endpoint 1: Auction lookup by auction number

**Staging destination** — `staging_auctions`.

#### GET `/auctions/{auction_number}?getItems=0`

**Response shape:** One auction JSON object.

**Collection note:** Because `getItems=0`, the `items` array is expected
to be empty. Item records are obtained through endpoint 2: auction items by auction ID.

#### Top-level auction fields

| JSON field | Observed type | Null or absent in sample? | Staging disposition | Staging note or source interpretation |
|---|---|---:|---|---|
| `id` | Integer | No | Stored in staging | Stored as `auction_id`. The numeric ID is used for the auction-items request. |
| `date_created` | ISO 8601 timestamp | No | Not stored in staging | Indicates when the auction record was created. Only useful as an internal, administrative field. |
| `auction_number` | String | No | Stored in staging | Human-readable auction identifier and connection to generated candidates. |
| `opening_date` | ISO 8601 timestamp | No | Stored in staging | Source-reported scheduled opening. |
| `closing_date` | ISO 8601 timestamp | No | Stored in staging | Source-reported auction closing time. Lot-level closing times are recorded separately. |
| `external_folder_name` | Null; likely string | Yes | Not stored in staging | Appears to be an internal operational field. |
| `pickup_date` | String | No | Stored in staging | Human-formatted pickup information, not a complete timestamp. |
| `closed_for_entry` | Integer flag | No | Not stored in staging | Likely indicates whether new inventory details can be added. |
| `location_id` | Integer | No | Stored in staging | Location identifier stored separately from `building_id`. |
| `allow_transfers` | Integer flag | No | Stored in staging | Source flag for transfer availability. |
| `abandon_date` | ISO 8601 timestamp | No | Stored in staging | May indicate the deadline after which uncollected purchases are abandoned. |
| `auction_mobility_id` | Null; likely integer or string | Yes | Not stored in staging | Appears to be an internal system identifier. |
| `auction_type_id` | Integer | No | Stored in staging | Source auction-type identifier. |
| `removal_text` | Null; likely string | Yes | Not stored in staging | Free-form operational or instructional text; not currently needed. |
| `is_active` | Integer flag | No | Not stored in staging | Meaning is ambiguous: the sample has `is_active=1` but `is_open=0`. Do not interpret this as bidding status. |
| `free_transfers` | Integer flag | No | Stored in staging | Source flag for free transfers. |
| `date_launched` | ISO 8601 timestamp | No | Stored in staging | Source-reported launch time, recorded separately from `opening_date`. |
| `date_completed` | Null; expected timestamp | Yes | Not stored in staging | Appears operational. |
| `is_open` | Integer flag | No | Not stored in staging | The auction is already closed before collection. |
| `stagger_close_seconds` | Integer | No | Stored in staging | Source-reported staggered closing interval. |
| `extension_window_seconds` | Integer | No | Stored in staging | Source-reported window in which late bids may trigger an extension. |
| `time_extension_seconds` | Integer | No | Stored in staging | Source-reported extension length. |
| `total_lots` | Null; expected integer | Yes | Stored in staging | Stored as `total_lots_source`. NULL across the January–March audited auction rows. |
| `online_only` | Integer flag | No | Stored in staging | Source flag for online-only auctions. |
| `members_only` | Integer flag | No | Stored in staging | Source flag for members-only auctions. |
| `new_billing` | Integer flag | No | Not stored in staging | Appears to describe an internal billing implementation. |
| `label_size` | Null; type unknown | Yes | Not stored in staging | Appears to be an internal warehouse or printing field. |
| `title` | Null; expected string | Yes | Not stored in staging | May distinguish special auction types, but `auction_type` already handles same function. |
| `description` | Null; expected string | Yes | Not stored in staging | Free-form expressive content not currently necessary for auction identification. |
| `logo` | Null; expected string or URL | Yes | Not stored in staging | Branding or image reference not needed for analysis. |
| `date_reviewed` | Null; expected timestamp | Yes | Not stored in staging | Appears to describe an internal review workflow. |
| `lot_fee_override` | Number | No | Stored in staging | Stored as `lot_fee_override_source`. Source unit is unverified. |
| `buyers_premium_override` | Null; expected number | Yes | Stored in staging | Stored as `buyers_premium_override_source`. NULL across the January–March audited auction rows. Source meaning and unit are unverified. |
| `immediate_settle` | Integer flag | No | Stored in staging | Source flag for immediate settlement. |
| `custom_invoice_email` | Null; expected string | Yes | Not stored in staging | Potential contact or administrative content and unnecessary for the research. |
| `non_taxable` | Integer flag | No | Stored in staging | Source flag for tax treatment. |
| `summary_email` | Null; type unknown | Yes | Not stored in staging | Appears to be an internal email or notification setting. |
| `info_message` | Null; expected string | Yes | Not stored in staging | Free-form informational content not required for the model. |
| `registration_message` | Null; expected string | Yes | Not stored in staging | Free-form registration content not required for the model. |
| `pickup_override` | Null; expected string or flag | Yes | Not stored in staging | May contain operational pickup information, or involve a post-auction pickup date extension. Neither are relevant winning bid predictors. |
| `slug` | Null; expected string | Yes | Not stored in staging | Website-routing field that is unnecessary because you already have stable identifiers. |
| `location_auction_build_config_id` | Integer | No | Not stored in staging | Appears to be an internal configuration identifier. |
| `location_name` | String | No | Stored in staging | Human-readable location and auction group, such as `Henderson - A`. |
| `building_id` | Integer | No | Stored in staging | Primary warehouse identifier, such as `Henderson` or `North Las Vegas`. |
| `items` | Array | No | Not stored in staging | Empty because `getItems=0`; items should come from the dedicated auction-items request. |

### Endpoint 2: Auction items by auction ID

**Staging destination** — `staging_lot_summaries` (from `items[]`).

#### GET `/auctions/{auction_id}?pg={page}&ppg={page_size}`

**Response shape:** One auction JSON object containing an `items` array.

**Top-level auction fields:** Same auction fields documented for
`GET /auctions/{auction_number}?getItems=0`.

**Pagination note:** The provided response contains the first page of
up to 100 items. `total_lots` was NULL in the January–March staging audit. The array is a page of item observations.

#### items[] fields

| JSON field | Observed type | Null or absent in sample? | Staging disposition | Staging note or source interpretation |
|---|---|---:|---|---|
| `id` | Integer | No | Stored in staging | Stored as `lot_id`. The numeric ID is used for the bid-history request. |
| `auction_id` | Integer | No | Stored in staging | Auction identifier linking a lot to its parent auction. Many lots can share this value. |
| `closed_date` | ISO 8601 timestamp | No | Stored in staging | Source-reported lot close time. |
| `expected_close_date` | ISO 8601 timestamp | No | Stored in staging | Source-reported expected close. Whether historical responses reflect the original schedule or extensions is unverified. |
| `inventory_id` | Integer | No | Stored in staging | Likely identifies the underlying physical inventory record. |
| `date_created` | ISO 8601 timestamp | No | Stored in staging | Time the lot record was created. |
| `lot_number` | String | No | Stored in staging | Auction-relative lot identifier used by the single-item request. |
| `listing_url` | Null; expected string/URL | Yes | Not stored in staging | External or internal listing link that is unnecessary for the analysis. |
| `is_open` | Integer flag | No | Not stored in staging | Confirms whether bidding remains open for the lot. |
| `is_transferrable` | Integer flag | No | Stored in staging | Stored as `is_transferable_source`. |
| `total_bids` | Integer | No | Stored in staging | Final bid count reported by the endpoint, stored as `total_bids_source`. |
| `winning_customer_id` | Integer | No | Not stored in staging | Customer-linked identifier that is unnecessary for the research. |
| `winning_bid_id` | String | No | Not stored in staging | Contains a timestamp and customer identifier. |
| `winning_bid_amount` | JSON number | No | Stored in staging | Reported winning bid amount, stored as `winning_bid_amount_source`. |
| `unique_bidders` | Integer | No | Stored in staging | Final bidder count reported by the endpoint, stored as `unique_bidders_source`. |
| `pulled_date` | Null; expected timestamp | Yes | Not stored in staging | Appears to be an internal warehouse-operation field. |
| `pulled_by` | Null; type unknown | Yes | Not stored in staging | Could identify an employee or operational account. Not necessary. |
| `title` | String | No | Not stored in staging | Duplicates `product_name` in this sample. Reconsider only if later samples show meaningful differences. |
| `product_name` | String | No | Stored in staging | Source product name. |
| `upc` | String | No | Stored in staging | Stored as `product_upc`. Preserve source text and leading zeros. |
| `description` | String | No | Verify staging mapping | Expressive listing text. Verify whether staging stores a presence flag, a derived indicator, or the source value. |
| `dimensions` | String | No | Stored in staging | Stored as `dimensions_text`. Units and format are unverified. |
| `quantity` | Integer | No | Stored in staging | Stored as `quantity_source`. Zero has been observed; its meaning is unverified. |
| `is_pallet` | Integer flag | No | Stored in staging | Source pallet flag. |
| `is_shippable` | Integer flag | No | Stored in staging | Stored as `is_shippable_source`. |
| `current_location_id` | Integer | No | Stored in staging | Lot-level location reported at collection. |
| `shipping_height` | Null; expected number | Yes | Stored in staging | Potential physical-size feature. Units must be established. |
| `shipping_width` | Null; expected number | Yes | Stored in staging | Potential physical-size feature. Units must be established. |
| `shipping_length` | Null; expected number | Yes | Stored in staging | Potential physical-size feature. Units must be established. |
| `warehouse_location` | String | No | Not stored in staging | Exact internal storage position is unnecessary and could change operationally. |
| `shipping_weight` | Null; expected number | Yes | Stored in staging | Potential product feature. Units must be established. |
| `case_packed_qty` | Null; expected number | Yes | Stored in staging | May represent package quantity; meaning must be verified. |
| `retail_price` | JSON number | No | Stored in staging | Stored as `retail_price_source`. Summary and detail values are recorded separately. |
| `is_partial` | Integer flag | No | Stored in staging | Stored as `is_partial_source`. |
| `condition_name` | String | No | Stored in staging | Source-reported condition category. |
| `category` | String | No | Stored in staging | Stored as `category_name` in the lot summary table. |
| `image_url` | String/URL | No | Not stored in staging | Product photograph reference is not needed for the planned model. |
| `building_id` | Integer | No | Not stored in staging | Warehouse identifier already used for project scope filtering. |

### Endpoint 3: Single item by auction ID and lot number

**Staging destination** — `staging_lot_details`.

#### GET `/auction/{auction_id}/lot/{lot_number}`

**Response shape:** One lot JSON object containing:
- detailed lot and product fields;
- an `images` array; and
- a nested `auction` object.

#### Single item fields

| JSON field | Observed type | Null or absent in sample? | Staging disposition | Staging note or source interpretation |
|---|---|---:|---|---|
| `product_id` | Integer | No | Stored in staging | Source product identifier. Its stability across repeat listings is unverified. |
| `id` | Integer | No | Stored in staging | Stored as `lot_id`. The numeric ID is used for the bid-history request. |
| `auction_type` | String | No | Stored in staging | Human-readable auction format, such as `standard`. |
| `auction_id` | Integer | No | Stored in staging | Auction identifier linking a lot to its parent auction. Many lots can share this value. |
| `closed_date` | ISO 8601 timestamp | No | Stored in staging | Source-reported lot close time. |
| `expected_close_date` | ISO 8601 timestamp | No | Stored in staging | Source-reported expected close. Whether historical responses reflect the original schedule or extensions is unverified. |
| `instant_win_price` | JSON number | No | Stored in staging | Source-reported immediate-purchase price. |
| `buyers_assurance_cost` | JSON number | No | Stored in staging | Source-reported buyer-assurance cost. |
| `current_location_id` | Integer | No | Stored in staging | Lot-level location reported at collection. |
| `inventory_id` | Integer | No | Stored in staging | Likely identifies the underlying physical inventory record. |
| `update_text` | Null; expected string | Yes | Verify staging mapping | Free-form listing update. Verify whether staging stores a presence flag or the source value. |
| `date_created` | ISO 8601 timestamp | No | Stored in staging | Time the lot record was created. |
| `lot_number` | String | No | Stored in staging | Auction-relative lot identifier used by the single-item request. |
| `listing_url` | Null; expected URL | Yes | Not stored in staging | External or internal listing link unnecessary for the analysis. |
| `title` | String | No | Not stored in staging | Duplicates `product_name` in this sample. |
| `is_open` | Integer flag | No | Not stored in staging | Confirms whether bidding remains open for the lot. |
| `is_transferrable` | Integer flag | No | Stored in staging | Stored as `is_transferable_source`. |
| `total_bids` | Integer | No | Stored in staging | Final bid count reported by the endpoint, stored as `total_bids_source`. |
| `winning_customer_id` | Integer | No | Not stored in staging | Customer-linked identifier that is unnecessary for the research. |
| `winning_bid_id` | String | No | Not stored in staging | Contains a timestamp and customer identifier. |
| `winning_bid_amount` | JSON number | No | Stored in staging | Reported winning bid amount, stored as `winning_bid_amount_source`. |
| `unique_bidders` | Integer | No | Stored in staging | Final bidder count reported by the endpoint, stored as `unique_bidders_source`. |
| `product_name` | String | No | Stored in staging | Source product name. |
| `lot_status` | String | No | Stored in staging | Operational status observed at collection, for example `PICKED UP`. |
| `description` | String | No | Verify staging mapping | Expressive listing text. Verify whether staging stores a presence flag, a derived indicator, or the source value. |
| `size` | Null; expected string | Yes | Stored in staging | Potential product-size feature. |
| `is_shippable` | Integer flag | No | Stored in staging | Stored as `is_shippable_source`. |
| `model` | Null; expected string | Yes | Stored in staging | Source product model text. |
| `warehouse_location` | String | No | Not stored in staging | Internal shelf or warehouse position is unnecessary. |
| `dimensions` | String | No | Stored in staging | Stored as `dimensions_text`. Units and format are unverified. |
| `is_partial` | Integer flag | No | Stored in staging | Stored as `is_partial_source`. |
| `partial_note` | String | No | Verify staging mapping | Free-form note. Verify whether staging stores a presence flag or the source value. |
| `is_tested` | Integer flag | No | Stored in staging | Structured condition information likely relevant to price. |
| `tested_note` | String | No | Verify staging mapping | Free-form note. Verify whether staging stores a presence flag or the source value. |
| `damaged_note` | String | No | Verify staging mapping | Free-form note. Verify whether staging stores a presence flag or the source value. |
| `upc` | String | No | Stored in staging | Stored as `product_upc`. Preserve source text and leading zeros. |
| `boxes` | Integer | No | Stored in staging | Number of boxes associated with the lot; may reflect product size or completeness. |
| `category_name` | String | No | Stored in staging | Stored separately as `category_name` in the lot detail table. |
| `retail_price` | JSON number | No | Stored in staging | Stored as `retail_price_source`. Summary and detail values are recorded separately. |
| `condition_name` | String | No | Stored in staging | Source-reported condition category. |
| `image_url` | String/URL | No | Not stored in staging | Raw image references are omitted per the inventory. The audit shows a staged `has_primary_image` flag. Verify its exact source and rule. |
| `images` | Array of objects | No | Not stored in staging | Raw image references are omitted per the inventory. The audit shows a staged `has_primary_image` flag. Verify its exact source and rule. |
| `auction` | Object | No | Not stored in staging | Nested auction metadata. Auction records are obtained through the auction lookup. |

### Endpoint 4: Bid history by lot ID

**Staging destination** — `staging_lot_bid_histories` and `staging_bid_events`.

#### GET `/auctions/lot/{lot_id}/bid-history`

**Response shape:** One JSON object containing a `bids` array.

**Identifier note:** This endpoint requires the numeric `lot_id`,
not the alphanumeric `lot_number`.

#### Top-level fields

| JSON field | Observed type | Staging disposition | Reason |
|---|---|---|---|
| `bids` | Array of objects | Expanded | Selected child fields populate `staging_bid_events`. The response is also represented in `staging_lot_bid_histories`. |

#### bids[] field inventory

| JSON field | Observed type | Null or absent in sample? | Staging disposition | Staging note or source interpretation |
|---|---|---:|---|---|
| `lot_id` | Integer | No | Stored in staging | Lot identifier linking the event to its lot history. |
| `bid_amount` | JSON number | No | Stored in staging | Bid amount reported for the event. |
| `bid_time` | ISO 8601 timestamp | No | Stored in staging | Timestamp of the bid event; essential for time-dependent features. |
| `lot_end_time` | ISO 8601 timestamp | No | Stored in staging | End time reported by the bid-history endpoint. It differs from `closed_date` in the documented example. |
| `isMatchedProxy` | Boolean | No | Stored in staging | Source proxy-match flag. Exact semantics are unverified. |
| `anonId` | String | No | Verify staging mapping | Pseudonymous bidder label. Verify the collector and schema for persistence and any aggregate actually derived at ingestion. |
| `displayedBid` | JSON number | No | Stored in staging | Displayed bid amount reported for the event. It can differ from `bid_amount`. |
| `bidType` | String | No | Stored in staging | Source bid mechanism, for example `manual`. |
| `isCurrentUser` | Boolean | No | Not stored in staging | Account-relative field with no analytical value in an unauthenticated research collection. |
| `isCurrentWinner` | Boolean | Absent on some rows | Not stored in staging | Describes the final current winner when the response is retrieved; it is not a prediction-time feature. |

## Staging metadata and coverage

The field tables cover response values. The collector also records staging metadata such as `collection_run_id` and the history's `observed_bid_record_count`. These are generated during ingestion. Use the staging schema and collector to document their exact definitions. Summary and detail records may coexist for a lot and may differ in value or coverage.

Nested arrays and objects are listed at the level represented by the available samples. Their child keys are documented where the collector uses them or where separate field tables are provided.