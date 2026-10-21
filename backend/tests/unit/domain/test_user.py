from datetime import UTC, datetime, timedelta

from backend.app.domain.entities.user import User, UserRole

NOW = datetime(2026, 10, 21, 18, 0, tzinfo=UTC)


def account(email: str | None, expires_at: datetime | None = None) -> User:
    return User(
        id="9f1c2a7e-5b1d-4c3a-8e2f-00000000c4fe",
        email=email,
        password_hash=None,
        role=UserRole.TRADER,
        created_at=NOW,
        updated_at=NOW,
        expires_at=expires_at,
    )


def test_a_normal_account_is_named_by_its_email_and_never_expires() -> None:
    normal = account("trader@example.com")

    assert normal.display_name == "trader@example.com"
    assert not normal.is_expired(NOW + timedelta(days=3650))


def test_a_demo_account_is_a_guest_named_after_its_id_until_its_expiry() -> None:
    demo = account(None, expires_at=NOW + timedelta(hours=24))

    assert demo.display_name == "Guest C4FE"
    assert not demo.is_expired(NOW + timedelta(hours=23, minutes=59))
    assert demo.is_expired(NOW + timedelta(hours=24))
