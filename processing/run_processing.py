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

from processing.tables.collection_runs import (
    import_collection_runs,
    verify_collection_run_import,
)

from processing.constants import (
    STAGING_DATABASES_PARTIAL, 
)

from processing.import_scope import (
    find_excluded_auction_ids,
    retained_lot_ids_query,
)

def main():
    processed_path = Path("macbid_processed_pilot.sqlite").resolve()
    processed_engine = create_engine(f"sqlite:///{processed_path}")

    try:
        processed_metadata.create_all(processed_engine)

        for database_name, database_path in STAGING_DATABASES_PARTIAL.items():
            database_uri = Path(database_path).resolve().as_uri()
            staging_engine = create_engine(
                f"sqlite:///{database_uri}?mode=ro&uri=true"
            )

            try:
                with (
                    staging_engine.connect() as source,
                    processed_engine.begin() as target,
                ):
                    run_id_map = import_collection_runs(
                        source, target, database_path
                    )
                    verify_collection_run_import(source, target, database_path)

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