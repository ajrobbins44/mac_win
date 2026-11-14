from sqlalchemy import select
from database.staging_tables import staging_bid_events

# ----------------------------------------------------------------------
# IMPORT_BID_EVENTS
# ----------------------------------------------------------------------

def import_bid_events(source, target, run_id_map, retained_lots):

    event_stmt = select(staging_bid_events).where(
        staging_bid_events.c.lot_id.in_(retained_lots)
    )

    for row in source.execute(event_stmt).mappings():
        pass
