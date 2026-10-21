from datetime import UTC, datetime, timedelta

from backend.app.infrastructure.security.jwt_service import JWTTokenService


def test_a_demo_token_ends_with_its_account_and_says_it_is_a_demo() -> None:
    service = JWTTokenService()
    expires_at = datetime.now(UTC) + timedelta(hours=24)

    claims = service.verify_token(service.create_access_token("user-1", "trader", expires_at=expires_at, demo=True))

    assert (claims["sub"], claims["role"], claims["demo"]) == ("user-1", "trader", True)
    assert claims["exp"] == int(expires_at.timestamp())


def test_a_normal_token_carries_no_demo_claim() -> None:
    service = JWTTokenService()

    claims = service.verify_token(service.create_access_token("user-1", "admin"))

    assert "demo" not in claims
