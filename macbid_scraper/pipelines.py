import json

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from sqlalchemy import update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.engine import Engine
from scrapy import signals
from scrapy.exceptions import CloseSpider

from database.connection import(
    create_staging_engine,
)
from database.staging_tables import(
    collection_runs,
    staging_auctions,
    staging_bid_events,
    staging_lot_bid_histories,
    staging_lot_details,
    staging_lot_summaries,
)

from .items import (
    AuctionRecordItem,
    LotBidHistoryItem,
    LotDetailItem,
    LotSummaryItem,
    BidEventItem,
)

from config import STAGING_DATABASE_PATHS


def utc_now_text() -> str:
    """Return the current UTC time as an ISO format string."""
   
    return datetime.now(
        timezone.utc
    ).isoformat(
        timespec="milliseconds"
    ).replace(
        "+00:00",
        "Z"
    )

class StagingSQLitePipeline:
    """Pipeline for processing privacy-minimized source records 
    in Staging SQLite DB.
    """

    def __init__(
        self,
        database_paths: dict[int, str | Path],
        scraper_version: str,
        schema_version: str,
    ):
        self.database_paths = {
            int(month): Path(path)
            for month, path
            in database_paths.items()
        }

        self.scraper_version = scraper_version
        self.schema_version = schema_version

        # These values don't exist until open_spider() runs.
        self.database_path: Path | None = None
        self.engine: Engine | None = None
        self.collection_run_id: int | None = None
    
    @classmethod
    def from_crawler(cls, crawler):
        """Create an instance of the pipeline from a Scrapy crawler."""

        database_paths = crawler.settings.get(
            "STAGING_DATABASE_PATHS"
        )

        if not isinstance(database_paths, dict):
            raise RuntimeError(
                "STAGING_DATABASE_PATHS is"
                "not assigned a value."
            )
        
        pipeline = cls(
            database_paths = database_paths,
            scraper_version = crawler.settings["SCRAPER_VERSION"],
            schema_version = crawler.settings["STAGING_SCHEMA_VERSION"]
        )   

        # Will be called after Scrapy has determined why the spider closed.
        crawler.signals.connect(
            pipeline.on_close_spider,
            signal=signals.spider_closed
        )

        return pipeline

    
    def require_engine(self) -> Engine:
    
        if self.engine is None:
            raise RuntimeError(
                "The staging database engine is not initialized. "
                "open_spider() must run before this method is called. "
            )
        return self.engine
    
    def require_collection_run_id(self) -> int:

        if self.collection_run_id is None:
            raise RuntimeError(
                "The collection run ID is not initialized. "
                "open_spider() must run before this method is called. "
            )
        return self.collection_run_id
    
    def open_spider(self, spider):

        start_date = spider.start_date
        end_date = spider.end_date

        # Validate the provided date range
        if end_date < start_date:
            raise RuntimeError(
                "The target end date cannot occur "
                "before the target start date | "
                f"start_date={start_date} | "
                f"end_date={end_date}"
            )

        start_year_month = (
            start_date.year,
            start_date.month,
        )

        end_year_month = (
            end_date.year,
            end_date.month,
        )

        if start_year_month != end_year_month:
            raise RuntimeError(
                "One collection run cannot cross a "
                "calendar-month boundary | "
                f"start_date={start_date} | "
                f"end_date={end_date}"
            )

        collection_month = (
        start_date.month
    )

        database_path = (
            self.database_paths.get(
                collection_month
            )
        )

        if database_path is None:
            raise RuntimeError(
                "No staging database path is "
                "configured for collection month "
                f"{collection_month:02d}."
            )

        database_directory = (
        database_path.parent
    )

        if not database_directory.is_dir():
            raise RuntimeError(
                "The staging database directory "
                "does not exist. Confirm that the "
                "SSD is mounted | "
                f"directory={database_directory}"
            )

        # Because the monthly databases are initialized
        # beforehand, a missing file indicates a setup error.
        if not database_path.is_file():
            raise RuntimeError(
                "The selected staging database has "
                "not been initialized | "
                f"database={database_path}"
            )

        # Retain the selected path for logging and shutdown.
        self.database_path = database_path

        spider.logger.info(
            "COLLECTION_TARGET | "
            f"start_date={start_date} | "
            f"end_date={end_date} | "
            f"collection_month="
            f"{collection_month:02d} | "
            f"database={database_path}"
        )
            
        self.engine = create_staging_engine(self.database_path)
        
        run_values = {
            "started_at_utc": utc_now_text(),
            "ended_at_utc": None,

            "target_start_date": spider.start_date.isoformat(),
            "target_end_date": spider.end_date.isoformat(),
            "target_building_ids": json.dumps(sorted(spider.target_building_ids)),

            "scraper_version": self.scraper_version,
            "schema_version": self.schema_version,

            "status": "running",
            "status_reason": None,
        }

        with self.engine.begin() as conn:
            result = conn.execute(
                collection_runs.insert().values(**run_values)
            )

            # Returns a tuple of values (to support composite primary keys)
            primary_key = result.inserted_primary_key

            if primary_key is None:
                raise RuntimeError(
                    "SQLite did not return a primary key for the inserted row."
                )

            # Extract the collection run ID from the tuple
            self.collection_run_id = int(primary_key[0])

        spider.logger.info(
            "started collection run: %s", self.collection_run_id
        )

        self.log_request_policy(spider)

    def insert_source_record(
            self,
            item,
            table,
            conflict_columns,
    ) -> None:
        """Insert a source record into the staging database."""

        # Using ItemAdapter provides a standardized way to access item fields
        adapter = ItemAdapter(item)
        # Convert the item to a dictionary
        item_values = adapter.asdict()

        # Create a set of column names from the table.
        table_column_names = {
            col.name 
            for col in table.columns
        }

        # Create a dictionary of values for the columns 
        # found in the table.
        values = {
            field_name: field_value
            for field_name, field_value in item_values.items()
            if field_name in table_column_names
        }

        collection_run_id = self.require_collection_run_id()
        values["collection_run_id"] = collection_run_id

        # Every item is supposed to inherit this 
        # field from CollectedRecordItem
        if not values.get("response_collected_at_utc"):
            raise ValueError(
                f"{type(item).__name__} is missing "
                "response_collected_at_utc."
            )

        statement = insert(table).values(
            **values
        )

        # Handle conflicts by leaving the row unchanged. This prevents 
        # duplicate entries or accidental rewrites. 
        statement = statement.on_conflict_do_nothing(
            index_elements=conflict_columns
        )

        engine = self.require_engine()

        # Opens a transactional connection to the database, 
        # executes the insert statement, and commits it.
        with engine.begin() as conn:
            conn.execute(statement)

    def process_item(self, item, spider):
        """Send the item to its source-aligned staging table."""

        if isinstance(item, AuctionRecordItem):
            self.insert_source_record(
                item=item,
                table=staging_auctions,
                conflict_columns=[
                    staging_auctions.c.auction_id
                ],
            )

        elif isinstance(item, LotSummaryItem):
            self.insert_source_record(
                item=item,
                table=staging_lot_summaries,
                conflict_columns=[
                    staging_lot_summaries.c.lot_id
                ],
            )

        elif isinstance(item, LotDetailItem):
            self.insert_source_record(
                item=item,
                table=staging_lot_details,
                conflict_columns=[
                    staging_lot_details.c.lot_id
                ],
            )

        elif isinstance(item, LotBidHistoryItem):
            self.insert_source_record(
                item=item,
                table=staging_lot_bid_histories,
                conflict_columns=[
                    staging_lot_bid_histories.c.lot_id
                ],
            )

        elif isinstance(item, BidEventItem):
            self.insert_source_record(
                item=item,
                table=staging_bid_events,
                conflict_columns=[
                    staging_bid_events.c.bid_key
                ],
            )

        else:
            raise TypeError(
                "Unsupported Item type: "
                f"{type(item).__name__}"
            )

        return item

    def on_close_spider(self, 
        spider,
        reason: str,
    ) -> None:
        """Handle the spider_closed signal to update the collection run status."""

        if reason == "finished":
            run_status = "completed"
        elif reason == "start_error":
            run_status = "failed"
        else:
            run_status = "stopped"

        collection_run_id = self.require_collection_run_id()

        # Update the collection_runs table to add columns that record
        # the end time, status (completed/stopped), and stop reason
        statement = (
            update(collection_runs)
            .where(
                collection_runs.c.collection_run_id
                == collection_run_id
            )
            .values(
                ended_at_utc=utc_now_text(),
                status=run_status,
                status_reason=reason
            )
        )

        engine = self.require_engine()
        with engine.begin() as conn:
            conn.execute(statement)

        spider.logger.info(
            "Finalized collection run %s with status: %s, reason: %s",
            collection_run_id,
            run_status,
            reason
        )

        engine.dispose()
        self.engine = None

    def log_request_policy(
        self,
        spider,
    ) -> None:
        """Log the effective request-policy settings."""

        settings = spider.crawler.settings

        spider.logger.info(
            "REQUEST_POLICY | "
            "collection_run_id=%s | "
            "target_start_date=%s | "
            "target_end_date=%s | "
            "target_building_ids=%s | "
            "robots_obey=%s | "
            "user_agent=%s | "
            "concurrency_per_domain=%s | "
            "download_delay_seconds=%s | "
            "autothrottle_enabled=%s | "
            "autothrottle_start_delay=%s | "
            "autothrottle_max_delay=%s | "
            "retry_enabled=%s | "
            "retry_times=%s | "
            "http_cache_enabled=%s | "
            "http_proxy_enabled=%s | "
            "job_directory=%s",
            self.collection_run_id,
            spider.start_date.isoformat(),
            spider.end_date.isoformat(),
            sorted(spider.target_building_ids),
            settings.getbool("ROBOTSTXT_OBEY"),
            settings.get("USER_AGENT"),
            settings.getint(
                "CONCURRENT_REQUESTS_PER_DOMAIN"
            ),
            settings.getfloat("DOWNLOAD_DELAY"),
            settings.getbool(
                "AUTOTHROTTLE_ENABLED"
            ),
            settings.getfloat(
                "AUTOTHROTTLE_START_DELAY"
            ),
            settings.getfloat(
                "AUTOTHROTTLE_MAX_DELAY"
            ),
            settings.getbool("RETRY_ENABLED"),
            settings.getint("RETRY_TIMES"),
            settings.getbool("HTTPCACHE_ENABLED"),
            settings.getbool("HTTPPROXY_ENABLED"),
            settings.get("JOBDIR"),
        )