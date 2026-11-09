from collections import Counter
from pathlib import Path

from sqlalchemy import (
    create_engine,
    inspect,
)

from processing.constants import (
    STAGING_DATABASES,
    SHARED_LOT_FIELDS,
    TABLES_TO_AUDIT,
)

from processing.audit.staging_audits import (
    audit_column_profiles,
    audit_shared_lot_fields,
    audit_referential_integrity,
    audit_bid_record_counts,

    # Helper functions added after the initial audit results
    # revealed a need for further investigation of specific issues.
    sample_shared_field_disagreements,
    find_summaries_without_details,
)

def audit_database(
    conn,
    database_name: str,
) -> dict:
    """
    Execute the complete audit suite for one staging database.

    All audit functions share the same read-only connection.
    Their results are retained rather than merely printed,
    allowing future export to CSV or JSON.
    """

    inspector = inspect(conn)

    # Store each audit's results under a descriptive key.
    results = {
        "database_name": database_name,
        "table_inventory": [],
        "column_profiles": [],
        "shared_lot_fields": [],
        "referential_integrity": {},
        "bid_record_counts": {},
    }

    # ------------------------------------------------------
    # 1. TABLE INVENTORY AND COLUMN PROFILES
    # ------------------------------------------------------

    for table_name in TABLES_TO_AUDIT:

        # Fail explicitly if a required staging table is missing.
        # Otherwise, an incomplete schema could be mistaken for
        # a successfully audited database.
        if not inspector.has_table(table_name):
            raise ValueError(
                f"Missing table in {database_name}: {table_name}"
            )

        # Table names cannot be passed as ordinary SQL parameters.
        # SQLAlchemy's identifier preparer safely quotes the name.
        quoted_table_name = (
            conn.dialect.identifier_preparer.quote(table_name)
        )

        # COUNT(*) counts rows without loading them into Python.
        row_count = conn.exec_driver_sql(
            f"SELECT COUNT(*) FROM {quoted_table_name}"
        ).scalar_one()

        # Inspector returns metadata dictionaries. Extract the
        # column names for audit_column_profiles().
        columns = [
            column["name"]
            for column in inspector.get_columns(table_name)
        ]

        results["table_inventory"].append({
            "database_name": database_name,
            "table_name": table_name,
            "row_count": row_count,
            "column_count": len(columns),
        })

        # Profile every column's NULL frequency, distinct values,
        # and classification (constant, variable, etc.).
        column_results = audit_column_profiles(
            conn=conn,
            database_name=database_name,
            table_name=table_name,
            columns=columns,
            row_count=row_count,
        )

        results["column_profiles"].extend(column_results)

    # ------------------------------------------------------
    # 2. SHARED LOT FIELD CONSISTENCY
    # ------------------------------------------------------

    # Compare observations from the summary and detail
    # endpoints for lots present in both tables.
    #
    # Mismatches and asymmetric NULL values are reported
    # separately because they have different implications.
    results["shared_lot_fields"] = audit_shared_lot_fields(
        conn=conn,
        database_name=database_name,
        shared_fields=list(SHARED_LOT_FIELDS),
    )

    # ------------------------------------------------------
    # 2A. SHARED FIELD DISAGREEMENT DIAGNOSTICS
    # ------------------------------------------------------

    # Aggregate counts identify how frequently shared fields
    # disagree, but do not reveal the actual conflicting values.
    #
    # Automatically identify fields with at least one
    # non-NULL value mismatch between the summary and
    # detail endpoints to avoid hardcoding field names.

    mismatched_fields = [
        result["field_name"]
        for result in results["shared_lot_fields"]
        if int(result["mismatch_count"]) > 0
    ]

    # Only list up to 20 examples per field to avoid overwhelming output.
    for field_name in mismatched_fields:
        examples = sample_shared_field_disagreements(
            conn,
            str(field_name),
            limit=20,
        )

        print(f"\nExamples for {field_name}:")

        for example in examples:
            print(example)

    # ------------------------------------------------------
    # 3. REFERENTIAL INTEGRITY
    # ------------------------------------------------------

    # Identify missing parent records, incomplete endpoint
    # coverage, and conflicting auction IDs.
    #
    # A missing counterpart is not automatically a crawler
    # failure; interpretation occurs after auditing.
    results["referential_integrity"] = (
        audit_referential_integrity(
            conn=conn,
            database_name=database_name,
        )
    )

    # ------------------------------------------------------
    # 3A. INVESTIGATE MISSING LOT DETAILS
    # ------------------------------------------------------

    # The referential integrity audit reports how many lot
    # summaries lack corresponding detail records.
    #
    # This diagnostic query retrieves the identifiers of
    # those summaries so their collection history can be
    # investigated individually.
    #
    # No staging records are modified.

    results["summaries_without_details"] = (
        find_summaries_without_details(conn)
    )

    missing_details = results["summaries_without_details"]

    print("\n4A. SUMMARIES WITHOUT LOT DETAILS")

    if not missing_details:
        print("  None")
    else:
        print(f" Missing detail records: {len(missing_details)}")

        for lot in missing_details:
            print(
                f"  lot_id={lot['lot_id']}, "
                f"auction_id={lot['auction_id']}, "
                f"lot_number={lot['lot_number']}, "
                f"collection_run_id={lot['collection_run_id']}"
            )
  

    # ------------------------------------------------------
    # 4. BID HISTORY CONSISTENCY
    # ------------------------------------------------------

    # Compare each successful bid-history response's
    # observed_bid_record_count against the actual number
    # of bid events stored for that lot.
    results["bid_record_counts"] = (
        audit_bid_record_counts(conn)
    )

    return results


def print_audit_summary(results: dict) -> None:
    """
    Display a readable summary without discarding
    the underlying detailed audit results.
    """

    print(f"\n{'=' * 65}")
    print(f"Database: {results['database_name']}")
    print(f"{'=' * 65}")

    # Table inventory
    print("\n1. TABLE INVENTORY")

    for table in results["table_inventory"]:
        print(
            f"  {table['table_name']}: "
            f"{table['row_count']:,} rows, "
            f"{table['column_count']} columns"
        )

    # Column profile classifications
    print("\n2. COLUMN PROFILES")

    profiles = results["column_profiles"]

    classifications = Counter(
        profile["classification"]
        for profile in profiles
    )

    print(f"  Total columns profiled: {len(profiles)}")

    for classification, count in sorted(
        classifications.items()
    ):
        print(f"  {classification}: {count}")

    # Display the specific columns that warrant examination.
    # Variable columns are omitted because they are generally
    # expected to vary across auction and lot records.
    for classification in (
        "all_null",
        "strict_constant",
        "constant_when_present",
    ):
        matching_profiles = [
            profile
            for profile in profiles
            if profile["classification"] == classification
        ]

        if not matching_profiles:
            continue

        print(f"\n  {classification.upper()} COLUMNS:")

        for profile in matching_profiles:
            print(
                f"    {profile['table_name']}."
                f"{profile['column_name']}"
                f" | non-NULL: {profile['non_null_count']:,}"
                f"/{profile['row_count']:,}"
                f" | distinct: "
                f"{profile['distinct_non_null_count']}"
            )

    # Shared field comparisons
    print("\n3. SHARED LOT FIELD CONSISTENCY")

    shared_results = results["shared_lot_fields"]

    print(f"  Fields compared: {len(shared_results)}")

    for field in shared_results:

        mismatch_count = int(field["mismatch_count"])
        summary_only = int(field["summary_only_count"])
        detail_only = int(field["detail_only_count"])

        # Report both value conflicts and asymmetric NULLs.
        if mismatch_count or summary_only or detail_only:
            print(
                f"  {field['field_name']}: "
                f"{mismatch_count} mismatches, "
                f"{summary_only} summary-only, "
                f"{detail_only} detail-only"
            )

    # Referential integrity
    print("\n4. REFERENTIAL INTEGRITY")

    for check, value in results[
        "referential_integrity"
    ].items():

        if check != "database_name":
            print(f"  {check}: {value}")

    # Bid count consistency
    print("\n5. BID RECORD CONSISTENCY")

    for check, value in results[
        "bid_record_counts"
    ].items():
        print(f"  {check}: {value}")


def main() -> None:
    """
    Audit every configured monthly staging database.

    Database files are opened read-only. Results are
    accumulated across months without merging or modifying
    the underlying staging databases.
    """

    all_results = {}

    for database_name, db_path in STAGING_DATABASES.items():

        db_path = Path(db_path)

        if not db_path.is_file():
            raise FileNotFoundError(
                f"Staging database not found: {db_path}"
            )

        # SQLite URI mode=ro prevents writes through this
        # connection to the staging database.
        database_uri = (
            db_path.resolve().as_uri() + "?mode=ro"
        )

        engine = create_engine(
            "sqlite:///" + database_uri + "&uri=true"
        )

        try:
            with engine.connect() as conn:

                # Execute all audits on this database.
                results = audit_database(
                    conn=conn,
                    database_name=database_name,
                )

                # Retain detailed findings for future reporting.
                all_results[database_name] = results

                # Display the concise per-database summary.
                print_audit_summary(results)

        finally:
            # Release the SQLite connection pool and file handles.
            engine.dispose()

    print(
        f"\nCompleted audits for "
        f"{len(all_results)} staging databases."
    )


if __name__ == "__main__":
    main()
