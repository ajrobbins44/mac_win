import logging

from datetime import date
from types import SimpleNamespace
from sqlalchemy import func, select

from database.connection import (
    create_staging_engine,
)
from database.staging_tables import (
    collection_runs,
    staging_auctions,
    staging_bid_events,
    staging_lot_bid_histories,
    staging_lot_details,
    staging_lot_summaries,
)

from macbid_scraper.items import (
    AuctionRecordItem,
    LotBidHistoryItem,
    LotDetailItem,
    LotSummaryItem,
    SingleBidItem,
)

from macbid_scraper.pipelines import (
    StagingSQLitePipeline,
)

class FakeStats:
    """Provide a simple stats object for testing."""

    def get_value(self, key):
        if key == "finish_reason":
            return "finished"

        return None

def make_fake_spider():

    # Use a basic object to make the fake spider
    return SimpleNamespace(
        start_date=date(2026, 2, 1),
        end_date=date(2026, 2, 1),
        target_building_ids={24},

        logger=logging.getLogger(
            "staging-pipeline-test"
        ),

        # A simple imitation of a spider's crawler and stats attributes
        crawler=SimpleNamespace(
            stats=FakeStats()
        ),
    )

def count_rows(connection, table) -> int:

    statement = (
        select(func.count())
        .select_from(table)
    )

    result = connection.scalar(statement)
    if result is None:
        raise RuntimeError(f"Failed to count rows in table {table.name}")

    return int(result)

def test_staging_pipeline_stores_each_item_type(
    tmp_path,
):
    """Confirm that every Item reaches its staging table."""

    db_path = (tmp_path / "test_staging.sqlite3")

    pipeline = StagingSQLitePipeline(
        database_path=db_path,
        scraper_version="test",
        schema_version="test",
    )

    spider = make_fake_spider()
    pipeline.open_spider(spider)

    collected_at = (
        "2026-10-23T20:00:00.000Z"
    )

    auction_items = [
        AuctionRecordItem(
            response_collected_at_utc=collected_at,
            auction_id=71841,
            auction_number="HEA2602-01-A1",
            opening_date_source="2026-01-23T03:00:00.000Z",
            closing_date_source="2026-02-01T22:00:00.000Z",
            pickup_date_source="Wednesday (02/04)",
            abandon_date_source="2026-02-04T05:00:00.000Z",
            date_launched_source="2026-01-23T21:35:58.000Z",
            location_id=54,
            building_id=24,
            location_name="Henderson - A",
            auction_type_id=1,
            allow_transfers_source=1,
            free_transfers_source=0,
            online_only_source=0,
            members_only_source=0,
            non_taxable_source=0,
            immediate_settle_source=0,
            stagger_close_seconds=7,
            extension_window_seconds=120,
            time_extension_seconds=120,
            lot_fee_override_source=3,
            buyers_premium_override_source=None,
            total_lots_source=None,
        ),
        AuctionRecordItem(
            response_collected_at_utc=collected_at,
            auction_id=92473,
            auction_number="HEA2609-01-A2",
            opening_date_source="2026-08-28T03:00:00.000Z",
            closing_date_source="2026-09-01T22:00:00.000Z",
            pickup_date_source="Friday (09/04)",
            abandon_date_source="2026-09-04T00:00:00.000Z",
            date_launched_source="2026-08-28T20:35:30.000Z",
            location_id=54,
            building_id=24,
            location_name="Henderson - A",
            auction_type_id=1,
            allow_transfers_source=1,
            free_transfers_source=1,
            online_only_source=0,
            members_only_source=0,
            non_taxable_source=0,
            immediate_settle_source=0,
            stagger_close_seconds=7,
            extension_window_seconds=120,
            time_extension_seconds=120,
            lot_fee_override_source=3,
            buyers_premium_override_source=None,
            total_lots_source=None,
        ),
    ]

    summary_items = [
        LotSummaryItem(
            response_collected_at_utc=collected_at,
            lot_id=49027749,
            auction_id=71841,
            lot_number="2054M",
            inventory_id=66692769,
            product_upc="B0CQRKWS2R",
            date_created_source="2026-01-21T14:49:16.000Z",
            closed_date_source="2026-02-02T00:23:38.000Z",
            expected_close_date_source=(
                "2026-02-02T00:23:38.000Z"
            ),
            current_location_id=54,
            is_transferable_source=1,
            is_shippable_source=0,
            is_partial_source=0,
            total_bids_source=6,
            winning_bid_amount_source=5,
            unique_bidders_source=4,
            product_name="Rose Home Fashion Area Rug",
            dimensions_text="8X10",
            quantity_source=0,
            is_pallet_source=0,
            retail_price_source=104.99,
            condition_name="OPEN BOX",
            category_name="Rugs",
        ),
        LotSummaryItem(
            response_collected_at_utc=collected_at,
            lot_id=62499568,
            auction_id=92473,
            lot_number="5021F",
            inventory_id=85860806,
            product_upc="B0FG782TFG",
            date_created_source="2026-08-19T18:46:40.000Z",
            closed_date_source="2026-09-01T21:57:39.000Z",
            expected_close_date_source=(
                "2026-09-01T22:57:39.000Z"
            ),
            current_location_id=54,
            is_transferable_source=1,
            is_shippable_source=0,
            is_partial_source=0,
            total_bids_source=2,
            winning_bid_amount_source=2,
            unique_bidders_source=2,
            product_name="Jivifao Kids Gymnastics Bar",
            dimensions_text="\u200e41 x 14.5 x 7 inches",
            quantity_source=0,
            is_pallet_source=0,
            shipping_height_source=None,
            shipping_width_source=None,
            shipping_length_source=None,
            shipping_weight_source=None,
            case_packed_qty_source=None,
            retail_price_source=139.99,
            condition_name="LIKE NEW",

            # Endpoint 2 returned a null category.
            category_name=None,
        ),
    ]

    detail_items = [
        LotDetailItem(
            response_collected_at_utc=collected_at,
            lot_id=49027749,
            auction_id=71841,
            lot_number="2054M",
            product_id=17565454,
            auction_type_source="standard",
            instant_win_price_source=84,
            buyers_assurance_cost_source=7,
            product_model=None,
            size_text=None,
            box_count_source=1,
            is_tested_source=0,
            lot_status_source="PICKED UP",
            has_update=0,
            has_partial_note=0,
            has_tested_note=0,
            has_damage_note=0,
            has_primary_image=1,
            detail_image_count=2,
            total_observed_image_count=3,
            inventory_id=66692769,
            product_upc="B0CQRKWS2R",
            date_created_source="2026-01-21T14:49:16.000Z",
            closed_date_source="2026-02-02T00:23:38.000Z",
            expected_close_date_source=(
                "2026-02-02T00:23:38.000Z"
            ),
            current_location_id=54,
            is_transferable_source=1,
            is_shippable_source=0,
            is_partial_source=0,
            total_bids_source=6,
            winning_bid_amount_source=5,
            unique_bidders_source=4,
            product_name="Rose Home Fashion Area Rug",
            dimensions_text="8X10",
            retail_price_source=104.99,
            condition_name="OPEN BOX",
            category_name="Rugs",
        ),
        LotDetailItem(
            response_collected_at_utc=collected_at,
            lot_id=62499568,
            auction_id=92473,
            lot_number="5021F",
            product_id=46823419,
            auction_type_source="standard",
            instant_win_price_source=29,
            buyers_assurance_cost_source=7,
            product_model=None,
            size_text=None,
            box_count_source=1,
            is_tested_source=0,
            lot_status_source="PICKED UP",
            has_update=0,
            has_partial_note=0,
            has_tested_note=0,
            has_damage_note=0,
            has_primary_image=1,
            detail_image_count=0,
            total_observed_image_count=1,
            inventory_id=85860806,
            product_upc="B0FG782TFG",
            date_created_source="2026-08-19T18:46:40.000Z",
            closed_date_source="2026-09-01T21:57:39.000Z",
            expected_close_date_source=(
                "2026-09-01T22:57:39.000Z"
            ),
            current_location_id=54,
            is_transferable_source=1,
            is_shippable_source=0,
            is_partial_source=0,
            total_bids_source=2,
            winning_bid_amount_source=2,
            unique_bidders_source=2,
            product_name="Jivifao Kids Gymnastics Bar",
            dimensions_text="\u200e41 x 14.5 x 7 inches",
            retail_price_source=139.99,
            condition_name="LIKE NEW",

            # Endpoint 3 supplied a category even though
            # Endpoint 2 returned null.
            category_name="Sports & Outdoors",
        ),
    ]

    history_items = [
        LotBidHistoryItem(
            response_collected_at_utc=collected_at,
            lot_id=49027749,
            observed_bid_record_count=1,
        ),
        LotBidHistoryItem(
            response_collected_at_utc=collected_at,
            lot_id=62499568,
            observed_bid_record_count=2,
        ),
    ]

    bid_items = [
        SingleBidItem(
            response_collected_at_utc=collected_at,
            bid_key="49027749:1",
            lot_id=49027749,
            bid_sequence=1,
            bid_amount_source=5,
            displayed_bid_source=5,
            bid_time_source="2026-02-02T05:21:27.602Z",
            lot_end_time_source="2026-02-02T05:23:38.000Z",
            is_matched_proxy=0,
            bid_type="manual",
            cumulative_unique_bidder_count=1,
        ),
        SingleBidItem(
            response_collected_at_utc=collected_at,
            bid_key="62499568:1",
            lot_id=62499568,
            bid_sequence=1,
            bid_amount_source=1,
            displayed_bid_source=1,
            bid_time_source="2026-09-02T02:26:15.752Z",
            lot_end_time_source="2026-09-02T02:57:39.000Z",
            is_matched_proxy=0,
            bid_type="manual",
            cumulative_unique_bidder_count=1,
        ),
        SingleBidItem(
            response_collected_at_utc=collected_at,
            bid_key="62499568:2",
            lot_id=62499568,
            bid_sequence=2,
            bid_amount_source=2,
            displayed_bid_source=2,
            bid_time_source="2026-09-02T02:52:31.515Z",
            lot_end_time_source="2026-09-02T02:57:39.000Z",
            is_matched_proxy=0,
            bid_type="manual",
            cumulative_unique_bidder_count=2,
        ),
    ]

    # Flatten the per-type lists into the order in which the
    # pipeline will receive them.
    items = [
        *auction_items,
        *summary_items,
        *detail_items,
        *history_items,
        *bid_items,
    ]

    # Process every Item twice. The second pass simulates duplicate
    # Scrapy output and tests ON CONFLICT DO NOTHING.
    for _ in range(2):
        for item in items:
            returned_item = pipeline.process_item(item, spider)

            assert returned_item is item

    # Mark fake run completed and release its engine
    pipeline.close_spider(spider)

    # Reopen the database for read-only verification
    verification_engine = create_staging_engine(db_path)

    with verification_engine.connect() as connection:
        assert count_rows(
            connection,
            collection_runs,
        ) == 1

        assert count_rows(
            connection,
            staging_auctions,
        ) == len(auction_items)

        assert count_rows(
            connection,
            staging_lot_summaries,
        ) == len(summary_items)

        assert count_rows(
            connection,
            staging_lot_details,
        ) == len(detail_items)

        assert count_rows(
            connection,
            staging_lot_bid_histories,
        ) == len(history_items)

        assert count_rows(
            connection,
            staging_bid_events,
        ) == len(bid_items)

        run_status = connection.scalar(
            select(collection_runs.c.status)
        )

        assert run_status == "completed"

        stored_auction_numbers = set(
            connection.execute(
                select(
                    staging_auctions.c.auction_number
                )
            ).scalars()
        )

        assert stored_auction_numbers == {
            "HEA2602-01-A1",
            "HEA2609-01-A2",
        }

        stored_product_names = set(
            connection.execute(
                select(
                    staging_lot_details.c.product_name
                )
            ).scalars()
        )

        assert stored_product_names == {
            "Rose Home Fashion Area Rug",
            "Jivifao Kids Gymnastics Bar",
        }

    verification_engine.dispose()