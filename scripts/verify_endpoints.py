from datetime import date, datetime, timezone
from itertools import islice
from pathlib import Path
from time import sleep
from typing import Any
import requests

from config import PROJECT_ROOT, PROJECT_USER_AGENT, BASE_URL
from generate_auction_candidates import (
    generate_auction_candidates,
)

def create_session() -> requests.Session:
    session = requests.Session()

    session.headers.update(
        {
            "Accept": "application/json",
            "User-Agent": PROJECT_USER_AGENT,
        }
    )

    return session

def request_endpoint(
    session: requests.Session,
    endpoint_path: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Makes a GET request and summarizes its results."""

    request_url = (f"{BASE_URL}{endpoint_path}")

    try:
        response = session.get(
            request_url,
            params=params,
            timeout=30,
        )

    except requests.RequestException as error:
        return {
            "success": False,
            "status": "request_error",
            "http_status": None,
            "response_data": None,
            "error": str(error),
        }

    if response.status_code == 404:
        return {
            "success": False,
            "status": "not_found",
            "http_status": 404,
            "response_data": None,
            "error": None,
        }

    try:
        response_data = response.json()

    except ValueError as error:
        return {
            "success": False,
            "status": "invalid_json",
            "http_status": 200,
            "response_data": None,
            "error": str(error),
        }

    return {
        "success": True,
        "status": "success",
        "http_status": 200,
        "response_data": response_data,
        "error": None,
    }

def verify_auction_number(
    candidate: dict[str, str],
    session: requests.Session,
) -> dict[str, Any]:
    """Calls GET /auctions/{auction_number}?getItems=0
    and extracts auction_id from recovered auction data."""

    auction_number = candidate["auction_number"]

    endpoint_result = request_endpoint(
        session=session,
        endpoint_path= (f"/auctions/{auction_number}"),
        params={
            "getItems": 0,
        },
    )

    result = {
        **candidate,
        **endpoint_result,
        "auction_id": None,
        "opening_date": None,
    }

    if not result["success"]:
        return result

    response_data = result["response_data"]

    auction_id = response_data.get("id")
    opening_date = response_data.get("opening_date")
  
    if auction_id is None:
        result["success"] = False
        result["status"] = "missing_auction_id"
        result["error"] = (
            "The response did not contain an "
            "auction ID."
        )

        return result

    result["auction_id"] = int(auction_id)
    result["opening_date"] = opening_date

    return result

def verify_auction_id(
    auction_id: int,
    session: requests.Session,
) -> dict[str, Any]:
    """Calls GET /auctions/{auction_id}?pg=1&ppg=100 
    and extracts the lot IDs and lot numbers from the
    auction items in the response."""

    endpoint_result = request_endpoint(
        session=session,
        endpoint_path=f"/auctions/{auction_id}",
        params={
            # Changing pg value will fetch the next 100
            # auction items and change the results display
            "pg": 1,
            "ppg": 100,
        },
    )

    result = {
        "auction_id": auction_id,
        **endpoint_result,
        "returned_item_count": None,
        "lots": [],
    }

    if not result["success"]:
        return result

    response_data = result["response_data"]

    items = response_data.get("items")

    if not isinstance(items, list):
        result["success"] = False
        result["status"] = "missing_items"
        result["error"] = (
            "The auction response did not contain "
            "an items list."
        )

        return result

    result["returned_item_count"] = len(items)
    
    result["lots"] = [
        {
            "lot_id": int(item["id"]),
            "lot_number": str(item.get("lot_number"))
        }
        for item in items
        if (
            isinstance(item, dict)
            and item.get("id") is not None
            and item.get("lot_number") is not None
        ) 
    ]

    return result

def verify_lot_number(
    auction_number: str,
    lot_number: str,
    session: requests.Session,
) -> dict[str, Any]:
    """Calls GET /auction/{auction_number}/lot/{lot_number}
    and extracts the product name and numeric lot ID.
    """

    endpoint_result = request_endpoint(
        session=session,
        endpoint_path=(
            f"/auction/{auction_number}/lot/{lot_number}"
        ),
    )

    result = {
        "auction_number": auction_number,
        "lot_number": lot_number,
        **endpoint_result,
        "lot_id": None,
        "product_name": None,
    }

    if not result["success"]:
        return result

    response_data = result["response_data"]

    returned_lot_number = response_data.get("lot_number")

    if str(returned_lot_number) != lot_number:
        result["success"] = False
        result["status"] = "identifier_mismatch"
        result["error"] = (
            "The returned lot number did not match "
            "the requested lot number."
        )

        return result

    lot_id = response_data.get("id")

    if lot_id is None:
        result["success"] = False
        result["status"] = "missing_lot_id"
        result["error"] = (
            "The item response did not contain a lot ID."
        )

        return result

    result["lot_id"] = int(lot_id)
    result["product_name"] = (
        response_data.get("product_name")
        or response_data.get("title")
    )

    return result

def verify_lot_id(
    lot_id: int,
    session: requests.Session,
) -> dict[str, Any]:
    """Calls GET /auctions/lot/{lot_id}/bid-history 
    and extracts bid count from successful responses."""

    endpoint_result = request_endpoint(
        session=session,
        endpoint_path=(
            f"/auctions/lot/{lot_id}/bid-history"
        ),
    )

    result = {
        "lot_id": lot_id,
        **endpoint_result,
        "bid_count": None,
    }

    if not result["success"]:
        return result

    response_data = result["response_data"]

    bids = response_data.get("bids")

    result["bid_count"] = len(bids)

    return result

def main():

    start_date = date(2026, 2, 1)
    end_date = date(2026, 3, 1)

    input_file_name = "pattern_behavior_batches1-3.csv"

    pattern_file = Path(
        PROJECT_ROOT, 
        "data",
        "discovery",
        "auction_patterns",
        input_file_name
    )

    target_building_ids = {24}  # Henderson
    # target_building_ids = {24, 27}  # Henderson and NLV

    candidates = generate_auction_candidates(
        start_date=start_date,
        end_date=end_date,
        pattern_file=pattern_file,
        target_building_ids=target_building_ids,
    )

    results = []

    with create_session() as session:
        # Limit the initial test to five candidates
        for candidate in islice(candidates, 5):
            auction_number_result = (
                verify_auction_number(
                    candidate=candidate,
                    session=session,
                )
            )

            print(
                "\nAuction number:",
                candidate["auction_number"],
                "Opening date:",
                auction_number_result["opening_date"]
            )

            sleep(0.7)

            if not auction_number_result["success"]:
                continue

            auction_id = (
                auction_number_result["auction_id"]
            )

            auction_id_result = verify_auction_id(
                auction_id=auction_id,
                session=session,
            )

            print(
                "\nAuction ID:",
                auction_id,
                "Items returned:",
                auction_id_result["returned_item_count"]
            )

            sleep(0.7)

            if not auction_id_result["success"]:
                continue

            lots = auction_id_result["lots"]

            if not lots:
                print(
                    "No lots were returned for "
                    f"auction {auction_id}."
                )
                continue

            # Verify first item only while testing.
            sample_lot = lots[0]
            sample_lot_id = sample_lot["lot_id"]
            sample_lot_number = sample_lot["lot_number"]

            lot_number_result = verify_lot_number(
                auction_number=candidate["auction_number"],
                lot_number=sample_lot_number,
                session=session,
            )

            print(
                "\nLot number:",
                sample_lot_number,
                "Product:",
                lot_number_result["product_name"],
            )

            sleep(0.7)

            lot_id_result = verify_lot_id(
                lot_id=sample_lot_id,
                session=session,
            )

            print(
                "\nLot ID:",
                sample_lot_id,
                "Total bids placed:",
                lot_id_result["bid_count"],
            )

            sleep(0.7)

if __name__ == "__main__":
    main()