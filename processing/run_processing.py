from sqlalchemy import create_engine, select
from pathlib import Path
from datetime import date

from database.processed_tables import processed_metadata
from processing.helpers.validation import verify_keys_match

from database.staging_tables import (
    collection_runs as staging_runs,
    staging_auctions,
)
from database.processed_tables import collection_runs as processed_runs

from processing.tables.auctions import (
    import_auctions,
    verify_auction_import,
)
 
from processing.tables.collection_runs import (
    import_collection_runs,
    verify_collection_run_import,
)

from processing.constants import (
    STAGING_DATABASES_PARTIAL,
    EXCLUDED_AUCTION_DATES, 
)

from processing.import_scope import (
    find_excluded_auction_ids,
    retained_lot_ids_query,
)

def main():
    # Assign the output path for the processed database. 
    processed_path = Path("macbid_processed_pilot.sqlite").resolve() 
    processed_engine = create_engine(f"sqlite:///{processed_path}")

    try:
        # Create any missing processed tables in the processed database.
        # Existing tables will not be modified or dropped.
        processed_metadata.create_all(processed_engine)

        for database_name, database_path in STAGING_DATABASES_PARTIAL.items():

            # Use the filename consistently for provenance and exclusion lookup.
            source_db = database_path.name

            if not database_path.is_file():
                raise FileNotFoundError(
                    f"Staging database not found: {database_path}"
                )

            # Open this month's staging file in read-only mode to prevent accidental writes.
            database_uri = Path(database_path).resolve().as_uri()
            staging_engine = create_engine(
                f"sqlite:///{database_uri}?mode=ro&uri=true"
            )

            try:
                # Keep all writes for this source file in one transaction.
                # Successful completion commits them; an exception rolls them back.
                with (
                    staging_engine.connect() as source,
                    processed_engine.begin() as target,
                ):
                    # The returned map translates the staging run IDs 
                    # into processed foreign-key values.
                    run_id_map = import_collection_runs(
                        source, target, database_path
                    )
                    verify_collection_run_import(source, target, database_path)

                    # Determine exclusions separately for each source file.
                    # A filename absent from the configuration yields an empty set.
                    excluded_auction_ids = find_excluded_auction_ids(
                        source,
                        excluded_date=EXCLUDED_AUCTION_DATES.get(source_db),
                    )

                    auction_count = import_auctions(
                        source,
                        target,
                        database_path,
                        run_id_map,
                        excluded_auction_ids=excluded_auction_ids,
                    )
                    verify_auction_import(
                        source,
                        target,
                        database_path,
                        excluded_auction_ids=excluded_auction_ids,
                    )

                print(
                    f"{database_name}: imported and verified "
                    f"{len(run_id_map)} collection runs"
                )
            finally:
                staging_engine.dispose()
    finally:
        processed_engine.dispose()


if __name__ == "__main__":
    main()