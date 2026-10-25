from datetime import date, datetime, timezone
from typing import Any

import scrapy
from scrapy.exceptions import CloseSpider
from scrapy.http import TextResponse

from macbid_scraper.items import AuctionRecordItem

def current_utc_timestamp() -> str:
    """Return the current UTC time in ISO 8601 format."""

    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )

class MacbidIncrementalSpider(scrapy.Spider):
    """Collect one known auction through Endpoint 1."""

    name = "macbid_incremental"

    allowed_domains = [
        "api.macdiscount.com",
    ]

    auction_number = "HEA2602-01-A1"

    start_urls = [
        (
            "https://api.macdiscount.com"
            "/auctions/HEA2602-01-A1"
            "?getItems=0"
        ),
    ]

    # These attributes describe the authorized scope of this
    # particular collection run. The pipeline uses them when
    # creating the collection_runs row.
    start_date = date(2026, 2, 1)
    end_date = date(2026, 2, 1)
    target_building_ids = {24}

    def parse(
        self,
        response: TextResponse,
    ):
        """Convert the Endpoint 1 response into an auction Item."""

        response_data: Any = response.json()

        if not isinstance(response_data, dict):
            raise CloseSpider(
                reason="unexpected_auction_response"
            )

        returned_auction_number = response_data.get(
            "auction_number"
        )

        if returned_auction_number != self.auction_number:
            raise CloseSpider(
                reason="auction_number_mismatch"
            )

        building_id = response_data.get("building_id")

        if building_id not in self.target_building_ids:
            raise CloseSpider(
                reason="auction_outside_building_scope"
            )

        collected_at = current_utc_timestamp()

        yield AuctionRecordItem(
            response_collected_at_utc=collected_at,
            auction_id=response_data.get("id"),
            auction_number=returned_auction_number,
            opening_date_source=response_data.get(
                "opening_date"
            ),
            closing_date_source=response_data.get(
                "closing_date"
            ),
            pickup_date_source=response_data.get(
                "pickup_date"
            ),
            abandon_date_source=response_data.get(
                "abandon_date"
            ),
            date_launched_source=response_data.get(
                "date_launched"
            ),
            location_id=response_data.get("location_id"),
            building_id=building_id,
            location_name=response_data.get(
                "location_name"
            ),
            auction_type_id=response_data.get(
                "auction_type_id"
            ),
            allow_transfers_source=response_data.get(
                "allow_transfers"
            ),
            free_transfers_source=response_data.get(
                "free_transfers"
            ),
            online_only_source=response_data.get(
                "online_only"
            ),
            members_only_source=response_data.get(
                "members_only"
            ),
            non_taxable_source=response_data.get(
                "non_taxable"
            ),
            immediate_settle_source=response_data.get(
                "immediate_settle"
            ),
            stagger_close_seconds=response_data.get(
                "stagger_close_seconds"
            ),
            extension_window_seconds=response_data.get(
                "extension_window_seconds"
            ),
            time_extension_seconds=response_data.get(
                "time_extension_seconds"
            ),
            lot_fee_override_source=response_data.get(
                "lot_fee_override"
            ),
            buyers_premium_override_source=response_data.get(
                "buyers_premium_override"
            ),
            total_lots_source=response_data.get(
                "total_lots"
            ),
        )