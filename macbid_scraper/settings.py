# Scrapy settings for macbid_scraper project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html
from pathlib import Path
from config import PROJECT_ROOT, PROJECT_USER_AGENT

# -------------------------------------------------------------------
# Scrapy settings for the MAC.BID research crawler.
# Policy references below point to sections of 
# docs/compliance/request-policy.md
# -------------------------------------------------------------------

BOT_NAME = "macbid_scraper"

STAGING_DATABASE_PATH = Path(
    PROJECT_ROOT,
    "data",
    "staging",
    "macbid_staging_test.sqlite3"
)

SCRAPER_VERSION = "1.0.0"
STAGING_SCHEMA_VERSION = "1.0.0"

ITEM_PIPELINES = {
    "macbid_scraper.pipelines.StagingSQLitePipeline": 300
}

SPIDER_MODULES = ["macbid_scraper.spiders"]
NEWSPIDER_MODULE = "macbid_scraper.spiders"

ADDONS = {}


# Policy: "Identification and records"
# Descriptive User-Agent stating the project purpose and a contact email.
USER_AGENT = PROJECT_USER_AGENT

# Policy: "Access boundaries"
# Follow robots.txt. Note that Scrapy does not apply a Crawl-delay from
# robots.txt, so if one is ever published, set DOWNLOAD_DELAY to match it.
ROBOTSTXT_OBEY = True

# Policy: "Access boundaries"
# No login, so no cookies or session state are needed or stored.
COOKIES_ENABLED = False

# Policy: "Request pacing"
# No more than one active request at a time, across all domains.
CONCURRENT_REQUESTS = 1
CONCURRENT_REQUESTS_PER_DOMAIN = 1

# Wait at least one second between consecutive requests.
DOWNLOAD_DELAY = 1.0
# Turn off Scrapy's default 0.5x-1.5x randomization so the 1-second minimum
# always holds.
RANDOMIZE_DOWNLOAD_DELAY = False

# Policy: "Request pacing"
# AutoThrottle may raise the delay when responses slow down, but it never goes
# below DOWNLOAD_DELAY (1 second). Target concurrency of 1 matches the
# one-request-at-a-time rule.
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0
AUTOTHROTTLE_MAX_DELAY = 10.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0

# A request that hangs should not stall the one-at-a-time crawl.
DOWNLOAD_TIMEOUT = 30

# Policy: "Retries and stopping behavior"
# Retry connection failures, timeouts, and 500/502/503/504 responses at most
# once. 400, 401, 403, 404, and 429 are deliberately not retried.
RETRY_ENABLED = True
RETRY_TIMES = 1
RETRY_HTTP_CODES = [500, 502, 503, 504]

# Policy: "Access boundaries" ("Avoid repeated API calls")
# The HTTP cache stays off for real collection runs. Every response is saved
# once as raw JSON so the same request is never needed again.
HTTPCACHE_ENABLED = False 

# Policy: "Identification and records" (logs of requests, status codes,
# retry counts, start and stop times, reasons for interrupted runs)
# Set LOG_FILE and JOBDIR per run, for example:
#   -s LOG_FILE=logs/henderson_run1.log -s JOBDIR=crawls/henderson_run1
LOG_LEVEL = "INFO"

# Set settings whose default value is deprecated to a future-proof value
FEED_EXPORT_ENCODING = "utf-8"
