from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from .staging_tables import metadata

def create_staging_engine(
        db_path: Path,
) -> Engine:
    """Opens SQLite and creates the tables in the database."""

    engine = create_engine(f"sqlite+pysqlite:///{db_path}")

    @event.listens_for(engine, "connect")
    def configure_sqlite(dbapi_connection, _connection_record):
        """Configures SQLite connection."""

        cursor = dbapi_connection.cursor()

        # Ensures foreign keys are enforced
        cursor.execute(
            "PRAGMA foreign_keys=ON"
        )
        # WAL = write-ahead logging
        # Improves reliability when reads and writes overlap
        cursor.execute(
            "PRAGMA journal_mode=WAL"
        )

        cursor.close()
        
    # Creates tables attached to the metadata object (includes all staging tables)
    metadata.create_all(engine)
    return engine