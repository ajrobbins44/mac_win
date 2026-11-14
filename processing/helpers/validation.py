
# ---------------------------------------------------------
# VERIFY_KEYS_MATCH
# ---------------------------------------------------------

def verify_keys_match(expected_keys, actual_keys, *, context):
    """
    Verify that the actual keys match the expected keys.

    Args:
        expected_keys (iterable): The expected set of keys.
        actual_keys (iterable): The actual set of keys.
        context (str): A descriptive context for the error message.
        
    """
    expected = set(expected_keys)
    actual = set(actual_keys)

    missing = expected - actual
    unexpected = actual - expected

    if missing or unexpected:
        raise ValueError(
            f"{context}: {len(missing)} missing keys, "
            f"{len(unexpected)} unexpected keys. "
            f"Missing examples: {list(missing)[:5]}. "
            f"Unexpected examples: {list(unexpected)[:5]}."
        )