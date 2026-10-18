from pathlib import Path
from datetime import date, timedelta
import pandas as pd


def load_patterns(
    input_path: Path,
    target_building_ids: set[int],
) -> dict[str, tuple[str, ...]]:
    """Load observed auction-number patterns from a CSV file."""
    
    pattern_behavior = pd.read_csv(input_path)

    # Locate prefix + suffix patterns for target buildings
    pattern_rows = (
        # Keep rows whose building_id is in the target building IDs 
        # and retain the prefix + suffix columns
        pattern_behavior.loc[
            pattern_behavior["building_id"].isin(target_building_ids),
            ["prefix", "suffix"],
        ]
        .sort_values(["prefix", "suffix"])
        .drop_duplicates() # Doesn't hurt to be careful
        .dropna()
    )

    # Construct the patterns dictionary
    patterns: dict[str, tuple[str, ...]] = {}

    for prefix_value, group in pattern_rows.groupby(
    "prefix",
    sort=True
    ):
        # Ensure all prefixes and suffixes are strings
        prefix = str(prefix_value)

        suffixes: tuple[str, ...] = tuple(
            str(suffix)
            for suffix in group["suffix"].tolist()
        )

        patterns[prefix] = suffixes

    return patterns

def date_range(
    start_date: date,
    end_date: date,
):
    """Yield every date from start_date through end_date."""
    
    current_date = start_date

    # Return all dates one at a time from the start date
    # until the end date
    while current_date <= end_date:
        yield current_date
        current_date += timedelta(days=1)


def generate_auction_candidates(
    start_date: date,
    end_date: date,
    pattern_file: Path,
    target_building_ids: set[int],
):
    """Yield candidate auction numbers for a date range."""

    patterns = load_patterns(
        input_path=pattern_file,
        target_building_ids=target_building_ids,
    )

    for candidate_date in date_range(start_date, end_date):
        # Format date as shown in auction number identifier
        date_formatted = candidate_date.strftime('%y%m-%d')

        for prefix, suffixes in patterns.items():
            for suffix in suffixes:
                yield {
                    "auction_number": (
                        f"{prefix}{date_formatted}-{suffix}"
                    ),
                    "candidate_close_date": (
                        candidate_date.isoformat()
                    ),
                    "prefix": prefix,
                    "suffix": suffix,
                }

