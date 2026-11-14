from sqlalchemy import select
from database.staging_tables import staging_lot_bid_histories

# ----------------------------------------------------------------------
# IMPORT_BID_HISTORY
# ----------------------------------------------------------------------

def import_bid_history(source, target, run_id_map, retained_lots):

    history_stmt = select(staging_lot_bid_histories).where(
        staging_lot_bid_histories.c.lot_id.in_(retained_lots)
    )

    for row in source.execute(history_stmt).mappings():
        pass
