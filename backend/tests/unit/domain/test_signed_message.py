import pytest

from backend.app.domain.signed_message import MAX_NONCE, build_signed_message, next_nonce

SENDER = "aa" * 32
RECEIVER = "bb" * 32


def message(amount: str = "1.00000000", fee: str = "0.00000000", nonce: int = 1) -> str:
    return build_signed_message(sender_address=SENDER, receiver_address=RECEIVER, amount=amount, fee=fee, nonce=nonce)


def test_keys_are_sorted_with_no_whitespace_and_payload_is_omitted_when_absent() -> None:
    assert message(amount="1.50000000", nonce=7) == (
        f'{{"amount":"1.50000000","fee":"0.00000000","nonce":7,"receiver_address":"{RECEIVER}","sender_address":"{SENDER}"}}'
    )


@pytest.mark.parametrize(
    "amount",
    [
        "10",
        "10.0",
        "10.0000000",
        "10.000000001",
        "-1.00000000",
        "+1.00000000",
        "1e1",
        "010.00000000",
        "12345678901.00000000",
        "10.00000000\n",
        "",
    ],
)
def test_an_amount_with_another_spelling_is_refused(amount: str) -> None:
    with pytest.raises(ValueError, match="exactly 8 decimals"):
        message(amount=amount)


def test_a_fee_with_another_spelling_is_refused() -> None:
    with pytest.raises(ValueError, match="fee must be"):
        message(fee="0.1")


@pytest.mark.parametrize("nonce", [0, -1, True, MAX_NONCE + 1, 1.0, "1"])
def test_a_nonce_outside_the_integers_both_sides_write_alike_is_refused(nonce: object) -> None:
    with pytest.raises(ValueError, match="nonce must be"):
        message(nonce=nonce)  # type: ignore[arg-type]


def test_the_largest_nonce_javascript_holds_exactly_is_accepted() -> None:
    assert f'"nonce":{MAX_NONCE},' in message(nonce=MAX_NONCE)


def test_the_first_nonce_is_one_and_each_next_is_one_more() -> None:
    assert (next_nonce(None), next_nonce(1), next_nonce(41)) == (1, 2, 42)
