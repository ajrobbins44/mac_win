from sqlalchemy import select
from database.staging_tables import staging_lot_summaries, staging_lot_details

# ----------------------------------------------------------------------
# IMPORT_AUCTION_LOTS
# ----------------------------------------------------------------------

def import_auction_lots(source, target, run_id_map, excluded_auction_ids):

    summary_stmt = select(staging_lot_summaries).where(
        staging_lot_summaries.c.auction_id.not_in(excluded_auction_ids)
    )
    detail_stmt = select(staging_lot_details).where(
        staging_lot_details.c.auction_id.not_in(excluded_auction_ids)
    )

    for row in source.execute(summary_stmt).mappings():
        pass

    for row in source.execute(detail_stmt).mappings():
        pass