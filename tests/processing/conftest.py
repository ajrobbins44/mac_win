import pytest
from sqlalchemy import create_engine

from database.processed_tables import collection_runs as processed_runs
from database.staging_tables import collection_runs as staging_runs


@pytest.fixture
def databases(tmp_path):
    """Create fresh staging and processed databases for each test."""
    staging_engine = create_engine(
        f"sqlite:///{tmp_path / 'staging.sqlite'}"
    )
    processed_engine = create_engine(
        f"sqlite:///{tmp_path / 'processed.sqlite'}"
    )

    try:
        staging_runs.create(staging_engine)
        processed_runs.create(processed_engine)

        yield staging_engine, processed_engine
    finally:
        staging_engine.dispose()
        processed_engine.dispose()