from sqlalchemy import select
from database.staging_tables import staging_auctions

# ----------------------------------------------------------------------
# IMPORT_AUCTIONS
# ----------------------------------------------------------------------

def import_auctions(source, target, run_id_map, excluded_auction_ids):

    auction_stmt = select(staging_auctions).where(
        staging_auctions.c.auction_id.not_in(excluded_auction_ids)
    )

    for row in source.execute(auction_stmt).mappings():
        pass
