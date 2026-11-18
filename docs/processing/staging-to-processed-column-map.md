# Staging to Processed Column Map

Remember to add verification vs validation distinction

## Collection runs

| Staging source | Processed destination | Decision | Implementation | Rule |
|---|---|---|---|---|
| `collection_runs.collection_run_id` | `collection_runs.source_collection_run_id` | Copy | Verified | Preserve the run ID from the staging file. Together with `source_db`, it identifies the original run. |
| No staging column | `collection_runs.collection_run_id` | Generate | Verified | SQLite assigns the processed primary key. Use it for foreign keys in processed tables. |
| No staging column | `collection_runs.source_db` | Generate | Verified | Use the input SQLite filename. |
| `collection_runs.started_at_utc` | `collection_runs.request_started_at_utc` | Copy after validation | Validated | Validate the UTC timestamp format before inserting. This records when the collection run began. |
| `collection_runs.ended_at_utc` | `collection_runs.request_ended_at_utc` | Copy after validation | Validated | Preserve `NULL` if no end time was recorded. Otherwise, validate the UTC format and check that the end is at or after the start. |
| `collection_runs.target_start_date` | `collection_runs.target_start_date` | Copy after validation | Validated | Validate the calendar date as `YYYY-MM-DD`. |
| `collection_runs.target_end_date` | `collection_runs.target_end_date` | Copy or correct | Validated | Validate the calendar date and date order. Apply the documented January scope correction to `2026-01-31` in processed. The original `2026-02-01` in staging records what the crawler used. |
| `collection_runs.target_building_ids` | — | Omit | — | The intended crawl scope is available in staging. Use `auctions.building_id` for the building recorded for each auction. |
| `collection_runs.scraper_version` | — | Omit | — | The collector version is available through the staging run reference. |
| `collection_runs.schema_version` | — | Omit | — | This describes the source staging schema and is available through the staging run reference. |
| `collection_runs.status` | `collection_runs.status` | Copy | Verify | Preserve the collector’s recorded run status. |
| `collection_runs.status_reason` | `collection_runs.status_reason` | Copy | Verify | Preserve the recorded reason, including `NULL` when no reason was recorded. |


| `staging_lot_summaries.category_name` + `staging_lot_details.category_name` | `auction_lots.category_name` | Consolidate | Planned | Trim both values and use detail first, with summary fallback. |
| No direct staging column | `auctions.observed_lot_count` *(query or view)* | Derive | Planned | Count consolidated `auction_lots` rows per auction. |