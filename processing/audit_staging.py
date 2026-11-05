import csv
import sqlite3

from sqlalchemy.engine import Connection
from sqlalchemy import text
from pathlib import Path
from typing import Any

from sqlalchemy import (
    create_engine,
    func,
    select,
    table,
    case,
    and_,
)

from database.staging_tables import (
    staging_lot_summaries,
    staging_lot_details,
)

from processing.constants import (
    TABLES_TO_AUDIT,
    SHARED_LOT_FIELDS,
    STAGING_DATABASES,
)

def quote_identifier(identifier: str) -> str:
    """Return the identifier quoted for use in SQL queries."""
    
    # Uses the standard way to escape a quote within a quoted identifier.
    return '"' + identifier.replace('"', '""') + '"'

def classify_column(
        row_count: int,
        non_null_count: int,
        distinct_non_null_count: int,
) -> str:
    """Classify a column based on its observed values."""
    
    if row_count == 0:
        return "empty_table"
    
    elif non_null_count == 0:
        return "all_null"
    
    elif distinct_non_null_count == 1:
        if non_null_count == row_count:
            return "strict_constant"
        
        return "constant_when_present"

    else:
        return "variable"

def audit_shared_lot_fields(
    conn: Connection,
    database_name: str,
    shared_fields: list[str],
) -> list[dict[str, str | int]]:
    """
    Compare shared fields between lot summaries and lot details.

    Only lots present in both tables are compared.
    NULL differences are reported separately from value mismatches.
    """

    # Create SQLAlchemy aliases for the two tables.
    summaries = staging_lot_summaries.alias("s")
    details = staging_lot_details.alias("d")

    # Validate ALL configured shared fields before querying.
    for field in shared_fields:
        if (
            field not in summaries.c
            or field not in details.c
        ):
            raise ValueError(
                f"Shared field '{field}' is not present in both "
                "staging_lot_summaries and staging_lot_details."
            )

    results: list[dict[str, str | int]] = []

    # Audit each shared field.
    for field in shared_fields:

        summary_col = summaries.c[field]
        detail_col = details.c[field]

        statement = (
            select(
                func.count().label("compared_lots"),

                func.sum(
                    case(
                        (
                            summary_col.is_not(None)
                            & detail_col.is_not(None)
                            & (summary_col == detail_col),
                            1,
                        ),
                        else_=0,
                    )
                ).label("match_count"),

                func.sum(
                    case(
                        (
                            summary_col.is_not(None)
                            & detail_col.is_not(None)
                            & (summary_col != detail_col),
                            1,
                        ),
                        else_=0,
                    )
                ).label("mismatch_count"),

                func.sum(
                    case(
                        (
                            summary_col.is_not(None)
                            & detail_col.is_(None),
                            1,
                        ),
                        else_=0,
                    )
                ).label("summary_only_count"),

                func.sum(
                    case(
                        (
                            summary_col.is_(None)
                            & detail_col.is_not(None),
                            1,
                        ),
                        else_=0,
                    )
                ).label("detail_only_count"),

                func.sum(
                    case(
                        (
                            summary_col.is_(None)
                            & detail_col.is_(None),
                            1,
                        ),
                        else_=0,
                    )
                ).label("both_null_count"),
            )
            .select_from(
                summaries.join(
                    details,
                    summaries.c.lot_id == details.c.lot_id,
                )
            )
        )

        row = conn.execute(statement).one()

        results.append(
            {
                "database_name": database_name,
                "field_name": field,
                "compared_lots": int(row.compared_lots),
                "match_count": int(row.match_count or 0),
                "mismatch_count": int(row.mismatch_count or 0),
                "summary_only_count": int(
                    row.summary_only_count or 0
                ),
                "detail_only_count": int(
                    row.detail_only_count or 0
                ),
                "both_null_count": int(
                    row.both_null_count or 0
                ),
            }
        )

    return results

def audit_column_profiles(
        conn: Connection,
        database_name: str,
        table_name: str,
        columns: list,
        row_count: int,
)-> list[dict]:
    """Audit columns that are expected to be constant across rows."""
    
    audit_results = []

    quoted_table_name = quote_identifier(table_name)

    for column in columns:

        column_name = column[1]
        quoted_column_name = quote_identifier(column_name)

        result = conn.execute(
            text(
                f"""
                SELECT
                    COUNT({quoted_column_name}),
                    COUNT(DISTINCT {quoted_column_name})
                FROM {quoted_table_name}
                """
            )
        ).one()

        non_null_count = result[0]
        distinct_non_null_count = result[1]

        null_count = row_count - non_null_count

        classification = classify_column(
            row_count=row_count,
            non_null_count=non_null_count,
            distinct_non_null_count=distinct_non_null_count,
        )

        audit_results.append(
            {
                "database_name": database_name,
                "table_name": table_name,
                "column_name": column_name,
                "row_count": row_count,
                "non_null_count": non_null_count,
                "null_count": null_count,
                "distinct_non_null_count": distinct_non_null_count,
                "classification": classification,
            }
        )

    return audit_results

def main() -> None:
    """Run the audit process for all read-only staging databases
    not already audited.
    """

    databases_audited = set()
    
    for database_name, db_path in STAGING_DATABASES.items():

        # Open the database in read-only mode.
        database_uri = (
            db_path.resolve().as_uri()
            + "?mode=ro"
        )

        if database_name in databases_audited:
            # Skip databases that have already been audited.
            continue

        with sqlite3.connect(database_uri) as conn:

            for table_name in TABLES_TO_AUDIT:

                quoted_table_name = quote_identifier(table_name)

                # Retrieve row count without loading rows.
                row_count = conn.execute(
                    f"SELECT COUNT(*) FROM {quoted_table_name}"
                ).fetchone()[0]

                # Retrieve column information.
                columns = conn.execute(
                    f"PRAGMA table_info({quoted_table_name})"
                ).fetchall()

                print(
                    f"\n{database_name} - {table_name}"
                )

                print(
                    # Include commas as thousand separators for 
                    # row count readability.
                    f"Rows: {row_count:,}"
                )

                print(
                    "Columns:",
                    [
                        column[1]
                        for column in columns
                    ],
                )

        # Add the current database to the set of audited databases
        # after processing all tables in the current database.
        databases_audited.add(database_name)

    print(f"\nDatabases audited: {databases_audited}")

if __name__ == "__main__":
    main()