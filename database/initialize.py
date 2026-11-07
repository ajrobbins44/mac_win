from pathlib import Path
from sqlalchemy import inspect

from .connection import create_staging_engine

from config import STAGING_DATABASE_PATHS

REQUIRED_TABLES = {
    "collection_runs",
    "staging_auctions",
    "staging_lot_summaries",
    "staging_lot_details",
    "staging_lot_bid_histories",
    "staging_bid_events",
}

def initialize_database(
    month: int,
    database_path: Path,
):
    """Initialize and inspect one monthly staging database."""

    database_path = Path(
        database_path
    )

    if not database_path.parent.is_dir():
        raise RuntimeError(
            "The staging directory does not exist. "
            "Confirm that the SSD is mounted: "
            f"{database_path.parent}"
        )

    print(
        f"\nMonth {month:02d}"
    )

    print(
        f"Staging database: {database_path}"
    )

    engine = create_staging_engine(
        database_path
    )

    try:
        inspector = inspect(
            engine
        )

        table_names = sorted(
            inspector.get_table_names()
        )

        print("\nTables present:")

        for table_name in table_names:
            print(
                f"  - {table_name}"
            )

        missing_tables = (
            REQUIRED_TABLES
            - set(table_names)
        )

        if missing_tables:
            missing_text = ", ".join(
                sorted(missing_tables)
            )

            raise RuntimeError(
                f"Missing tables in month "
                f"{month:02d}: "
                f"{missing_text}"
            )

        print(
            "\nAll required tables are present."
        )


    finally:
        # Release the file before opening the
        # next monthly database.
        engine.dispose()

def initialize_all_databases():
    """Initialize all the configured monthly staging databases."""

    for month, database_path in sorted(
        STAGING_DATABASE_PATHS.items()
    ):
        initialize_database(
            month=month,
            database_path=database_path,
        )

    print(
        "\nAll monthly staging databases "
        "were initialized successfully."
    )

def initialize_database_for_month(month: int):
    """Initialize the staging database for a specific month."""

    database_path = STAGING_DATABASE_PATHS[month]

    if not database_path:
        raise RuntimeError(
            f"No staging database configured for month {month:02d}."
        )

    initialize_database(
        month=month,
        database_path=database_path,
    )

    print(
        f"\nMonth {month:02d} staging database "
        "initialized successfully."
    )

def main():

    initialize_all_databases()

if __name__ == "__main__":
    main()