from datetime import date, datetime, timezone
from typing import Any, cast
from itertools import islice
from urllib.parse import quote, urlencode
from pathlib import Path


from scrapy import Spider
from scrapy.exceptions import CloseSpider
from scrapy.http import TextResponse, Request, Response
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.python.failure import Failure

from macbid_scraper.items import (
    AuctionRecordItem, 
    LotSummaryItem, 
    LotDetailItem, 
    LotBidHistoryItem, 
    SingleBidItem
)

from scripts.generate_auction_candidates import (
    generate_auction_candidates,
)

from config import PROJECT_ROOT, BASE_URL

PATTERN_FILE = Path(
    PROJECT_ROOT,
    "data",
    "discovery",
    "auction_patterns",
    "pattern_behavior_batches1-3.csv"
)

def current_utc_timestamp() -> str:
    """Return the current UTC time in ISO 8601 format.
    Used to assign the response_collected_at_utc field.
    """

    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )

class MacbidIncrementalSpider(Spider):
    """Collect one known auction through Endpoint 1."""

    name = "macbid_incremental"

    allowed_domains = [
        BASE_URL.replace("https://", "")
    ]

    # Using a controlled, one-day scope
    start_date = date(2026, 2, 1)
    end_date = date(2026, 2, 1)

    # Henderson building only
    target_building_ids = {24}

    # Keep controlled crawl limited to 10 candidates
    candidate_limit = 1

    # Yield 100 lots per auction page
    auction_page_size = 100
    # Ensures an infinite loop doesn't occur 
    max_pages_per_auction = 100

    # ---------------------------------------------------------
    # START
    # ---------------------------------------------------------
    async def start(self):
        """Generate candidate auction numbers and yield Requests for them."""

        candidates = generate_auction_candidates(
            start_date=self.start_date,
            end_date=self.end_date,
            pattern_file=PATTERN_FILE,
            target_building_ids=self.target_building_ids,
        )

        limited_candidates = islice(candidates, self.candidate_limit)

        for candidate in limited_candidates:

            auction_number = candidate["auction_number"]
            encoded_auction_number = quote(auction_number, safe="")

            request_url = (
                f"{BASE_URL}/auctions/{encoded_auction_number}/?getItems=0"
            )

            self.crawler.stats.inc_value(
                "macbid/candidate_requests_generated"
            )

            yield Request(
                url=request_url,
                method="GET",
                callback=self.parse_candidate,
                errback=self.handle_error,
                cb_kwargs={
                    "candidate": candidate,
                },
                meta={
                    # A nonexistent generated candidate is an
                    # expected result, so allow its response to
                    # reach the callback.
                    "handle_httpstatus_list": [404],
                },
            )

    # ---------------------------------------------------------
    # REQUIRE_SUCCESSFUL_JSON_OBJECT
    # ---------------------------------------------------------
    def require_successful_json_object(
        self,
        response: Response,
        *,
        endpoint_name: str,
    ) -> dict[str, Any]:
        """Validate and decode a successful JSON-object response."""

        if response.status != 200:
            self.crawler.stats.inc_value(
                "macbid/unexpected_http_statuses"
            )

            self.logger.error(
                f"Unexpected HTTP status | "
                f"endpoint={endpoint_name} | "
                f"status={response.status} | "
                f"url={response.url}",
            )

            raise CloseSpider(
                reason=(
                    f"{endpoint_name}_http_"
                    f"{response.status}"
                )
            )
        
        # Must check that the response is a TextResponse before 
        # calling .json() on it.
        if not isinstance(response, TextResponse):
            self.crawler.stats.inc_value(
                "macbid/unexpected_response_types"
            )

            self.logger.error(
                f"Unexpected response type | "
                f"endpoint={endpoint_name} | "
                f"returned response={response!r} | "
                f"url={response.url}"
            )

            raise CloseSpider(
                reason=(
                    f"{endpoint_name}_"
                    "non_text_response"
                )
            )

        try:
            response_data = response.json()

        except ValueError as error:
            self.crawler.stats.inc_value(
                "macbid/invalid_json_responses"
            )

            self.logger.error(
                f"Invalid JSON response | "
                f"endpoint={endpoint_name} | "
                f"url={response.url}",
            )

            raise CloseSpider(
                reason=(
                    f"{endpoint_name}_invalid_json"
                )
            ) from error

        if not isinstance(response_data, dict):
            self.crawler.stats.inc_value(
                "macbid/unexpected_json_types"
            )

            self.logger.error(
                f"Unexpected JSON type | "
                f"endpoint={endpoint_name} | "
                f"returned response={response_data!r} | "
                f"url={response.url}"
            )

            raise CloseSpider(
                reason=(
                    f"{endpoint_name}_"
                    "unexpected_json_type"
                )
            )

        return response_data

    # ---------------------------------------------------------
    # PARSE_CANDIDATE
    # ---------------------------------------------------------
    def parse_candidate(
        self,
        response: Response,
        candidate: dict[str, Any],
    ):
        """Parse one candidate's Endpoint 1 response and, if successful,
        yield an AuctionRecordItem and schedule an Endpoint 2 request.
        """

        auction_number = candidate["auction_number"]

        if response.status == 404:

            self.crawler.stats.inc_value(
                "macbid/candidates_not_found"
            )

            self.logger.info(
                f"Candidate not found: {auction_number}"
            )

            return

        response_data = (
            self.require_successful_json_object(
                response,
                endpoint_name="ep1_auction_lookup",
            )
        )

        returned_auction_number = response_data.get(
            "auction_number"
        )

        if returned_auction_number != auction_number:
            self.crawler.stats.inc_value(
                "macbid/auction_number_mismatches"
            )
            self.logger.error(
                f"Auction number mismatch | "
                f"requested={auction_number} | "
                f"returned={returned_auction_number}"
            )
            raise CloseSpider(
                reason="ep1_auction_lookup_identifier_mismatch"
            )

        building_id = response_data.get("building_id")

        if building_id not in self.target_building_ids:
            self.crawler.stats.inc_value(
                "macbid/out_of_scope_auctions"
            )

            self.logger.warning(
                f"Candidate {auction_number} belongs to out-of-scope "
                f"building {building_id} and will not be stored."
            )

            return

        self.crawler.stats.inc_value(
            "macbid/candidate_found"
        )

        auction_id = response_data.get("id")

        if not isinstance(auction_id, int):
            self.logger.error(
                "Missing or invalid auction ID | "
                f"auction_number={auction_number} | "
                f"auction_id={auction_id}"
            )

            raise CloseSpider(
                reason="ep1_auction_lookup_invalid_auction_id"
            )

        # Send item to the pipeline
        yield AuctionRecordItem(
            response_collected_at_utc=current_utc_timestamp(),
            auction_id=auction_id,
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

        # Send Enpoint 2 request to Scrapy's scheduler
        yield self.make_auction_page_request(
            auction_number=auction_number,
            auction_id=auction_id,
            page_number=1,
        )
        
    # ---------------------------------------------------------
    # HANDLE_ERROR
    # ---------------------------------------------------------
    def handle_error(
        self,
        failure: Failure,
    ) -> None:
        """Handle a failed Endpoint 1 or Endpoint 2 request."""

        # First recover the Scrapy Request that failed
        request = getattr(
            failure, 
            "request", 
            None,
        )

        if not isinstance(request, Request):
            self.crawler.stats.inc_value(
                "macbid/failures_without_request"
            )

            self.logger.error(
                "A request failure did not contain "
                "its originating Scrapy Request: %s",
                failure.getErrorMessage(),
            )

            raise CloseSpider(
                reason="failure_without_request"
            )

        # Determine which endpoint produced the failure and 
        # log its auction information.

        callback_arguments = request.cb_kwargs
        candidate = callback_arguments.get(
            "candidate"
        )

        if isinstance(candidate, dict):

            endpoint_name = "ep1_auction_lookup"

            auction_number_value = candidate.get(
                "auction_number"
            )

            page_number = None

        else:
            # Endpoint 2 requests do not have a candidate dict, 
            # but they do have auction_number and page_number.
            endpoint_name = "ep2_auction_page"

            auction_number_value = callback_arguments.get(
                "auction_number"
            )
            page_number = callback_arguments.get(
                "page_number"
            )

        if isinstance(auction_number_value, str):
            auction_number = auction_number_value
        else:
            auction_number = "unknown"

        # Handle an HTTP response that Scrapy rejected
        if failure.check(HttpError):
            http_error = failure.value

            if not isinstance(http_error, HttpError):
                self.crawler.stats.inc_value(
                    "macbid/invalid_http_failures"
                )

                self.logger.error(
                    "Failure was identified as an HttpError "
                    "but did not contain an HttpError value | "
                    f"endpoint={endpoint_name} | url={request.url}"
                )

                raise CloseSpider(
                    reason="invalid_http_failure"
                )   

            response = http_error.response
            http_status = response.status

            self.crawler.stats.inc_value(
                f"macbid/http_status_{http_status}"
            )

            self.logger.error(
                "HTTP request failed | "
                f"endpoint={endpoint_name} | status={http_status} | "
                f"auction_number={auction_number} | page={page_number} | "
                f"url={request.url}"
            )

            if http_status in {403, 429}:
                raise CloseSpider(
                    reason=f"http_{http_status}"
                )

            raise CloseSpider(
                reason=f"{endpoint_name}_http_{http_status}"
            )

        # Handle a non-HTTP failure, such as a timeout or connection error
        self.crawler.stats.inc_value(
            "macbid/request_failures"
        )

        self.logger.error(
            "request failed without an HTTP response | "
            f"endpoint={endpoint_name} | "
            f"auction_number={auction_number} | "
            f"page_number={page_number!r} | "
            f"url={request.url}"
        )

    # ---------------------------------------------------------
    # MAKE_AUCTION_PAGE_REQUEST
    # ---------------------------------------------------------
    def make_auction_page_request(
        self,
        auction_number: str,
        auction_id: int,
        page_number: int,
    ) -> Request:
        """Return a Request for Endpoint 2, the auction page."""

        query_string = urlencode(
            {
                "pg": page_number,
                "ppg": self.auction_page_size,
            }
        )

        request_url = (
            f"{BASE_URL}/auctions/{auction_id}"
            f"?{query_string}"
        )

        return Request(
            url=request_url,
            method="GET",
            callback=self.parse_auction_page,
            errback=self.handle_error,
            cb_kwargs={
                "auction_number": auction_number,
                "auction_id": auction_id,
                "page_number": page_number,
            },
        )

    # ---------------------------------------------------------
    # PARSE_AUCTION_PAGE
    # ---------------------------------------------------------
    def parse_auction_page(
        self,
        response: Response,
        auction_number: str,
        auction_id: int,
        page_number: int,
    ):
        """Parse one Endpoint 2 page and yield one LotSummaryItem per lot, 
        or raise CloseSpider on error.
        """

        response_data = (
            self.require_successful_json_object(
                response,
                endpoint_name="ep2_auction_page",
            )
        )

        returned_auction_id = response_data.get("id")

        if returned_auction_id != auction_id:
            self.crawler.stats.inc_value(
                "macbid/auction_id_mismatches"
            )

            self.logger.error(
                f"Auction ID mismatch | "
                f"requested={auction_id} | "
                f"returned={returned_auction_id} | "
                f"auction_number={auction_number} | "
                f"page_number={page_number}"
            )

            raise CloseSpider(
                reason="ep2_auction_page_identifier_mismatch"
            )

        returned_auction_number = response_data.get(
            "auction_number"
        )

        if returned_auction_number != auction_number:
            self.crawler.stats.inc_value(
                "macbid/auction_number_mismatches"
            )

            self.logger.error(
                f"Auction number mismatch | "
                f"requested={auction_number} | "
                f"returned={returned_auction_number} | "
                f"page_number={page_number}"
            )

            raise CloseSpider(
                reason="ep2_auction_page_identifier_mismatch"
            )

        lots = response_data.get("items")

        if not isinstance(lots, list):
            self.crawler.stats.inc_value(
                "macbid/missing_items_lists"
            )

            self.logger.error(
                "Missing items list | "
                f"auction_number={auction_number} | "
                f"auction_id={auction_id} | page={page_number}"
            )

            raise CloseSpider(
                reason="ep2_auction_page_missing_items"
            )

        response_collected_at_utc = current_utc_timestamp()

        for lot_position, lot_data in enumerate(
            lots, 
            start=1
        ):
            if not isinstance(lot_data, dict):
                self.crawler.stats.inc_value(
                    "macbid/invalid_lot_data"
                )

                self.logger.error(
                    "Invalid lot object | "
                    f"auction_number={auction_number} | "
                    f"auction_id={auction_id} | "
                    f"page={page_number} | "
                    f"lot_position={lot_position}"
                )

                raise CloseSpider(
                    reason="ep2_auction_page_invalid_lot_object"
                )

            lot_summary_item = self.build_lot_summary_item(
                lot_data=lot_data,
                expected_auction_id=auction_id,
                response_collected_at_utc=response_collected_at_utc,
            )

            self.crawler.stats.inc_value(
                "macbid/lot_summary_items_yielded"
            )

            yield lot_summary_item

            # build_lot_summary_item() already validated that these
            # values are an int and a nonempty string.
            lot_id = cast(
                int,
                lot_summary_item["lot_id"],
            )

            lot_number = cast(
                str,
                lot_summary_item["lot_number"],
            )

            # Schedule Endpoint 3 for this lot.
            self.crawler.stats.inc_value(
                "macbid/lot_detail_requests_scheduled"
            )

            """
            self.logger.info(
                "Lot-detail request scheduled | "
                f"auction_number={auction_number} | "
                f"auction_id={auction_id} | "
                f"page_number={page_number} | "
                f"lot_position={lot_position} | "
                f"lot_number={lot_number} | "
                f"lot_id={lot_id}"
            )
            """

            yield self.make_lot_detail_request(
                auction_number=auction_number,
                auction_id=auction_id,
                lot_number=lot_number,
                lot_id=lot_id,
            )
                    

        """
        self.logger.info(
            "Auction page collected | "
            f"auction_number={auction_number} | "
            f"auction_id={auction_id} | "
            f"page={page_number} | "
            f"lots_returned={len(lots)}" 
        )
        """
        
        returned_lot_count = len(lots)

        if returned_lot_count < self.auction_page_size:
            self.logger.info(
                "Last auction page reached | "
                f"auction_number={auction_number} | "
                f"auction_id={auction_id} | "
                f"final page={page_number} | "
                f"lots on final page={returned_lot_count}"
            )

            self.crawler.stats.inc_value(
                "macbid/auctions_fully_paginated"
            )

            return

        if page_number >= self.max_pages_per_auction:
            self.crawler.stats.inc_value(
                "macbid/auction_page_limits_reached"
            )

            self.logger.error(
                "Maximum auction page limit reached | "
                f"auction_number={auction_number} | "
                f"auction_id={auction_id}"
            )

            raise CloseSpider(
                reason="ep2_auction_page_limit_reached"
            )
        
        next_page_number = page_number + 1

        yield self.make_auction_page_request(
            auction_number=auction_number,
            auction_id=auction_id,
            page_number=next_page_number,
        ) 

    # ---------------------------------------------------------
    # BUILD_LOT_SUMMARY_ITEM
    # ---------------------------------------------------------
    def build_lot_summary_item(
        self,
        *,
        lot_data: dict[str, Any],
        expected_auction_id: int,
        response_collected_at_utc: str,
    ) -> LotSummaryItem:
        """Build a LotSummaryItem from one Endpoint 2 items[] object."""

        returned_auction_id = lot_data.get("auction_id")
        lot_id = lot_data.get("id")
        lot_number = lot_data.get("lot_number")

        # Validate the returned auction ID to ensure the lot 
        # belongs to the expected auction.
        if (returned_auction_id != expected_auction_id):
            self.crawler.stats.inc_value(
                "macbid/lot_identifier_mismatches"
            )

            self.logger.error(
                f"Lot identifier mismatch | "
                f"expected_auction_id={expected_auction_id} | "
                f"returned_auction_id={returned_auction_id}"
            )

            raise CloseSpider(
                reason="ep2_lot_identifier_mismatch"
            )
        
        if not isinstance(lot_id, int):
            self.crawler.stats.inc_value(
                "macbid/lot_missing_lot_id"
            )

            self.logger.error(
                f"Missing or invalid lot ID | "
                f"auction_id={returned_auction_id} | "
                f"lot_number={lot_number} | "
                f"returned lot_id={lot_id!r}"
            )

            raise CloseSpider(
                reason="ep2_auction_page_missing_lot_id"
            )

        if not isinstance(lot_number, str) or not lot_number.strip():
            self.crawler.stats.inc_value(
                "macbid/lot_missing_lot_number"
            )

            self.logger.error(
                f"Missing or invalid lot number | "
                f"auction_id={returned_auction_id} | "
                f"returned lot_number={lot_number!r}"
            )

            raise CloseSpider(
                reason="ep2_auction_page_missing_lot_number"
            )
        
        return LotSummaryItem(
            # Collection metadata
            response_collected_at_utc=response_collected_at_utc,

            # Required identifiers
            lot_id=lot_id,
            auction_id=returned_auction_id,
            lot_number=lot_number,
            
            # Product and inventory identifiers
            inventory_id=lot_data.get("inventory_id"),
            product_upc=lot_data.get("upc"),

            # Source timestamps
            date_created_source=lot_data.get(
                "date_created"
            ),
            closed_date_source=lot_data.get(
                "closed_date"
            ),
            expected_close_date_source=lot_data.get(
                "expected_close_date"
            ),

            # Location
            current_location_id=lot_data.get(
                "current_location_id"
            ),

            # Boolean source values
            is_transferable_source=lot_data.get(
                "is_transferrable"
            ),
            is_shippable_source=lot_data.get(
                "is_shippable"
            ),
            is_partial_source=lot_data.get(
                "is_partial"
            ),

            # Auction outcomes
            total_bids_source=lot_data.get(
                "total_bids"
            ),
            winning_bid_amount_source=lot_data.get(
                "winning_bid_amount"
            ),
            unique_bidders_source=lot_data.get(
                "unique_bidders"
            ),

            # Product characteristics
            product_name=lot_data.get(
                "product_name"
            ),
            dimensions_text=lot_data.get(
                "dimensions"
            ),
            quantity_source=lot_data.get(
                "quantity"
            ),
            is_pallet_source=lot_data.get(
                "is_pallet"
            ),

            # Shipping and package measurements
            shipping_height_source=lot_data.get(
                "shipping_height"
            ),
            shipping_width_source=lot_data.get(
                "shipping_width"
            ),
            shipping_length_source=lot_data.get(
                "shipping_length"
            ),
            shipping_weight_source=lot_data.get(
                "shipping_weight"
            ),
            case_packed_qty_source=lot_data.get(
                "case_packed_qty"
            ),

            # Price and classification
            retail_price_source=lot_data.get(
                "retail_price"
            ),
            condition_name=lot_data.get(
                "condition_name"
            ),
            category_name=lot_data.get(
                "category"
            ),
        )
    # ---------------------------------------------------------
    # MAKE_LOT_DETAIL_REQUEST
    # ---------------------------------------------------------
    def make_lot_detail_request(
        self,
        *,
        auction_number: str,
        auction_id: int,
        lot_number: str,
        lot_id: int,
    ) -> Request:
        """Return an Endpoint 3 request for one lot's details."""

        encoded_auction_number = quote(
            auction_number,
            safe="",
        )

        encoded_lot_number = quote(
            lot_number,
            safe="",
        )

        request_url = (
            f"{BASE_URL}/auction/"
            f"{encoded_auction_number}/lot/"
            f"{encoded_lot_number}"
        )

        return Request(
            url=request_url,
            method="GET",
            callback=self.parse_lot_detail,
            errback=self.handle_error,
            cb_kwargs={
                "expected_auction_number": auction_number,
                "expected_auction_id": auction_id,
                "expected_lot_number": lot_number,
                "expected_lot_id": lot_id,
            },
        )

    # ---------------------------------------------------------
    # REQUIRE_NULLABLE_SOURCE_TEXT
    # ---------------------------------------------------------
    def require_nullable_source_text(
        self,
        value: Any,
        *,
        field_name: str,
        lot_id: int,
    ) -> str | None:
        """Nullable text fields should either store a string or None."""

        if value is None or isinstance(value, str):
            return value

        self.crawler.stats.inc_value(
            "macbid/invalid_source_text"
        )

        self.logger.error(
            "Unexpected source-text type | "
            f"field={field_name} | "
            f"lot_id={lot_id} | "
            f"returned value={value!r}"
        )

        raise CloseSpider(
            reason="ep3_lot_detail_invalid_source_text"
        )

    # ---------------------------------------------------------
    # BUILD_LOT_DETAIL_ITEM
    # ---------------------------------------------------------
    def build_lot_detail_item(
            self,
            *,
            response_data: dict[str, Any],
            expected_auction_number: str,
            expected_auction_id: int,
            expected_lot_number: str,
            expected_lot_id: int,
            response_collected_at_utc: str,
    ) -> LotDetailItem:
        """Build one staging LotDetailItem from Endpoint 3 data."""

        returned_lot_id = response_data.get("id")
        returned_auction_id = response_data.get(
            "auction_id"
        )
        returned_lot_number = response_data.get(
            "lot_number"
        )

        # ---------------------------------------------------------
        # Validate the returned lot ID.
        # ---------------------------------------------------------
        if type(returned_lot_id) is not int:
            self.crawler.stats.inc_value(
                "macbid/lot_detail_invalid_lot_ids"
            )

            self.logger.error(
                f"Missing or invalid Endpoint 3 lot ID | "
                f"expected_lot_id={expected_lot_id} | "
                f"returned_lot_id={returned_lot_id!r}"
            )

            raise CloseSpider(
                reason="ep3_lot_detail_invalid_lot_id"
            )

        if returned_lot_id != expected_lot_id:
            self.crawler.stats.inc_value(
                "macbid/lot_detail_lot_id_mismatches"
            )

            self.logger.error(
                f"Endpoint 3 lot ID mismatch | "
                f"expected_lot_id={expected_lot_id} | "
                f"returned_lot_id={returned_lot_id}"
            )

            raise CloseSpider(
                reason="ep3_lot_detail_lot_id_mismatch"
            )

        # ---------------------------------------------------------
        # Validate the returned auction ID.
        # ---------------------------------------------------------

        if type(returned_auction_id) is not int:
            self.crawler.stats.inc_value(
                "macbid/lot_detail_invalid_auction_ids"
            )

            self.logger.error(
                f"Missing or invalid Endpoint 3 auction ID | "
                f"expected_auction_id={expected_auction_id} | "
                f"returned_auction_id={returned_auction_id!r} | "
                f"lot_id={returned_lot_id}"
            )

            raise CloseSpider(
                reason="ep3_lot_detail_invalid_auction_id"
            )

        if returned_auction_id != expected_auction_id:
            self.crawler.stats.inc_value(
                "macbid/lot_detail_auction_id_mismatches"
            )

            self.logger.error(
                f"Endpoint 3 auction ID mismatch | "
                f"expected_auction_id={expected_auction_id} | "
                f"returned_auction_id={returned_auction_id} | "
                f"lot_id={returned_lot_id}"
            )

            raise CloseSpider(
                reason="ep3_lot_detail_auction_id_mismatch"
            )

        # ---------------------------------------------------------
        # Validate the returned lot number.
        # ---------------------------------------------------------

        if (
            not isinstance(returned_lot_number, str)
            or not returned_lot_number.strip()
        ):
            self.crawler.stats.inc_value(
                "macbid/lot_detail_invalid_lot_numbers"
            )

            self.logger.error(
                f"Missing or invalid Endpoint 3 lot number | "
                f"expected_lot_number={expected_lot_number!r} | "
                f"returned_lot_number={returned_lot_number!r} | "
                f"lot_id={returned_lot_id}"
            )

            raise CloseSpider(
                reason="ep3_lot_detail_invalid_lot_number"
            )

        if returned_lot_number != expected_lot_number:
            self.crawler.stats.inc_value(
                "macbid/lot_detail_lot_number_mismatches"
            )

            self.logger.error(
                f"Endpoint 3 lot-number mismatch | "
                f"expected_lot_number={expected_lot_number!r} | "
                f"returned_lot_number={returned_lot_number!r} | "
                f"lot_id={returned_lot_id}"
            )

            raise CloseSpider(
                reason="ep3_lot_detail_lot_number_mismatch"
            )

        # ---------------------------------------------------------
        # Validate the nested auction identifiers.
        # The nested auction object is not stored because the same
        # auction data is already retained in staging_auctions.
        # ---------------------------------------------------------

        nested_auction = response_data.get("auction")

        if not isinstance(nested_auction, dict):
            self.logger.error(
                "Endpoint 3 response missing nested auction | "
                f"lot_id={returned_lot_id}"
            )

            raise CloseSpider(
                reason="ep3_lot_detail_missing_nested_auction"
            )

        nested_auction_id = nested_auction.get("id")
        nested_auction_number = nested_auction.get(
            "auction_number"
        )

        if nested_auction_id != expected_auction_id:
            raise CloseSpider(
                reason="ep3_lot_detail_nested_auction_id_mismatch"
            )

        if (
            nested_auction_number
            != expected_auction_number
        ):
            raise CloseSpider(
                reason="ep3_lot_detail_nested_auction_number_mismatch"
            )

        # ---------------------------------------------------------
        # Retain free-text source values without transforming them.
        # ---------------------------------------------------------

        description_source = (
            self.require_nullable_source_text(
                response_data.get("description"),
                field_name="description",
                lot_id=returned_lot_id,
            )
        )

        update_text_source = (
            self.require_nullable_source_text(
                response_data.get("update_text"),
                field_name="update_text",
                lot_id=returned_lot_id,
            )
        )

        partial_note_source = (
            self.require_nullable_source_text(
                response_data.get("partial_note"),
                field_name="partial_note",
                lot_id=returned_lot_id,
            )
        )

        tested_note_source = (
            self.require_nullable_source_text(
                response_data.get("tested_note"),
                field_name="tested_note",
                lot_id=returned_lot_id,
            )
        )

        damaged_note_source = (
            self.require_nullable_source_text(
                response_data.get("damaged_note"),
                field_name="damaged_note",
                lot_id=returned_lot_id,
            )
        )

        # ---------------------------------------------------------
        # Count image references without retaining their URLs.
        # ---------------------------------------------------------

        primary_image_url = (
            self.require_nullable_source_text(
                response_data.get("image_url"),
                field_name="image_url",
                lot_id=returned_lot_id,
            )
        )

        has_primary_image = int(
            isinstance(primary_image_url, str)
            and bool(primary_image_url.strip())
        )

        images = response_data.get("images")

        if not isinstance(images, list):
            self.crawler.stats.inc_value(
                "macbid/ep3_invalid_image_lists"
            )

            self.logger.error(
                "Endpoint 3 images field was not a list | "
                "lot_id=%s | type=%s",
                returned_lot_id,
                type(images).__name__,
            )

            raise CloseSpider(
                reason="ep3_invalid_images_list"
            )

        detail_image_count = 0

        for image_position, image_data in enumerate(
            images,
            start=1,
        ):
            if not isinstance(image_data, dict):
                self.logger.error(
                    "Invalid Endpoint 3 image object | "
                    "lot_id=%s | position=%s",
                    returned_lot_id,
                    image_position,
                )

                raise CloseSpider(
                    reason="ep3_invalid_image_object"
                )

            detail_image_url = (
                self.require_nullable_source_text(
                    image_data.get("image_url"),
                    field_name="images[].image_url",
                    lot_id=returned_lot_id,
                )
            )

            if (
                isinstance(detail_image_url, str)
                and detail_image_url.strip()
            ):
                detail_image_count += 1

        total_observed_image_count = (
            has_primary_image + detail_image_count
        )

        # ---------------------------------------------------------
        # Construct the staging item.
        # ---------------------------------------------------------

        return LotDetailItem(
            response_collected_at_utc=(
                response_collected_at_utc
            ),

            # Identifiers
            lot_id=returned_lot_id,
            auction_id=returned_auction_id,
            lot_number=returned_lot_number,
            product_id=response_data.get("product_id"),
            inventory_id=response_data.get(
                "inventory_id"
            ),
            product_upc=response_data.get("upc"),

            # Endpoint-3-specific fields
            auction_type_source=response_data.get(
                "auction_type"
            ),
            instant_win_price_source=response_data.get(
                "instant_win_price"
            ),
            buyers_assurance_cost_source=response_data.get(
                "buyers_assurance_cost"
            ),
            product_model=response_data.get("model"),
            size_text=response_data.get("size"),
            box_count_source=response_data.get("boxes"),
            is_tested_source=response_data.get(
                "is_tested"
            ),
            lot_status_source=response_data.get(
                "lot_status"
            ),

            # Source timestamps
            date_created_source=response_data.get(
                "date_created"
            ),
            closed_date_source=response_data.get(
                "closed_date"
            ),
            expected_close_date_source=response_data.get(
                "expected_close_date"
            ),

            # Location and Boolean source values
            current_location_id=response_data.get(
                "current_location_id"
            ),
            is_transferable_source=response_data.get(
                "is_transferrable"
            ),
            is_shippable_source=response_data.get(
                "is_shippable"
            ),
            is_partial_source=response_data.get(
                "is_partial"
            ),

            # Outcome fields
            total_bids_source=response_data.get(
                "total_bids"
            ),
            winning_bid_amount_source=response_data.get(
                "winning_bid_amount"
            ),
            unique_bidders_source=response_data.get(
                "unique_bidders"
            ),

            # Product fields
            product_name=response_data.get(
                "product_name"
            ),
            dimensions_text=response_data.get(
                "dimensions"
            ),
            retail_price_source=response_data.get(
                "retail_price"
            ),
            condition_name=response_data.get(
                "condition_name"
            ),
            category_name=response_data.get(
                "category_name"
            ),

            # Unmodified free-text source fields
            description_source=description_source,
            update_text_source=update_text_source,
            partial_note_source=partial_note_source,
            tested_note_source=tested_note_source,
            damaged_note_source=damaged_note_source,

            # Image measurements
            has_primary_image=has_primary_image,
            detail_image_count=detail_image_count,
            total_observed_image_count=(
                total_observed_image_count
            ),
        )

    # ---------------------------------------------------------
    # PARSE_LOT_DETAIL
    # ---------------------------------------------------------
    def parse_lot_detail(
        self,
        response: Response,
        expected_auction_number: str,
        expected_auction_id: int,
        expected_lot_number: str,
        expected_lot_id: int,
    ):
        """Parse Endpoint 3 and yield one LotDetailItem."""

        response_data = (
            self.require_successful_json_object(
                response,
                endpoint_name="ep3_lot_detail"
            )
        )

        response_collected_at_utc = (
            current_utc_timestamp()
        )

        lot_detail_item = self.build_lot_detail_item(
            response_data=response_data,
            expected_auction_number=(
                expected_auction_number
            ),
            expected_auction_id=expected_auction_id,
            expected_lot_number=expected_lot_number,
            expected_lot_id=expected_lot_id,
            response_collected_at_utc=(
                response_collected_at_utc
            ),
        )

        self.crawler.stats.inc_value(
            "macbid/lot_detail_items_yielded"
        )

        """
        self.logger.info(
            "Lot detail collected | "
            f"auction_number={expected_auction_number} | "
            f"auction_id={expected_auction_id} | "
            f"lot_number={expected_lot_number} | "
            f"lot_id={expected_lot_id}"
        )
        """

        yield lot_detail_item