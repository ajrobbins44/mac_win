
# ---------------------------------------------------------
# VALIDATE_POSITIVE_INTEGERS
# ---------------------------------------------------------

def validate_positive_integers(row, fields) -> dict[str, int]:
    """Return the specified fields after validating positive integer values."""
    validated = {}

    for field in fields:
        value = row[field]

        if type(value) is not int or value <= 0:
            raise ValueError(
                f"{field} must be a positive integer, got {value!r}"
            )

        validated[field] = value

    return validated

# ---------------------------------------------------------
# VALIDATE_NONEMPTY_TEXT
# ---------------------------------------------------------

def validate_nonempty_text(row, fields) -> None:
    """Require each specified field to contain text beyond whitespace."""
    for field in fields:
        value = row[field]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"{field} must contain nonempty text, got {value!r}"
            )
        
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