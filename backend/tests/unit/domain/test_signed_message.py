import pytest

from backend.app.domain.signed_message import build_signed_message

SENDER = "aa" * 32
RECEIVER = "bb" * 32


def test_keys_are_sorted_with_no_whitespace_and_payload_is_omitted_when_absent() -> None:
    message = build_signed_message(
        sender_address=SENDER, receiver_address=RECEIVER, amount="1.50000000", fee="0.00000000"
    )

    assert (
        message
        == f'{{"amount":"1.50000000","fee":"0.00000000","receiver_address":"{RECEIVER}","sender_address":"{SENDER}"}}'
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
        build_signed_message(sender_address=SENDER, receiver_address=RECEIVER, amount=amount, fee="0.00000000")


def test_a_fee_with_another_spelling_is_refused() -> None:
    with pytest.raises(ValueError, match="fee must be"):
        build_signed_message(sender_address=SENDER, receiver_address=RECEIVER, amount="1.00000000", fee="0.1")
