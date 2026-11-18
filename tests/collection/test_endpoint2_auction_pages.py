import json
from copy import deepcopy
from typing import Any

import pytest
from scrapy.exceptions import CloseSpider
from scrapy.http import Request, TextResponse

from macbid_scraper.items import LotSummaryItem

AUCTION_ID = 71841
AUCTION_NUMBER = "HEA2602-01-A1"
COLLECTED_AT = (
    "2026-10-29T20:00:00.000Z"
)

@pytest.fixture
def endpoint2_response_data() -> dict[str, Any]:
    """Return a fabricated Endpoint 2 response with two lots."""

    return {
        "id": AUCTION_ID,
        "auction_number": AUCTION_NUMBER,
        "items": [
            {
                "id": 49027749,
                "auction_id": AUCTION_ID,
                "lot_number": "2054M",
                "inventory_id": 66692769,
                "upc": "B0CQRKWS2R",
                "date_created": (
                    "2026-01-21T14:49:16.000Z"
                ),
                "closed_date": (
                    "2026-02-02T00:23:38.000Z"
                ),
                "expected_close_date": (
                    "2026-02-02T00:23:38.000Z"
                ),
                "current_location_id": 54,
                "is_transferrable": 1,
                "is_shippable": 0,
                "is_partial": 0,
                "total_bids": 6,
                "winning_bid_amount": 5,
                "unique_bidders": 4,
                "product_name": (
                    "Test Fixture Area Rug"
                ),
                "dimensions": "8X10",
                "quantity": 1,
                "is_pallet": 0,
                "shipping_height": None,
                "shipping_width": None,
                "shipping_length": None,
                "shipping_weight": None,
                "case_packed_qty": None,
                "retail_price": 104.99,
                "condition_name": "OPEN BOX",
                "category": "Rugs",
            },
            {
                "id": 49027750,
                "auction_id": AUCTION_ID,
                "lot_number": "2055M",
                "inventory_id": 66692770,
                "upc": "TEST-SECOND-UPC",
                "date_created": (
                    "2026-01-21T14:50:00.000Z"
                ),
                "closed_date": (
                    "2026-02-02T00:23:45.000Z"
                ),
                "expected_close_date": (
                    "2026-02-02T00:23:45.000Z"
                ),
                "current_location_id": 54,
                "is_transferrable": 1,
                "is_shippable": 0,
                "is_partial": 0,
                "total_bids": 3,
                "winning_bid_amount": 3,
                "unique_bidders": 2,
                "product_name": (
                    "Second Test Product"
                ),
                "dimensions": None,
                "quantity": 1,
                "is_pallet": 0,
                "shipping_height": None,
                "shipping_width": None,
                "shipping_length": None,
                "shipping_weight": None,
                "case_packed_qty": None,
                "retail_price": 49.99,
                "condition_name": "NEW",
                "category": "Test Category",
            },
        ],
    }

def make_endpoint2_response(
    response_data: dict[str, Any],
    *,
    page_number: int = 1,
    page_size: int = 100,
) -> TextResponse:
    """Wrap fabricated JSON in a Scrapy TextResponse."""

    url = (
        "https://api.macdiscount.com/"
        f"auctions/{AUCTION_ID}"
        f"?pg={page_number}&ppg={page_size}"
    )

    request = Request(url=url)

    return TextResponse(
        url=url,
        status=200,
        body=json.dumps(
            response_data
        ).encode("utf-8"),
        encoding="utf-8",
        request=request,
    )

def test_make_auction_page_request(
    historical_spider,
):
    """Confirm that Endpoint 2 requests are configured correctly."""

    historical_spider.auction_page_size = 100

    request = (
        historical_spider.make_auction_page_request(
            auction_number=AUCTION_NUMBER,
            auction_id=AUCTION_ID,
            page_number=1,
        )
    )

    assert request.url == (
        "https://api.macdiscount.com/"
        "auctions/71841?pg=1&ppg=100"
    )

    assert request.cb_kwargs == {
        "auction_number": AUCTION_NUMBER,
        "auction_id": AUCTION_ID,
        "page_number": 1,
    }

    assert request.callback == (
        historical_spider.parse_auction_page
    )

    assert request.errback == (
        historical_spider.handle_error
    )

def test_build_lot_summary_item(
    historical_spider,
    endpoint2_response_data,
):
    """Confirm that one items[] object becomes a summary Item."""

    lot_data = endpoint2_response_data[
        "items"
    ][0]

    item = (
        historical_spider.build_lot_summary_item(
            lot_data=lot_data,
            expected_auction_id=AUCTION_ID,
            response_collected_at_utc=(
                COLLECTED_AT
            ),
        )
    )

    assert isinstance(item, LotSummaryItem)

    assert item["lot_id"] == 49027749
    assert item["auction_id"] == AUCTION_ID
    assert item["lot_number"] == "2054M"

    assert item["inventory_id"] == 66692769
    assert item["product_upc"] == "B0CQRKWS2R"

    assert item["product_name"] == (
        "Test Fixture Area Rug"
    )

    assert item["is_transferable_source"] == 1
    assert item["total_bids_source"] == 6
    assert item["winning_bid_amount_source"] == 5
    assert item["unique_bidders_source"] == 4
    assert item["retail_price_source"] == 104.99
    assert item["category_name"] == "Rugs"

    assert (
        item["response_collected_at_utc"]
        == COLLECTED_AT
    )

def test_parse_auction_page_schedules_downstream_requests(
    historical_spider,
    endpoint2_response_data,
):
    """Confirm that every lot schedules Endpoints 3 and 4."""

    historical_spider.auction_page_size = 100
    historical_spider.max_pages_per_auction = 10

    response = make_endpoint2_response(
        endpoint2_response_data,
        page_number=1,
        page_size=100,
    )

    results = list(
        historical_spider.parse_auction_page(
            response=response,
            auction_number=AUCTION_NUMBER,
            auction_id=AUCTION_ID,
            page_number=1,
        )
    )

    summary_items = [
        result
        for result in results
        if isinstance(result, LotSummaryItem)
    ]

    requests = [
        result
        for result in results
        if isinstance(result, Request)
    ]

    lot_detail_requests = [
        request
        for request in requests
        if (
            request.callback
            == historical_spider.parse_lot_detail
        )
    ]

    bid_history_requests = [
        request
        for request in requests
        if (
            request.callback
            == historical_spider.parse_bid_history
        )
    ]

    next_page_requests = [
        request
        for request in requests
        if (
            request.callback
            == historical_spider.parse_auction_page
        )
    ]

    # Two source lots produce two summary Items.
    assert len(summary_items) == 2

    # Every lot schedules one Endpoint 3 request.
    assert len(lot_detail_requests) == 2

    # Every lot schedules one Endpoint 4 request.
    assert len(bid_history_requests) == 2

    # Two returned lots are fewer than page_size=100,
    # so this is the final Endpoint 2 page.
    assert next_page_requests == []

    assert {
        request.cb_kwargs["expected_lot_id"]
        for request in lot_detail_requests
    } == {
        49027749,
        49027750,
    }

    assert {
        request.cb_kwargs["expected_lot_id"]
        for request in bid_history_requests
    } == {
        49027749,
        49027750,
    }

def test_full_auction_page_schedules_next_page(
    historical_spider,
    endpoint2_response_data,
):
    """Confirm that a full Endpoint 2 page schedules another page."""

    historical_spider.auction_page_size = 2
    historical_spider.max_pages_per_auction = 10

    response = make_endpoint2_response(
        endpoint2_response_data,
        page_number=1,
        page_size=2,
    )

    results = list(
        historical_spider.parse_auction_page(
            response=response,
            auction_number=AUCTION_NUMBER,
            auction_id=AUCTION_ID,
            page_number=1,
        )
    )

    next_page_requests = [
        result
        for result in results
        if (
            isinstance(result, Request)
            and result.callback
            == historical_spider.parse_auction_page
        )
    ]

    assert len(next_page_requests) == 1

    next_page_request = next_page_requests[0]

    assert next_page_request.url == (
        "https://api.macdiscount.com/"
        "auctions/71841?pg=2&ppg=2"
    )

    assert next_page_request.cb_kwargs == {
        "auction_number": AUCTION_NUMBER,
        "auction_id": AUCTION_ID,
        "page_number": 2,
    }

def test_partial_auction_page_ends_pagination(
    historical_spider,
    endpoint2_response_data,
):
    """Confirm that a partial page does not schedule another page."""

    historical_spider.auction_page_size = 3
    historical_spider.max_pages_per_auction = 10

    response = make_endpoint2_response(
        endpoint2_response_data,
        page_number=2,
        page_size=3,
    )

    results = list(
        historical_spider.parse_auction_page(
            response=response,
            auction_number=AUCTION_NUMBER,
            auction_id=AUCTION_ID,
            page_number=2,
        )
    )

    next_page_requests = [
        result
        for result in results
        if (
            isinstance(result, Request)
            and result.callback
            == historical_spider.parse_auction_page
        )
    ]

    assert next_page_requests == []

@pytest.mark.parametrize(
    (
        "field_name",
        "incorrect_value",
    ),
    [
        (
            "id",
            99999999,
        ),
        (
            "auction_number",
            "WRONG-AUCTION-NUMBER",
        ),
    ],
)

def test_auction_page_rejects_identifier_mismatch(
    historical_spider,
    endpoint2_response_data,
    field_name,
    incorrect_value,
):
    """Confirm that the response belongs to the requested auction."""

    response_data = deepcopy(
        endpoint2_response_data
    )

    response_data[field_name] = incorrect_value

    response = make_endpoint2_response(
        response_data
    )

    with pytest.raises(CloseSpider) as exception:
        list(
            historical_spider.parse_auction_page(
                response=response,
                auction_number=AUCTION_NUMBER,
                auction_id=AUCTION_ID,
                page_number=1,
            )
        )

    assert exception.value.reason == (
        "ep2_auction_page_identifier_mismatch"
    )

def test_auction_page_rejects_missing_items_list(
    historical_spider,
    endpoint2_response_data,
):
    """Confirm that Endpoint 2 must return an items list."""

    response_data = deepcopy(
        endpoint2_response_data
    )

    response_data["items"] = None

    response = make_endpoint2_response(
        response_data
    )

    with pytest.raises(CloseSpider) as exception:
        list(
            historical_spider.parse_auction_page(
                response=response,
                auction_number=AUCTION_NUMBER,
                auction_id=AUCTION_ID,
                page_number=1,
            )
        )

    assert exception.value.reason == (
        "ep2_auction_page_missing_items"
    )