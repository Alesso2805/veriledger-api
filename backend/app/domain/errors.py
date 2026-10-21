class NonceConflictError(Exception):
    """A transaction's nonce is not the next one for its sender: reused or skipped (409, ADR-0004).

    Not a ValueError, so that no handler of ValueError turns it into a 400.
    """


class UnsafePeerUrlError(ValueError):
    """A peer URL this node must not call: not http(s), or not a public address (400, SPEC › Peer URLs)."""


class BlockHeightTakenError(Exception):
    """Another request stored a block at this block's height while it was mined (409, VLA-17).

    Not a ValueError, so that no handler of ValueError turns it into a 400.
    """
