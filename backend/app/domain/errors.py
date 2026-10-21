class NonceConflictError(Exception):
    """A transaction's nonce is not the next one for its sender: reused or skipped (409, ADR-0004).

    Not a ValueError, so that no handler of ValueError turns it into a 400.
    """
