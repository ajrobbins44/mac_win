from collections import Counter
from pathlib import Path
from pprint import pprint

from sqlalchemy import (
    create_engine,
    inspect,
    select,
)

from processing.constants import (
    STAGING_DATABASES,
    SHARED_LOT_FIELDS,
    TABLES_TO_AUDIT,
)

from processing.audit.staging_audits import (
    audit_auction_id_overlap,
    audit_column_profiles,
    audit_shared_lot_fields,
    audit_referential_integrity,
    audit_bid_record_counts,
    audit_auction_id_overlap,

    # Helper functions added after the initial audit results
    # revealed a need for further investigation of specific issues.
    sample_shared_field_disagreements,
    find_summaries_without_details,
)

from database.staging_tables import (
    staging_auctions,
)

# ------------------------------------------------------
# AUDIT_DATABASE
# ------------------------------------------------------

def audit_database(
    conn,
    database_name: str,
) -> dict:
    """
    Execute the complete audit suite for one staging database.

    All audit functions share the same read-only connection.
    Their results are often stored under 'mac_win/runtime/audits/staging'
    for future reference.
    """

    inspector = inspect(conn)

    # Store the audit findings for one month under 
    # a descriptive key with nested dictionaries or
    # arrays to hold its values.
    results = {
        "database_name": database_name,
        "table_inventory": [],
        "column_profiles": [],
        "shared_lot_fields": [],
        "referential_integrity": {},
        "bid_record_counts": {},
        "auction_identifiers": [],
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

        # Append one dictionary for this table to the table inventory list.
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

        # Each helper function result is a list of dictionaries.
        # Extend adds each dictionary from the column_results list 
        # to the column_profiles list.
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

    # Aggregate counts only identify how frequently shared 
    # fields disagree.
    #
    # Find actual conflicting values by identifying fields 
    # with at least one non-NULL value mismatch.

    # Extract field names that have at least one mismatch that needs a
    # follow-up query to retrieve sample rows for each mismatched field.
    mismatched_fields = [
        result["field_name"]
        for result in results["shared_lot_fields"]
        if int(result["mismatch_count"]) > 0
    ]

    results["shared_lot_fields_disagreement_samples"] = {}
    
    # Only list up to 10 examples per field to avoid overwhelming output.
    for field_name in mismatched_fields:
        samples = sample_shared_field_disagreements(
            conn,
            str(field_name),
            limit=10,
        )

        # Save samples inside the nested dictionary for the current field.
        results["shared_lot_fields_disagreement_samples"][field_name] = samples

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
    # summaries lack corresponding detail records. Missing
    # lot details are the only flagged issues in audits 
    # conducted so far.
    #
    # This diagnostic query retrieves the identifiers of
    # those summaries.
    #
    # No staging records are modified.

    # Retrieve the summaries that lack corresponding detail records
    # as a list of dictionaries for each summary.
    results["summaries_without_details"] = (
        find_summaries_without_details(conn)
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

    # ------------------------------------------------------
    # 5. AUCTION IDENTIFIERS
    # ------------------------------------------------------
    
    stmt = select(
        staging_auctions.c.auction_id,
        staging_auctions.c.auction_number,
    )
    results["auction_identifiers"] = conn.execute(stmt).mappings().all()

    # Return the complete results dictionary for one monthly database audit.
    return results

# ------------------------------------------------------
# AUDIT_ALL_DATABASES
# ------------------------------------------------------

def audit_all_databases() -> dict:
  
    # Initialize a dictionary to store all audit results
    # under its respective database name as the key.
    all_results = {}

    for database_name, db_path in STAGING_DATABASES.items():

        # STAGING_DATABASES maps each report label (the database name) 
        # to its corresponding file path.
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

        # uri=true is required to use read-only mode with SQLite URIs.
        engine = create_engine(
            "sqlite:///" + database_uri + "&uri=true"
        )

        try:
            # Scoped to each monthly database.
            with engine.connect() as conn:

                # Execute all audits on this database.
                results = audit_database(
                    conn=conn,
                    database_name=database_name,
                )
                all_results[database_name] = results

        finally:
            # Release the SQLite connection pool and file handles.
            engine.dispose()

    auctions_by_database = {
        database_name: results["auction_identifiers"]
        for database_name, results in all_results.items()
    }

    overlaps = audit_auction_id_overlap(auctions_by_database)

    # Give each monthly report the overlaps that involve its database.
    for database_name, results in all_results.items():
        results["auction_id_overlap"] = {
            auction_id: sources
            for auction_id, sources in overlaps.items()
            if database_name in sources
        }

    return all_results

    

# ------------------------------------------------------
# PRINT_AUDIT_SUMMARY
# ------------------------------------------------------

def print_audit_summary(results: dict) -> None:
    """
    Display a readable summary without discarding
    the underlying detailed audit results.
    """

    # Output header for each database's audit summary.
    print(f"\n{'=' * 65}")
    print(f"Database: {results['database_name']}")
    print(f"{'=' * 65}")

    # Table inventory
    print("\n1. TABLE INVENTORY AND COLUMN PROFILES")

    for table in results["table_inventory"]:
        print(
            f"  {table['table_name']}: "
            f"{table['row_count']:,} rows, "
            f"{table['column_count']} columns"
        )

    profiles = results["column_profiles"]

    # Count how many columns fall into each classification.
    classifications = Counter(
        profile["classification"]
        for profile in profiles
    )

    print(f"  \nTotal columns profiled: {len(profiles)}")

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
        "variable_with_nulls",
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
    print("\n2. SHARED LOT FIELD CONSISTENCY")

    shared_results = results["shared_lot_fields"]

    print(f"  Fields compared: {len(shared_results)}\n")

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

    # items() will yield each field name and its corresponding list of example disagreements.
    for field_name, examples in results["shared_lot_fields_disagreement_samples"].items():
            print(f"\n  Examples for {field_name}:")
            for example in examples:
                print(f"    {example}")

    # Referential integrity
    print("\n3. REFERENTIAL INTEGRITY")

    for check, value in results[
        "referential_integrity"
    ].items():

        if check != "database_name":
            print(f"  {check}: {value}")

    if results["summaries_without_details"]:
        missing_summary_details = results["summaries_without_details"]
        print(f" \nMissing summary detail records: {len(missing_summary_details)}")

        for lot in missing_summary_details:
            print(
                f"  lot_id={lot['lot_id']}, "
                f"auction_id={lot['auction_id']}, "
                f"lot_number={lot['lot_number']}, "
                f"collection_run_id={lot['collection_run_id']}"
            )

    # Bid count consistency
    print("\n4. BID RECORD CONSISTENCY")

    for check, value in results[
        "bid_record_counts"
    ].items():
        print(f"  {check}: {value}")


# ------------------------------------------------------
# PRINT_ALL_DATABASES_AUDIT_SUMMARY
# ------------------------------------------------------

def print_all_databases_audit_summary(all_results):
    table_totals = Counter()
    shared_totals = {}

    for database_name, results in all_results.items():
        for table in results["table_inventory"]:
            table_totals[table["table_name"]] += table["row_count"]

        for field in results["shared_lot_fields"]:
            field_name = field["field_name"]
            counts = shared_totals.setdefault(field_name, Counter())

            for key in (
                "mismatch_count",
                "summary_only_count",
                "detail_only_count",
            ):
                counts[key] += int(field[key])

    print(f"\nCOMBINED STAGING AUDIT ({len(all_results)} databases)")

    print("\n1. TABLE ROW TOTALS")
    for table_name, count in sorted(table_totals.items()):
        print(f"  {table_name}: {count:,} rows")

    print("\n2. SHARED LOT FIELD CONSISTENCY")
    for field_name, counts in sorted(shared_totals.items()):
        if any(counts.values()):
            print(
                f"  {field_name}: "
                f"{counts['mismatch_count']:,} mismatches, "
                f"{counts['summary_only_count']:,} summary-only, "
                f"{counts['detail_only_count']:,} detail-only"
            )

    print("\n3. CROSS-DATABASE AUCTION ID OVERLAP")

    overlaps = {}
    for monthly_results in all_results.values():
        overlaps.update(monthly_results["auction_id_overlap"])
    
    print(f"  Auction IDs found in multiple databases: {len(overlaps):,}")

    for auction_id, sources in overlaps.items():
        locations = ", ".join(
            f"{database_name} ({auction_number})"
            for database_name, auction_number in sorted(sources.items())
        )
        print(f"  {auction_id}: {locations}")
            
# ------------------------------------------------------
# MAIN
# ------------------------------------------------------
def main() -> None:
    """
    Audit every configured monthly staging database.

    Database files are opened read-only. Results are
    accumulated across months without merging or modifying
    the underlying staging databases.
    """

    all_results = audit_all_databases()

    for results in all_results.values():
        # Display the concise per-database summary.
        print_audit_summary(results)

    print(
        f"\nCompleted audits for "
        f"{len(all_results)} staging databases."
    )

    print_all_databases_audit_summary(all_results)

    print("\nEnd of combined audit summary.")


if __name__ == "__main__":
    main()
