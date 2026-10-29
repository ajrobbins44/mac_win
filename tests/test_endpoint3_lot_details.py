from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock
from typing import cast

import pytest

from scrapy.exceptions import CloseSpider
from scrapy.crawler import Crawler
from scrapy.settings import Settings

from macbid_scraper.spiders.macbid_historical_auctions import (
    MacbidHistoricalAuctionsSpider,
)

class FakeStats:
    """Provide a simple stats object for testing."""

    def __init__(self):
        self.values: dict[str, object] = {
            "finish_reason": "finished"
        }

    def get_value(
        self,
        key: str,
        default=None,
    ):
        return self.values.get(key, default)

    def set_value(
        self,
        key: str,
        value: object,
    ):
        self.values[key] = value

    def inc_value(
        self,
        key: str,
        count: int = 1,
    ):
        current_value = self.values.get(key, 0)
        if not isinstance(current_value, int):
            current_value = 0
        self.values[key] = current_value + count

def make_test_spider():

    test_settings = Settings(
        {
            "ROBOTSTXT_OBEY": True,
            "USER_AGENT": "MacWin test crawler",
            "CONCURRENT_REQUESTS": 1,
            "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
            "DOWNLOAD_DELAY": 1.0,
            "AUTOTHROTTLE_ENABLED": True,
            "AUTOTHROTTLE_START_DELAY": 1.0,
            "AUTOTHROTTLE_MAX_DELAY": 10.0,
            "RETRY_ENABLED": True,
            "RETRY_TIMES": 1,
            "HTTPCACHE_ENABLED": False,
            "HTTPPROXY_ENABLED": False,
            "JOBDIR": None,
        }
    )

    crawler_double = SimpleNamespace(
        settings=test_settings,
        stats=FakeStats(),

        # Spider.from_crawler() connects the spider's close
        # handler to crawler.signals.
        signals=MagicMock(),
    )

    crawler = cast(
        Crawler,
        crawler_double,
    )

    return MacbidHistoricalAuctionsSpider.from_crawler(
        crawler
    )

@pytest.fixture
def endpoint3_response():
    return {
        "product_id": 17565454,
        "id": 49027749,
        "auction_type": "standard",
        "auction_id": 71841,
        "closed_date": (
            "2026-02-02T00:23:38.000Z"
        ),
        "expected_close_date": (
            "2026-02-02T00:23:38.000Z"
        ),
        "instant_win_price": 84,
        "buyers_assurance_cost": 7,
        "current_location_id": 54,
        "inventory_id": 66692769,
        "update_text": None,
        "date_created": (
            "2026-01-21T14:49:16.000Z"
        ),
        "lot_number": "2054M",
        "product_name": (
            "Test Fixture Area Rug"
        ),
        "is_transferrable": 1,
        "total_bids": 6,
        "winning_bid_amount": 5,
        "unique_bidders": 4,
        "lot_status": "PICKED UP",
        "description": (
            "  Fabricated test description.  "
        ),
        "size": None,
        "is_shippable": 0,
        "model": None,
        "dimensions": "8X10",
        "is_partial": 0,
        "partial_note": "",
        "is_tested": 0,
        "tested_note": "Powers on.",
        "damaged_note": "Minor cosmetic damage.",
        "upc": "B0CQRKWS2R",
        "boxes": 1,
        "category_name": "Rugs",
        "retail_price": 104.99,
        "condition_name": "OPEN BOX",
        "image_url": (
            "https://example.test/primary.webp"
        ),
        "images": [
            {
                "image_url": (
                    "https://example.test/detail1.jpg"
                ),
            },
            {
                "image_url": (
                    "https://example.test/detail2.jpg"
                ),
            },
        ],
        "auction": {
            "id": 71841,
            "auction_number": "HEA2602-01-A1",
        },
    }

# Test the endpoint 3 request
def test_make_lot_detail_request():
    spider = make_test_spider()

    request = spider.make_lot_detail_request(
        auction_number="HEA2602-01-A1",
        auction_id=71841,
        lot_number="2054M",
        lot_id=49027749,
    )

    assert request.url == (
        "https://api.macdiscount.com/"
        "auction/HEA2602-01-A1/lot/2054M"
    )

    assert request.callback == (
        spider.parse_lot_detail
    )

    assert request.errback == spider.handle_error

    assert request.cb_kwargs == {
        "expected_auction_number": (
            "HEA2602-01-A1"
        ),
        "expected_auction_id": 71841,
        "expected_lot_number": "2054M",
        "expected_lot_id": 49027749,
    }

def test_build_lot_detail_item(
    endpoint3_response,
):
    spider = make_test_spider()

    item = spider.build_lot_detail_item(
        response_data=endpoint3_response,
        expected_auction_number=(
            "HEA2602-01-A1"
        ),
        expected_auction_id=71841,
        expected_lot_number="2054M",
        expected_lot_id=49027749,
        response_collected_at_utc=(
            "2026-10-28T20:00:00.000Z"
        ),
    )

    assert item["lot_id"] == 49027749
    assert item["auction_id"] == 71841
    assert item["lot_number"] == "2054M"
    assert item["product_id"] == 17565454
    assert item["product_upc"] == "B0CQRKWS2R"
    assert item["description_source"] == (
    "  Fabricated test description.  "
    )

    assert item["update_text_source"] is None
    assert item["partial_note_source"] == ""
    assert item["tested_note_source"] == (
        "Powers on."
    )
    assert item["damaged_note_source"] == (
        "Minor cosmetic damage."
)

def test_build_lot_detail_without_images(
    endpoint3_response,
):
    spider = make_test_spider()
    response_data = deepcopy(endpoint3_response)

    response_data["image_url"] = None
    response_data["images"] = []

    item = spider.build_lot_detail_item(
        response_data=response_data,
        expected_auction_number=(
            "HEA2602-01-A1"
        ),
        expected_auction_id=71841,
        expected_lot_number="2054M",
        expected_lot_id=49027749,
        response_collected_at_utc=(
            "2026-10-28T20:00:00.000Z"
        ),
    )

    assert item["has_primary_image"] == 0
    assert item["detail_image_count"] == 0
    assert item["total_observed_image_count"] == 0

@pytest.mark.parametrize(
    (
        "field_name",
        "incorrect_value",
        "expected_reason",
    ),
    [
        (
            "id",
            99999999,
            "ep3_lot_detail_lot_id_mismatch",
        ),
        (
            "auction_id",
            99999,
            "ep3_lot_detail_auction_id_mismatch",
        ),
        (
            "lot_number",
            "WRONG",
            "ep3_lot_detail_lot_number_mismatch",
        ),
    ],
)

def test_build_lot_detail_rejects_mismatches(
    endpoint3_response,
    field_name,
    incorrect_value,
    expected_reason,
):
    spider = make_test_spider()
    response_data = deepcopy(endpoint3_response)

    response_data[field_name] = incorrect_value

    with pytest.raises(CloseSpider) as exception:
        spider.build_lot_detail_item(
            response_data=response_data,
            expected_auction_number=(
                "HEA2602-01-A1"
            ),
            expected_auction_id=71841,
            expected_lot_number="2054M",
            expected_lot_id=49027749,
            response_collected_at_utc=(
                "2026-10-28T20:00:00.000Z"
            ),
        )

    assert exception.value.reason == expected_reason

def test_build_lot_detail_rejects_invalid_text(
    endpoint3_response,
):
    spider = make_test_spider()
    response_data = deepcopy(endpoint3_response)

    response_data["description"] = 12345

    with pytest.raises(CloseSpider) as exception:
        spider.build_lot_detail_item(
            response_data=response_data,
            expected_auction_number=(
                "HEA2602-01-A1"
            ),
            expected_auction_id=71841,
            expected_lot_number="2054M",
            expected_lot_id=49027749,
            response_collected_at_utc=(
                "2026-10-28T20:00:00.000Z"
            ),
        )

    assert exception.value.reason == (
    "ep3_lot_detail_invalid_source_text"
)