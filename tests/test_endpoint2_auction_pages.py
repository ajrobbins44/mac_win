from sqlalchemy import func, select

from database.connection import (
    create_staging_engine,
)
from macbid_scraper.spiders.macbid_historical_auctions import (
    MacbidHistoricalAuctionsSpider,
)

def test_make_auction_page_request():
    spider = MacbidHistoricalAuctionsSpider()
    spider.auction_page_size = 100

    request = spider.make_auction_page_request(
        auction_number="HEA2602-01-A1",
        auction_id=71841,
        page_number=1,
    )

    assert request.url == (
        "https://api.macdiscount.com/"
        "auctions/71841?pg=1&ppg=100"
    )

    assert request.cb_kwargs == {
        "auction_number": "HEA2602-01-A1",
        "auction_id": 71841,
        "page_number": 1,
    }

    assert request.callback == (
        spider.parse_auction_page
    )

    assert request.errback == spider.handle_error