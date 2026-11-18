from sqlalchemy import select

from processing.tables import collection_runs

# ------------------------------------------------------
# AUDIT_TABLE_DATES
# ------------------------------------------------------

def audit_table_dates(conn, table, *, columns, id_column, validate_row):

    selected_columns = [getattr(table.c, col) for col in columns]

    stmt = select(
        table.c[id_column],
        *(table.c[col] for col in columns),
    ).order_by(table.c[id_column])

    rows_checked = 0
    issues = []

    for row in conn.execute(stmt).mappings():
        rows_checked += 1

        try:
            validate_row(row)
        except ValueError as exc:
            issues.append({
                id_column: row[id_column],
                "error": str(exc),
            })

    return {"rows_checked": rows_checked, "issues": issues}

