from datetime import date
import logging
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock

import pytest
from scrapy.crawler import Crawler
from scrapy.settings import Settings

from macbid_scraper.spiders.macbid_historical_auctions import (
    MacbidHistoricalAuctionsSpider,
)

class FakeStats:
    """Provide the Scrapy stats behavior needed by tests."""

    def __init__(self):
        self.values: dict[str, object] = {
            "finish_reason": "finished",
        }

    def get_value(
        self,
        key: str,
        default=None,
    ):
        """Return a stored statistic or its default."""

        return self.values.get(key, default)

    def set_value(
        self,
        key: str,
        value: object,
    ) -> None:
        """Set a statistic to a specific value."""

        self.values[key] = value

    def inc_value(
        self,
        key: str,
        count: int = 1,
    ) -> None:
        """Increase an integer statistic."""

        current_value = self.values.get(
            key,
            0,
        )

        if not isinstance(current_value, int):
            current_value = 0

        self.values[key] = (
            current_value + count
        )

@pytest.fixture
def test_settings() -> Settings:
    """Return the Scrapy settings needed by test doubles."""

    return Settings(
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

@pytest.fixture
def pipeline_spider(
    test_settings: Settings,
):
    """Return the minimal spider-like object needed by the pipeline."""

    return SimpleNamespace(
        start_date=date(2026, 2, 1),
        end_date=date(2026, 2, 1),
        target_building_ids={24},

        logger=logging.getLogger(
            "staging-pipeline-test"
        ),

        crawler=SimpleNamespace(
            stats=FakeStats(),
            settings=test_settings,
        ),
    )

@pytest.fixture
def historical_spider(
    test_settings: Settings,
) -> MacbidHistoricalAuctionsSpider:
    """Return a real spider attached to a crawler test double."""

    crawler_double = SimpleNamespace(
        settings=test_settings,
        stats=FakeStats(),

        # Spider.from_crawler() connects its close handler
        # through crawler.signals.
        signals=MagicMock(),
    )

    # SimpleNamespace is deliberately acting as the small
    # portion of Crawler used by these tests.
    crawler = cast(
        Crawler,
        crawler_double,
    )

    return (
        MacbidHistoricalAuctionsSpider.from_crawler(
            crawler
        )
    )