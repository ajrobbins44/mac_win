# MAC.BID API Endpoint Map

**Last verified:** 2026-10-14
**Base URL:** https://api.macdiscount.com
**Access:** Publicly accessible without user login. Access was tested in an incognito browser and reaffirmed with unauthenticated HTTP GET requests. 

## Purpose

This document describes the public endpoints used for auction discovery and research data collection. It records observed behavior; it is **not official MAC.BID API documentation.** 

## Observed Behavior Summary

| Category | Observed behavior |
| --- | --- |
| Protocol | HTTPS |
| Response format | JSON |
| Authentication | No login, cookie, API key, or authorization header is required for the documented GET requests. |
| Required request headers | No special application header was required. `Accept: application/json` is recommended. A truthful, project-specific `User-Agent` is planned when collecting data. |
| CORS | `Access-Control-Allow-Origin: *` was observed. |
| Success status | `200 OK` |
| Not-found response | `404 Not Found` with `Content-Type: application/json`; an invalid auction lookup returned the JSON string `"Auction not found"`. |
| Rate limits | **Unknown.** No `429 Too Many Requests` response was observed during initial verification, but this does not establish that no limit exists. |

## Endpoint map

| Step | Starting value | Request used | Value obtained for the next step |
|---|---|---|---|
1 | string `auction_number` | `GET /auctions/{auction_number}?getItems=0` | numeric `auction_id` and auction metadata |
| 2 | numeric `auction_id` | `GET /auctions/{auction_id}?pg=…&ppg=…` | Lot records, including numeric `lot_id` and string `lot_number` |
| 3 | string `auction_number` and string `lot_number` | `GET /auction/{auction_number}/lot/{lot_number}` | Details pertaining to one item |
| 4 |  numeric `lot_id` | `GET /auctions/lot/{lot_id}/bid-history` | Bidding history for one lot item |

## Valid examples (copy and paste in terminal to see results)

**Step 1:** 
`cURL "https://api.macdiscount.com/auctions/HEA2602-01-A1?getItems=0"`

Verify that a generated auction number exists, obtain its
numeric auction ID, and collect auction-level metadata.

**Step 2:**
`cURL "https://api.macdiscount.com/auctions/71841?pg=1&ppg=100"`

Retrieve auction metadata and a page of lots belonging to a verified auction.

**Pagination note:** The provided response contains the first page of up to 100 items. Because `total_lots` is null, total auction size should
not be inferred from that field. Pagination behavior must be verified using additional pages.

**Step 3:** 
`cURL "https://api.macdiscount.com/auction/HEA2602-01-A1/lot/2054M"`

Extracts item-level metadata.

**Step 4:**
`cURL "https://api.macdiscount.com/auctions/lot/49027749/bid-history"`

Extracts an item's bid history metadata.