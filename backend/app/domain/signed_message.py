import json
import re

# Exactly 8 decimals and no leading zeros, so an amount has one spelling; at most 10 integer
# digits, the size of the numeric(18, 8) columns (ADR-0004)
AMOUNT = re.compile(r"^(0|[1-9]\d{0,9})\.\d{8}$")

# The largest integer JavaScript holds exactly; past it the webapp could write the nonce differently
MAX_NONCE = 2**53 - 1


def next_nonce(last_nonce: int | None) -> int:
    """A sender's first nonce is 1, and each one after is one more than the last accepted (ADR-0004)."""
    return (last_nonce or 0) + 1


def build_signed_message(
    *, sender_address: str, receiver_address: str, amount: str, fee: str, nonce: int, payload: str | None = None
) -> str:
    """The canonical message a transaction's signature covers (ADR-0004); its UTF-8 bytes are what gets signed."""
    for name, value in (("amount", amount), ("fee", fee)):
        # fullmatch: with match, "$" would also accept a trailing newline
        if not AMOUNT.fullmatch(value):
            raise ValueError(f"{name} must be a decimal string with exactly 8 decimals, like '10.00000000'")
    if isinstance(nonce, bool) or not isinstance(nonce, int) or not 1 <= nonce <= MAX_NONCE:
        raise ValueError(f"nonce must be an integer from 1 to {MAX_NONCE}")
    fields: dict[str, str | int] = {
        "amount": amount,
        "fee": fee,
        "nonce": nonce,
        "receiver_address": receiver_address,
        "sender_address": sender_address,
    }
    if payload is not None:
        fields["payload"] = payload
    return json.dumps(fields, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
