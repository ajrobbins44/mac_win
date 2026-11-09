"""
Read-only quality audits for monthly MAC.BID staging tables.

run_staging_audits.py controls which databases are audited 
when running the staging audit process.
"""

from sqlalchemy.engine import Connection
from sqlalchemy import Integer, text
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
    staging_auctions,
    staging_lot_summaries,
    staging_lot_details,
    staging_lot_bid_histories,
    staging_bid_events,
)

# ---------------------------------------------------------
# QUOTE_IDENTIFIER
# ---------------------------------------------------------

def quote_identifier(identifier: str) -> str:
    """Return the identifier quoted for use in SQL queries."""
    
    # Uses the standard way to escape a quote within a quoted identifier.
    return '"' + identifier.replace('"', '""') + '"'

# ---------------------------------------------------------
# AUDIT_SHARED_LOT_FIELDS
# ---------------------------------------------------------

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

    # Create SQLAlchemy aliases for the two tables. These prevent
    # mismatches when column names are the same in both tables.
    summaries = staging_lot_summaries.alias("s")
    details = staging_lot_details.alias("d")

    # Validate all shared fields across both tables before querying.
    # Fails early only if both tables are missing the shared field.
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

    # Now query each shared field to compare values between lot 
    # summaries and lot details. It will identify whether values 
    # match, mismatch, or if one table has a value while the other is NULL.
    for field in shared_fields:

        summary_col = summaries.c[field]
        detail_col = details.c[field]

        # Each CASE statement returns 1 when field values match and 0
        # otherwise. SUM(CASE) will count the number of matching or mismatching rows.
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
            # Join the lot summaries and lot details tables on lot_id
            # to compare the shared fields between the two tables.
            .select_from(
                summaries.join(
                    details,
                    summaries.c.lot_id == details.c.lot_id,
                )
            )
        )
        # Will execute the statement and return one row with all the 
        # shared field comparison results.
        row = conn.execute(statement).one()

        results.append(
            {
                "database_name": database_name,
                "field_name": field,
                "compared_lots": int(row.compared_lots),

                # SUM over an empty join can be null, 
                # so use 0 in that case instead.
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

# ---------------------------------------------------------
# CLASSIFY_COLUMN
# ---------------------------------------------------------

def classify_column(
        row_count: int,
        non_null_count: int,
        distinct_non_null_count: int,
) -> str:
    """Classify column variability without treating NULL as a value.
    
    A column can have a single observed non-null value but still have
    missing data. This is different from a strictly constant column.
    """

    # Check for empty table first. No observed values means it
    # cannot be classified as constant or variable.
    if row_count == 0:
        return "empty_table"

    # All rows exist, but every value in the column is NULL.
    elif non_null_count == 0:
        return "all_null"

    # Only 1 distinct non-null value observed.
    elif distinct_non_null_count == 1:
        # Check if there's complete coverage of the one non-null value.
        if non_null_count == row_count:
            return "strict_constant"
        # If not, the column is constant only when the value is present.
        return "constant_when_present"

    else:
        # More than one distinct non-null value observed.
        return "variable"

# ---------------------------------------------------------
# SAMPLE_SHARED_FIELD_DISAGREEMENTS
# ---------------------------------------------------------

def sample_shared_field_disagreements(
    conn,
    field_name: str,
    limit: int = 20,
):
    """Retrieve examples of conflicting non-NULL field values. 
    
    This is a helper function for displaying disagreements between 
    summary and detail tables.
    """

    summaries = staging_lot_summaries
    details = staging_lot_details

    if (
        field_name not in summaries.c
        or field_name not in details.c
    ):
        raise ValueError(f"Invalid shared field: {field_name}")

    summary_col = summaries.c[field_name]
    detail_col = details.c[field_name]

    statement = (
        select(
            summaries.c.lot_id,
            summaries.c.auction_id,
            summary_col.label("summary_value"),
            detail_col.label("detail_value"),
        )
        .select_from(
            summaries.join(
                details,
                summaries.c.lot_id == details.c.lot_id,
            )
        )
        .where(
            summary_col.is_not(None)
            & detail_col.is_not(None)
            & (summary_col != detail_col)
        )
        .order_by(summaries.c.lot_id)
        .limit(limit)
    )

    return [
        dict(row)
        for row in conn.execute(statement).mappings()
    ]

# ---------------------------------------------------------
# AUDIT_COLUMN_PROFILES
# ---------------------------------------------------------

def audit_column_profiles(
        conn: Connection,
        database_name: str,
        table_name: str,
        columns: list,
        row_count: int,
)-> list[dict]:
    """Profile NULL coverage and distinct-value counts for every column.

    The audit is descriptive: it does not assume columns are constant.
    It returns one dictionary per column for later reporting.
    """
    
    audit_results = []

    quoted_table_name = quote_identifier(table_name)

    for column in columns:

        # Accept either names from SQLAlchemy inspect().get_columns()
        # after extraction, or PRAGMA table_info() tuples (name at index 1).
        column_name = column if isinstance(column, str) else column[1]
        quoted_column_name = quote_identifier(column_name)

        # COUNT(column) ignores NULL; COUNT(DISTINCT column) counts
        # distinct non-NULL values. Row count is supplied by the runner.
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

        # Derive missingness without fetching the underlying data rows.
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

# ---------------------------------------------------------
# FIND_SUMMARIES_WITHOUT_DETAILS
# ---------------------------------------------------------

def find_summaries_without_details(conn):
    """Return summary records without corresponding detail records.

    This function performs a LEFT OUTER JOIN between the summary and detail
    tables and filters for rows where the detail table has no matching record. 
    So far the audit results only show summary records that lack corresponding 
    detail records in the month_01 staging database.
    """

    summaries = staging_lot_summaries
    details = staging_lot_details

    statement = (
        select(
            summaries.c.lot_id,
            summaries.c.auction_id,
            summaries.c.lot_number,
            summaries.c.collection_run_id,
        )
        .select_from(
            summaries.outerjoin(
                details,
                summaries.c.lot_id == details.c.lot_id,
            )
        )
        .where(details.c.lot_id.is_(None))
        .order_by(summaries.c.auction_id, summaries.c.lot_id)
    )

    return [
        dict(row)
        for row in conn.execute(statement).mappings()
    ]

# ---------------------------------------------------------
# AUDIT_REFERENTIAL_INTEGRITY
# ---------------------------------------------------------

def audit_referential_integrity(
    conn: Connection,
    database_name: str,
) -> dict[str, str | int]:
    """
    Audit relationships and record coverage across staging tables.

    All checks are read-only and scoped to one staging database.
    A missing match means missing *within this database*, not necessarily
    missing across every monthly file. Coverage gaps are not automatically
    crawler errors.
    """

    auctions = staging_auctions
    summaries = staging_lot_summaries
    details = staging_lot_details
    histories = staging_lot_bid_histories
    bids = staging_bid_events

    def count_unmatched(
        child,
        parent,
        child_key: str,
        parent_key: str,
    ) -> int:
        """Count child rows lacking a parent with the specified key.

        This nested helper reuses the outer function's SQLAlchemy `conn`.
        A LEFT OUTER JOIN retains every child row; unmatched parent
        columns become NULL, which the WHERE clause selects.
        """

        statement = (
            select(func.count())
            .select_from(
                child.outerjoin(
                    parent,
                    child.c[child_key] == parent.c[parent_key],
                )
            )
            .where(parent.c[parent_key].is_(None))
        )

        return conn.execute(statement).scalar_one()

    # Referential integrity: every summary/detail auction_id should have
    # a corresponding auction record in this same monthly database.
    orphaned_summaries = count_unmatched(
        summaries, auctions, "auction_id", "auction_id"
    )

    orphaned_details = count_unmatched(
        details, auctions, "auction_id", "auction_id"
    )

    # Endpoint coverage: these two counts measure missing counterparts
    # in opposite directions. They are not necessarily data corruption.
    summaries_without_details = count_unmatched(
        summaries, details, "lot_id", "lot_id"
    )

    details_without_summaries = count_unmatched(
        details, summaries, "lot_id", "lot_id"
    )

    # There is no master lots table in staging. UNION combines lot IDs
    # from summaries and details and removes duplicates, so a history is
    # orphaned only if neither endpoint contains its lot.
    known_lots = (
        select(summaries.c.lot_id)
        .union(select(details.c.lot_id))
        .subquery()
    )

    histories_without_lots = count_unmatched(
        histories, known_lots, "lot_id", "lot_id"
    )

    # Each bid event should be associated with a successfully collected
    # history response for its lot. Histories with zero bids are valid.
    bids_without_histories = count_unmatched(
        bids, histories, "lot_id", "lot_id"
    )

    # A lot_id present in both endpoints should belong to the same
    # auction_id. An INNER JOIN limits the comparison to shared lots;
    # missing counterparts were counted separately above.
    auction_disagreements = (
        select(func.count())
        .select_from(
            summaries.join(
                details,
                summaries.c.lot_id == details.c.lot_id,
            )
        )
        .where(
            summaries.c.auction_id != details.c.auction_id
        )
    )

    mismatched_lot_auction_ids = conn.execute(
        auction_disagreements
    ).scalar_one()

    return {
        "database_name": database_name,
        "orphaned_summaries": orphaned_summaries,
        "orphaned_details": orphaned_details,
        "summaries_without_details": summaries_without_details,
        "details_without_summaries": details_without_summaries,
        "histories_without_lots": histories_without_lots,
        "bids_without_histories": bids_without_histories,
        "mismatched_lot_auction_ids": mismatched_lot_auction_ids,
    }

# ---------------------------------------------------------
# AUDIT_BID_RECORD_COUNTS
# ---------------------------------------------------------

def audit_bid_record_counts(
    conn: Connection,
) -> dict[str, int]:
    """Compare each history response's bid count with saved event rows.

    A successfully collected empty bids[] array has expected count zero.
    This audit only evaluates lots with a history row; bid events lacking
    histories are reported by the referential integrity audit.
    """

    histories = staging_lot_bid_histories
    bids = staging_bid_events

    # Reduce many bid-event rows to one observed count per lot_id.
    # The subquery can then be LEFT JOINed to the one-row-per-lot histories.
    bid_counts = (
        select(
            bids.c.lot_id,
            func.count().label("stored_bid_count"),
        )
        .group_by(bids.c.lot_id)
        .subquery()
    )

    # A history with no event rows has no matching subquery row.
    # COALESCE interprets that missing aggregate as zero saved bids.
    stored_count = func.coalesce(
        bid_counts.c.stored_bid_count, 0
    )

    # Compare expected and stored counts for every history.
    # CAST(boolean AS INTEGER) maps a mismatch to 1 and a match to 0;
    # SUM counts mismatched histories. COALESCE handles an empty table.
    statement = (
        select(
            func.count().label("histories_checked"),
            func.coalesce(
                func.sum(
                    func.cast(
                        func.coalesce(
                            histories.c.observed_bid_record_count
                            != stored_count,
                            False,
                        ),
                        Integer,
                    )
                ),
                0,
            ).label("count_mismatches"),
        )
        .select_from(
            histories.outerjoin(
                bid_counts,
                histories.c.lot_id == bid_counts.c.lot_id,
            )
        )
    )

    row = conn.execute(statement).one()

    return {
        "histories_checked": int(row.histories_checked),
        "bid_count_mismatches": int(row.count_mismatches),
    }