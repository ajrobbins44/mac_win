from pathlib import Path
from sqlalchemy import inspect
from .connection import create_staging_engine
from config import STAGING_DATABASE_PATH

def main():
    engine = create_staging_engine(STAGING_DATABASE_PATH)

    inspector = inspect(engine)

    table_names = sorted(inspector.get_table_names())

    print(f"Staging database: {STAGING_DATABASE_PATH}")
    print("\nTables created:")
    for name in table_names:
        print(f"  - {name}")

    required_tables = {
        "collection_runs",
        "staging_auctions",
        "staging_lot_summaries",
        "staging_lot_details",
        "staging_lot_bid_histories",
        "staging_bid_events",
    }

    missing_tables = required_tables - set(table_names)

    if missing_tables:
        print(f"\nMissing tables: {', '.join(missing_tables)}")
    else:
        print("\nAll required tables are present.")

if __name__ == "__main__":
    main()