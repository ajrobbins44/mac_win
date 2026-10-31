from copy import deepcopy
from typing import Any

import pytest
from scrapy.exceptions import CloseSpider

LOT_ID = 49027749

COLLECTED_AT = (
    "2026-10-29T20:00:00.000Z"
)

@pytest.fixture
def endpoint4_response() -> dict[str, Any]:
    """Return a fabricated successful Endpoint 4 response.

    The source bids are deliberately newest-first, matching the
    observed API behavior. Bidder 1 appears twice so the tests
    can verify the total unique-bidder calculation.
    """

    return {
        "bids": [
            {
                "lot_id": LOT_ID,
                "bid_amount": 3,
                "bid_time": (
                    "2026-02-02T03:00:00.000Z"
                ),
                "lot_end_time": (
                    "2026-02-02T05:00:00.000Z"
                ),
                "isMatchedProxy": False,
                "anonId": "Bidder 1",
                "displayedBid": 3,
                "bidType": "manual",
                "isCurrentUser": False,
                "isCurrentWinner": True,
            },
            {
                "lot_id": LOT_ID,
                "bid_amount": 2,
                "bid_time": (
                    "2026-02-02T02:00:00.000Z"
                ),
                "lot_end_time": (
                    "2026-02-02T05:00:00.000Z"
                ),
                "isMatchedProxy": False,
                "anonId": "Bidder 2",
                "displayedBid": 2,
                "bidType": "manual",
                "isCurrentUser": False,
                "isCurrentWinner": False,
            },
            {
                "lot_id": LOT_ID,
                "bid_amount": 1,
                "bid_time": (
                    "2026-02-02T01:00:00.000Z"
                ),
                "lot_end_time": (
                    "2026-02-02T05:00:00.000Z"
                ),
                "isMatchedProxy": False,
                "anonId": "Bidder 1",
                "displayedBid": 1,
                "bidType": "manual",
                "isCurrentUser": False,
                "isCurrentWinner": False,
            },
        ]
    }

def test_make_bid_history_request(
    historical_spider,
):
    """Confirm that Endpoint 4 requests are configured correctly."""

    request = (
        historical_spider.make_bid_history_request(
            lot_id=LOT_ID,
        )
    )

    assert request.url == (
        "https://api.macdiscount.com/"
        "auctions/lot/49027749/bid-history"
    )

    assert request.callback == (
        historical_spider.parse_bid_history
    )

    assert request.errback == (
        historical_spider.handle_error
    )

    assert request.cb_kwargs == {
        "expected_lot_id": LOT_ID,
    }

def test_build_bid_history_items(
    historical_spider,
    endpoint4_response,
):
    """Confirm that a valid history produces the expected Items."""

    history_item, bid_items = (
        historical_spider.build_bid_history_items(
            response_data=endpoint4_response,
            expected_lot_id=LOT_ID,
            response_collected_at_utc=(
                COLLECTED_AT
            ),
        )
    )

    source_bid_count = len(
        endpoint4_response["bids"]
    )

    # One history summary represents the requested lot.
    assert history_item["lot_id"] == LOT_ID

    assert (
        history_item[
            "response_collected_at_utc"
        ]
        == COLLECTED_AT
    )

    # All source bids were validated and converted.
    assert (
        history_item[
            "observed_bid_record_count"
        ]
        == source_bid_count
    )

    assert len(bid_items) == source_bid_count

    # Sequence values represent chronological order.
    assert [
        item["bid_sequence"]
        for item in bid_items
    ] == [1, 2, 3]

    assert [
        item["bid_time_source"]
        for item in bid_items
    ] == [
        "2026-02-02T01:00:00.000Z",
        "2026-02-02T02:00:00.000Z",
        "2026-02-02T03:00:00.000Z",
    ]

    # Bid amounts move from earliest to latest.
    assert [
        item["bid_amount_source"]
        for item in bid_items
    ] == [1, 2, 3]

    # Bidder 1, then Bidder 2, then Bidder 1 again.
    assert [
        item[
            "total_unique_bidder_count"
        ]
        for item in bid_items
    ] == [1, 2, 2]

    assert [
        item["bid_key"]
        for item in bid_items
    ] == [
        "49027749:1",
        "49027749:2",
        "49027749:3",
    ]

    # Every bid event carries the same collection timestamp.
    assert all(
        item["response_collected_at_utc"]
        == COLLECTED_AT
        for item in bid_items
    )

def test_bid_items_do_not_retain_anon_id(
    historical_spider,
    endpoint4_response,
):
    """Confirm that source bidder labels are not stored."""

    _, bid_items = (
        historical_spider.build_bid_history_items(
            response_data=endpoint4_response,
            expected_lot_id=LOT_ID,
            response_collected_at_utc=(
                COLLECTED_AT
            ),
        )
    )

    for bid_item in bid_items:
        stored_fields = dict(bid_item)

        assert "anonId" not in stored_fields
        assert "anon_id" not in stored_fields

def test_build_empty_bid_history(
    historical_spider,
):
    """Confirm that an empty bids array is a successful result."""

    history_item, bid_items = (
        historical_spider.build_bid_history_items(
            response_data={
                "bids": [],
            },
            expected_lot_id=LOT_ID,
            response_collected_at_utc=(
                COLLECTED_AT
            ),
        )
    )

    assert history_item["lot_id"] == LOT_ID

    assert (
        history_item[
            "response_collected_at_utc"
        ]
        == COLLECTED_AT
    )

    assert (
        history_item[
            "observed_bid_record_count"
        ]
        == 0
    )

    assert bid_items == []

def test_bid_history_rejects_invalid_bid_list(
    historical_spider,
):
    """Confirm that Endpoint 4 must return a bids list."""

    with pytest.raises(CloseSpider) as exception:
        historical_spider.build_bid_history_items(
            response_data={
                "bids": None,
            },
            expected_lot_id=LOT_ID,
            response_collected_at_utc=(
                COLLECTED_AT
            ),
        )

    assert exception.value.reason == (
        "ep4_bid_history_invalid_bid_list"
    )

def test_bid_history_rejects_lot_id_mismatch(
    historical_spider,
    endpoint4_response,
):
    """Confirm that every bid belongs to the requested lot."""

    response_data = deepcopy(
        endpoint4_response
    )

    response_data["bids"][0]["lot_id"] = (
        99999999
    )

    with pytest.raises(CloseSpider) as exception:
        historical_spider.build_bid_history_items(
            response_data=response_data,
            expected_lot_id=LOT_ID,
            response_collected_at_utc=(
                COLLECTED_AT
            ),
        )

    assert exception.value.reason == (
        "ep4_bid_history_lot_id_mismatch"
    )