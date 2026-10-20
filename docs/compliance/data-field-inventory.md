# Data Field Inventory

Status: Preliminary
Based on: Endpoint samples captured 2026-10-16

## Purpose: 

This data field inventory documents the fields observed in responses from the four public, unauthenticated MAC.BID API endpoints used by this project. 

Because it is based on observed API responses rather than an official schema, it will be reviewed after initial data collection and updated when new values, types, or response structures are discovered.

### Endpoint 1: Auction lookup by auction number

#### GET `/auctions/{auction_number}?getItems=0`

**Response shape:** One auction JSON object.

**Collection note:** Because `getItems=0`, the `items` array is expected
to be empty. Item records are obtained through endpoint 2: auction items by auction ID.

#### Top-level auction fields

| JSON field | Observed type | Null in sample? | Preliminary decision | Reason or interpretation |
|---|---|---:|---|---|
| `id` | Integer | No | Retain | Numeric auction ID; required for retrieving auction items. Rename `auction_id` in the retained dataset. |
| `date_created` | ISO 8601 timestamp | No | Exclude | Indicates when the auction record was created. |
| `auction_number` | String | No | Retain | Human-readable auction identifier and connection to generated candidates. |
| `opening_date` | ISO 8601 timestamp | No | Derive and discard | Allows calculation of the auction’s scheduled duration. |
| `closing_date` | ISO 8601 timestamp | No | Derive and discard | Auction closing time and primary temporal reference. |
| `external_folder_name` | Null; likely string | Yes | Exclude | Appears to be an internal operational field. |
| `pickup_date` | String | No | Investigate | Human-formatted pickup information, not a complete timestamp. Pickup timing could potentially affect bidding. |
| `closed_for_entry` | Integer flag | No | QA only | Likely indicates whether new inventory can be added; not necessarily whether bidding is open. |
| `location_id` | Integer | No | Retain | Location identifier. Keep alongside `building_id` until their meanings are fully established. |
| `allow_transfers` | Integer flag | No | Retain | Transfer availability might affect which customers can realistically bid. |
| `abandon_date` | ISO 8601 timestamp | No | Exclude | May indicate the deadline after which uncollected purchases are abandoned. |
| `auction_mobility_id` | Null; likely integer or string | Yes | Exclude | Appears to be an internal system identifier. |
| `auction_type_id` | Integer | No | Retain | May identify materially different auction formats. Meaning needs documentation. |
| `removal_text` | Null; likely string | Yes | Exclude | Free-form operational or instructional text; not currently needed. |
| `is_active` | Integer flag | No | QA only | Meaning is ambiguous: the sample has `is_active=1` but `is_open=0`. Do not interpret this as bidding status. |
| `free_transfers` | Integer flag | No | Retain | Could affect bidder participation or total acquisition cost. |
| `date_launched` | ISO 8601 timestamp | No | Retain | Actual launch time; may differ from `opening_date` and can support duration features. |
| `date_completed` | Null; expected timestamp | Yes | QA only | Appears operational. Investigate only if it proves necessary for identifying completed auctions. |
| `is_open` | Integer flag | No | QA only | Useful for confirming the auction is closed before collection. |
| `stagger_close_seconds` | Integer | No | Retain | Auction-rule feature describing staggered lot closing. |
| `extension_window_seconds` | Integer | No | Retain | Defines when late bidding triggers an extension. Relevant to dynamic bidding behavior. |
| `time_extension_seconds` | Integer | No | Retain | Length of a bidding-time extension. Relevant to auction dynamics. |
| `total_lots` | Null; expected integer | Yes | Investigate | Potentially useful, but null in this response. Actual retrieved item counts may be more dependable. |
| `online_only` | Integer flag | No | Retain | Auction-format feature that may affect participation. |
| `members_only` | Integer flag | No | Retain | Participation restriction that could affect bidder population and prices. |
| `new_billing` | Integer flag | No | Exclude | Appears to describe an internal billing implementation. |
| `label_size` | Null; type unknown | Yes | Exclude | Appears to be an internal warehouse or printing field. |
| `title` | Null; expected string | Yes | Investigate | May distinguish special auction types, but is free-form expressive content. |
| `description` | Null; expected string | Yes | Exclude | Free-form expressive content not currently necessary for auction identification. |
| `logo` | Null; expected string or URL | Yes | Exclude | Branding or image reference not needed for analysis. |
| `date_reviewed` | Null; expected timestamp | Yes | Exclude | Appears to describe an internal review workflow. |
| `lot_fee_override` | Number | No | Retain | Transaction-cost feature that may affect bidding. Verify whether the value is expressed in dollars. |
| `buyers_premium_override` | Null; expected number | Yes | Retain | Buyer’s premium affects total customer cost. Store as nullable and verify whether it represents a percentage or amount. |
| `immediate_settle` | Integer flag | No | Investigate | May identify differences in payment timing or auction rules. |
| `custom_invoice_email` | Null; expected string | Yes | Exclude | Potential contact or administrative content and unnecessary for the research. |
| `non_taxable` | Integer flag | No | Retain | Tax treatment may affect the customer’s effective total cost. |
| `summary_email` | Null; type unknown | Yes | Exclude | Appears to be an internal email or notification setting. |
| `info_message` | Null; expected string | Yes | Exclude | Free-form informational content not required for the model. |
| `registration_message` | Null; expected string | Yes | Exclude | Free-form registration content not required for the model. |
| `pickup_override` | Null; expected string or flag | Yes | Investigate | Meaning is unclear; may contain operational pickup information. |
| `slug` | Null; expected string | Yes | Exclude | Website-routing field that is unnecessary because you already have stable identifiers. |
| `location_auction_build_config_id` | Integer | No | Exclude | Appears to be an internal configuration identifier. |
| `location_name` | String | No | Retain | Human-readable location and auction group, such as `Henderson - A`. |
| `building_id` | Integer | No | Retain | Primary warehouse filter used to identify Henderson and North Las Vegas. |
| `items` | Array | No | Exclude from this endpoint | Empty because `getItems=0`; items should come from the dedicated auction-items request. |

### Endpoint 2: Auction items by auction ID

#### GET `/auctions/{auction_id}?pg={page}&ppg={page_size}`

**Response shape:** One auction JSON object containing an `items` array.

**Top-level auction fields:** Same auction fields documented for
`GET /auctions/{auction_number}?getItems=0`.

**Pagination note:** The provided response contains the first page of
up to 100 items. Because `total_lots` is null, total auction size should
not be inferred from that field. Pagination behavior must be verified
using additional pages.

#### items[] fields

| JSON field | Observed type | Null in sample? | Preliminary decision | Reason or interpretation |
|---|---|---:|---|---|
| `id` | Integer | No | Retain | Numeric lot ID. Required for bid-history requests. Rename `lot_id`. |
| `auction_id` | Integer | No | Retain | Foreign key connecting the lot to its auction. |
| `closed_date` | ISO 8601 timestamp | No | Retain | Actual lot closing time. May differ among lots because of staggered closing and extensions. |
| `expected_close_date` | ISO 8601 timestamp | No | Retain with caution | Expected closing time. Determine whether a historical response reflects the original schedule or incorporates extensions. |
| `inventory_id` | Integer | No | Investigate | Likely identifies the underlying physical inventory record. Its usefulness for detecting repeated products is not yet established. |
| `date_created` | ISO 8601 timestamp | No | Retain | Time the lot record was created. Rename `lot_created_at_utc`. |
| `lot_number` | String | No | Retain | Auction-relative identifier used by the single-item endpoint. |
| `listing_url` | Null; expected string/URL | Yes | Exclude | External or internal listing link that is unnecessary for the analysis. |
| `is_open` | Integer flag | No | QA only | Confirms whether bidding remains open for the lot. |
| `is_transferrable` | Integer flag | No | Retain | Transfer availability could affect demand. Correct spelling to `is_transferable` in curated data. |
| `total_bids` | Integer | No | **Retain with leakage controls** | Final bid count is an outcome. It must not be used as an earlier-time predictor unless calculated from bids available at prediction time. |
| `winning_customer_id` | Integer | No | **Exclude (ensures data compliance)** | Customer-linked identifier that is unnecessary for the research. |
| `winning_bid_id` | String | No | **Derive then discard (ensures data compliance)** | Contains a timestamp and customer identifier. If the final-bid timestamp is necessary, extract only the timestamp and discard the original value. |
| `winning_bid_amount` | JSON number | No | Retain | Primary final-price outcome. Convert to integer cents in curated data. |
| `unique_bidders` | Integer | No | **Retain with leakage controls** | Useful outcome or descriptive measure. Final bidder count cannot be used as a pre-close predictor. |
| `pulled_date` | Null; expected timestamp | Yes | Exclude | Appears to be an internal warehouse-operation field. |
| `pulled_by` | Null; type unknown | Yes | Exclude | Could identify an employee or operational account. Not necessary. |
| `title` | String | No | Exclude as duplicate | Duplicates `product_name` in this sample. Reconsider only if later samples show meaningful differences. |
| `product_name` | String | No | Retain | Needed for product identification and matching repeated products. Do not republish full listings. |
| `upc` | String | No | Retain | Potential repeated-product identifier. Store as text because values may contain letters or leading zeros. |
| `description` | String | No | Derive then discard | Expressive listing content. Extract only predefined necessary features, such as an explicit “As-Is” indicator, then discard the full text. |
| `dimensions` | String | No | Investigate | Potential product-size feature, but format requires normalization. |
| `quantity` | Integer | No | Retain with validation | Item quantity may affect price. The observed value of zero requires investigation. |
| `is_pallet` | Integer flag | No | Retain | Product/auction format feature that may strongly affect price. |
| `is_shippable` | Integer flag | No | Retain | Availability of shipping may affect bidder participation. |
| `current_location_id` | Integer | No | Retain | Lot-level location identifier. Useful for validating consistency with the auction location. |
| `shipping_height` | Null; expected number | Yes | Investigate | Potential physical-size feature. Units must be established. |
| `shipping_width` | Null; expected number | Yes | Investigate | Potential physical-size feature. Units must be established. |
| `shipping_length` | Null; expected number | Yes | Investigate | Potential physical-size feature. Units must be established. |
| `warehouse_location` | String | No | Exclude | Exact internal storage position is unnecessary and could change operationally. |
| `shipping_weight` | Null; expected number | Yes | Investigate | Potential product feature. Units must be established. |
| `case_packed_qty` | Null; expected number | Yes | Investigate | May represent package quantity; meaning must be verified. |
| `retail_price` | JSON number | No | Retain | Important baseline-price feature. Convert to integer cents in curated data. |
| `is_partial` | Integer flag | No | Retain | May indicate incomplete merchandise and materially affect value. |
| `condition_name` | String | No | Retain | Important product-condition feature, such as `OPEN BOX`. |
| `category` | String | No | Retain | Product category for modeling, grouping, and evaluation. |
| `image_url` | String/URL | No | Exclude | Product photograph reference is not needed for the planned model. |
| `building_id` | Integer | No | Retain | Warehouse identifier used for project scope filtering. |

### Endpoint 3: Single item by auction number and lot number

#### GET `/auction/{auction_number}/lot/{lot_number}`

**Response shape:** One lot JSON object containing:

- detailed lot and product fields;
- an `images` array; and
- a nested `auction` object.

**Identifier note:** This endpoint requires the alphanumeric
`lot_number`, not the numeric `lot_id`.

#### Single item fields

| JSON field | Observed type | Null in sample? | Preliminary decision | Reason or interpretation |
|---|---|---:|---|---|
| `product_id` | Integer | No | Retain | Potential catalog-level product identifier. Could be especially valuable for recognizing repeated identical products. |
| `id` | Integer | No | Retain | Numeric lot ID required by the bid-history endpoint. Rename `lot_id`. |
| `auction_type` | String | No | Retain | Human-readable auction format, such as `standard`. |
| `auction_id` | Integer | No | Retain | Foreign key connecting the lot to its auction. |
| `closed_date` | ISO 8601 timestamp | No | Retain | Actual lot closing time. |
| `expected_close_date` | ISO 8601 timestamp | No | Retain with caution | Determine whether historical responses contain the original expected close or the final extension-adjusted time. |
| `instant_win_price` | JSON number | No | Retain | Immediate-purchase price potentially visible to bidders. Convert to integer cents. |
| `buyers_assurance_cost` | JSON number | No | Retain | Additional customer cost that could affect bids. Convert to integer cents. |
| `current_location_id` | Integer | No | Retain | Lot-level location identifier. |
| `inventory_id` | Integer | No | Investigate | Likely identifies the physical inventory record rather than a reusable product. |
| `update_text` | Null; expected string | Yes | Derive then discard | Potential free-form listing update. If needed, retain only a predefined flag such as `has_update`. |
| `date_created` | ISO 8601 timestamp | No | Retain | Time the lot record was created. |
| `lot_number` | String | No | Retain | Auction-relative item identifier. |
| `listing_url` | Null; expected URL | Yes | Exclude | External or internal listing link unnecessary for the analysis. |
| `title` | String | No | Exclude as duplicate | Duplicates `product_name` in this sample. Reconsider if later samples show meaningful differences. |
| `is_open` | Integer flag | No | QA only | Confirms whether the lot remains open. |
| `is_transferrable` | Integer flag | No | Retain | Transfer eligibility could affect demand. Rename corrected field to `is_transferable`. |
| `total_bids` | Integer | No | **Retain with leakage controls** | Final bid count. Do not use as an earlier-time feature unless reconstructed from bid history. |
| `winning_customer_id` | Integer | No | **Exclude (ensures data compliance)** | Customer-linked identifier unnecessary for the research. |
| `winning_bid_id` | String | No | **Derive then discard (ensures data compliance)** | Contains both a timestamp and customer ID. Extract only the timestamp if justified. |
| `winning_bid_amount` | JSON number | No | **Retain with leakage controls** | Final-price outcome. Convert to integer cents. |
| `unique_bidders` | Integer | No | **Retain with leakage controls** | Final bidder count; not valid as an earlier-time predictor. |
| `product_name` | String | No | Retain | Needed to identify and match repeated products. Do not republish listings. |
| `lot_status` | String | No | QA only | `PICKED UP` is a post-auction operational status, not a prediction-time feature. |
| `description` | String | No | Derive then discard | Expressive listing content. Extract only predefined features such as `is_as_is`, then discard the text. |
| `size` | Null; expected string | Yes | Investigate | Potential product-size feature. Meaning and formatting need validation. |
| `is_shippable` | Integer flag | No | Retain | Shipping availability could affect bidder participation. |
| `model` | Null; expected string | Yes | Retain | Product-model identifier could substantially improve repeated-product matching. |
| `warehouse_location` | String | No | Exclude | Internal shelf or warehouse position is unnecessary. |
| `dimensions` | String | No | Investigate | Potential size feature requiring normalization and unit validation. |
| `is_partial` | Integer flag | No | Retain | Indicates potentially incomplete merchandise. |
| `partial_note` | String | No | Derive then discard | Free-form expressive content. Consider retaining only `has_partial_note`. |
| `is_tested` | Integer flag | No | Retain | Structured condition information likely relevant to price. |
| `tested_note` | String | No | Derive then discard | Retain only a predefined indicator or structured result if necessary. |
| `damaged_note` | String | No | Derive then discard | Damage is relevant, but the complete free-form text need not be retained. |
| `upc` | String | No | Retain | Potential product identifier. Keep as text because values may contain letters or leading zeros. |
| `boxes` | Integer | No | Retain | Number of boxes associated with the lot; may reflect product size or completeness. |
| `category_name` | String | No | Retain | Product category. Standardize with the `category` field from Endpoint 2. |
| `retail_price` | JSON number | No | Retain | Important baseline-price feature. Convert to integer cents. |
| `condition_name` | String | No | Retain | Structured product-condition category. |
| `image_url` | String/URL | No | Exclude | Product photograph reference is unnecessary for the planned model. |
| `images` | Array of objects | No | Exclude | Photographs and their metadata are unnecessary for the planned model. |
| `auction` | Object | No | Do not duplicate | Nested auction metadata already collected through the auction endpoints. Use it for validation rather than storing another copy. |

### Endpoint 4: Bid history by lot ID

#### GET `/auctions/lot/{lot_id}/bid-history`

**Response shape:** One JSON object containing a `bids` array.

**Identifier note:** This endpoint requires the numeric `lot_id`,
not the alphanumeric `lot_number`.

#### Top-level fields

| JSON field | Observed type | Decision | Reason |
|---|---|---|---|
| `bids` | Array of objects | Retain selectively | Contains the bid-event history used to construct dynamic features. |

#### bids[] field inventory

| JSON field | Observed type | Null in sample? | Preliminary decision | Reason or interpretation |
|---|---|---:|---|---|
| `lot_id` | Integer | No | Retain | Foreign key connecting each bid to its lot. |
| `bid_amount` | JSON number | No | Retain | Amount submitted for the bid event. Convert to integer cents. |
| `bid_time` | ISO 8601 timestamp | No | Retain | Timestamp of the bid event; essential for time-dependent features. |
| `lot_end_time` | ISO 8601 timestamp | No | Retain with caution | End time reported by the bid-history system. It conflicts with `closed_date` from the item endpoints in this example. |
| `isMatchedProxy` | Boolean | No | Retain | Indicates whether the event represents or involves a matched proxy bid. Meaning should be validated with examples containing `true`. |
| `anonId` | String | No | **Derive then discard (ensures data compliance)** | Per-lot pseudonymous bidder label. Use temporarily to calculate bidder-based features, then remove. |
| `displayedBid` | JSON number | No | Retain | Bid amount displayed after the event. May differ from `bid_amount` during proxy bidding. Convert to integer cents. |
| `bidType` | String | No | Retain | Bid mechanism, such as `manual`. Standardize as a categorical value. |
| `isCurrentUser` | Boolean | No | Exclude | Account-relative field with no analytical value in an unauthenticated research collection. |
| `isCurrentWinner` | Boolean | Absent on some rows | **Exclude (ensures data compliance)** | Describes the final current winner when the response is retrieved; it is not a prediction-time feature. |