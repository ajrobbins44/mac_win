import csv
import sqlite3

from pathlib import Path

from config import (
    STAGING_DATABASE_PATHS,
)

from processing.constants import (
    TABLES_TO_AUDIT,
    SHARED_LOT_FIELDS,
)