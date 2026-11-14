# MAC.BID staging-to-processed plan

**Status** — Proposed schema v1, based on the pre-collection data dictionary, the two audit modules, and the audit output for month_01 through month_04. The mapping below distinguishes verified staging identifiers from source concepts whose exact SQLite column names need to be bound from the live schema. Audit results apply to those four audited snapshots.

## 1. What the finished database contains

The database has a normalized auction table, one consolidated lot row per lot, and one row per observed bid event. **Will add the checkpoint table after the base database validates.** It is built using the audited and processed input set derived from all staging databases.

| Table | Grain and keys | Purpose |
|---|---|---|
| `collection_runs` | One row per source run, PK `collection_run_id` and UQ `(source_db, source_collection_run_int)` | Collection provenance, including the source database and its source-assigned collection run id. |
| `auctions` | One row per `auction_id`, FK `collection_run_id` and UQ `auction_number` | Auction identity, location, timing, and validated policy fields |
| `auction_lots` | One row per `lot_id`, FK `collection_run_id` and UQ `(auction_id, lot_number)` | Consolidated lot attributes, row coverage, and eventual target |
| `lot_bid_histories` | One row per lot with a usable history response, PK `lot_id`, FK `collection_run_id` | History coverage, reported event count and endpoint end time |
| `bid_events` | One row per retained source event, PK `bid_key`, FK `collection_run_id` and UQ `(lot_id, bid_sequence)` after validating the source key | Event time, public displayed price, and event metadata |
| `lot_checkpoint_features` | One row per `(lot_id, checkpoint_id)` within a feature build | Reconstructed auction state at a defined prediction time |

## 2. Consolidate and normalize

Use positive integer source IDs where validated and TEXT for identifiers such as lot number and UPC. Keep leading zeros. Parse nullable booleans via an explicit accepted-token mapping and enforce 0/1. Preserve NULL and flag unrecognized values. Validate counts and durations as nonnegative integers where their semantics support it. Normalize offset-bearing timestamps to fixed-width UTC text with a consistent fractional precision sufficient for the source. For naive timestamps require a documented source zone before conversion. Keep calendar dates as dates. Flag malformed values and preserve the source reference. Required invalid keys block the affected record or the build according to the reconciliation gate below.

Use **integer cents for all stored monetary amounts**, including bids. This resolves the old dictionary's mix of cents and dollars. Parse with Decimal from source text and use an explicit nearest-cent rule (half up) for validated reference prices. Inspect residual precision to distinguish floating point artifacts from genuine fractions. Flag questionable precision and verify bid increments separately. User-facing rounding belongs in the prediction output.
