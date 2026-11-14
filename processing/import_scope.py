from sqlalchemy import select

from database.staging_tables import (
    staging_auctions,
    staging_lot_details,
    staging_lot_summaries,
)


def find_excluded_auction_ids(conn, *, excluded_date=None):
    """Find auction IDs whose auction number contains the excluded date."""
    if excluded_date is None:
        return set()

    date_code = excluded_date.strftime("%y%m-%d")

    stmt = select(staging_auctions.c.auction_id).where(
        staging_auctions.c.auction_number.contains(date_code)
    )
    return set(conn.execute(stmt).scalars())


def retained_lot_ids_query(excluded_auction_ids):
    """Select lot IDs belonging to retained auctions in this staging file."""
    retained_auctions = select(staging_auctions.c.auction_id).where(
        staging_auctions.c.auction_id.not_in(excluded_auction_ids)
    )

    summary_lots = select(staging_lot_summaries.c.lot_id).where(
        staging_lot_summaries.c.auction_id.in_(retained_auctions)
    )
    detail_lots = select(staging_lot_details.c.lot_id).where(
        staging_lot_details.c.auction_id.in_(retained_auctions)
    )

    return summary_lots.union(detail_lots)