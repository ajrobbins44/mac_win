# Staging to Processed Column Map

Remember to add verification vs validation distinction

Notes to document later: response collection timestamps always in utc. All other timestamps converted to Henderson time.

## Collection runs

| Staging source | Processed destination | Decision | Implementation | Rule |
|---|---|---|---|---|
| No staging column | `collection_runs.collection_run_id` | Generate | Verified | SQLite assigns the processed primary key. Use it for foreign keys in processed tables. |
| `collection_runs.collection_run_id` | `collection_runs.source_collection_run_id` | Copy | Verified | Preserve the run ID from the staging file. Together with `source_db`, it identifies the original run. |
| No staging column | `collection_runs.source_db` | Generate | Verified | Use the input SQLite filename. Together with `source_collection_run_id`, it identifies the original run. |
| `collection_runs.started_at_utc` | `collection_runs.request_started_at_utc` | Copy after validation | Validated | Validate the UTC timestamp format before inserting. This records when the collection run began. |
| `collection_runs.ended_at_utc` | `collection_runs.request_ended_at_utc` | Copy after validation | Validated | Preserve `NULL` if no end time was recorded. Otherwise, validate the UTC format and check that the end is at or after the start. |
| `collection_runs.target_start_date` | `collection_runs.target_start_date` | Copy after validation | Validated | Validate the calendar date as `YYYY-MM-DD`. |
| `collection_runs.target_end_date` | `collection_runs.target_end_date` | Copy or correct | Validated | Validate the calendar date and date order. Apply the documented January scope correction to `2026-01-31` in processed. The original `2026-02-01` in staging records what the crawler used. |
| `collection_runs.target_building_ids` | — | Omit | — | The intended crawl scope is available in staging. Use `auctions.building_id` for the building recorded for each auction. |
| `collection_runs.scraper_version` | — | Omit | — | The collector version is available through the staging run reference. |
| `collection_runs.schema_version` | — | Omit | — | This describes the source staging schema and is available through the staging run reference. |
| `collection_runs.status` | `collection_runs.status` | Copy | Verify | Preserve the collector’s recorded run status. |
| `collection_runs.status_reason` | `collection_runs.status_reason` | Copy | Verify | Preserve the recorded reason, including `NULL` when no reason was recorded. |

## Auctions

| Staging source | Processed destination | Decision | Implementation | Rule |
|---|---|---|---|---|
| `staging_auctions.auction_id` | `auctions.auction_id` | Copy after validation | Planned | Preserve the positive integer auction ID. Exclude auctions outside the source file’s intended scope before importing. |
| `staging_auctions.auction_number` | `auctions.auction_number` | Copy after validation | Planned | Require nonempty text, trim surrounding whitespace, and enforce uniqueness. |
| `staging_auctions.collection_run_id` | `auctions.collection_run_id` | Remap | Planned | Use the current source file’s `run_id_map` to assign the corresponding processed collection-run ID. |
| `staging_auctions.response_collected_at_utc` | `auctions.response_collected_at_utc` | Copy after validation | Planned | Validate the UTC timestamp format before inserting. Preserve when the API response was collected. |
| `staging_auctions.opening_date_source` | `auctions.scheduled_open_at_local` | Normalize | Planned | Validate the source UTC timestamp and convert to Henderson time, retaining milliseconds and the numeric UTC offset. |
| `staging_auctions.closing_date_source` | `auctions.scheduled_close_at_local` | Normalize | Planned | Apply the same local-time conversion. Check that scheduled closing is at or after scheduled opening. |
| `staging_auctions.date_launched_source` | `auctions.launched_at_local` | Normalize | Planned | Validate the source UTC timestamp and convert to Henderson time, retaining milliseconds and the numeric UTC offset. |
| `staging_auctions.pickup_date_source` | — | Omit | — | Retain the display text in staging for reference when investigating deadline discrepancies. |
| `staging_auctions.abandon_date_source` | `auctions.pickup_deadline_at_local` | Normalize | Planned | Validate the source UTC timestamp and convert to Henderson time, preserving milliseconds and the numeric UTC offset. Use the source-reported deadline without calculating a pickup window from the closing date. |
| `staging_auctions.building_id` | `auctions.building_id` | Copy after validation | Planned | Require a positive integer and check membership in the linked staging collection run’s target building list. |
| `staging_auctions.location_id` | `auctions.location_id` | Copy after validation | Planned | Require a positive integer and check its observed mapping to building IDs across the collected databases. |
| `staging_auctions.location_name` | — | Omit | — | Use during the location-mapping audit. The name remains available in staging through the auction ID. |