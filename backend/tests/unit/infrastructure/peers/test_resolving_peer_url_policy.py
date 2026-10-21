import socket

import pytest

from backend.app.core.config import settings
from backend.app.domain.errors import UnsafePeerUrlError
from backend.app.infrastructure.peers.resolving_peer_url_policy import ResolvingPeerUrlPolicy

PUBLIC_V4 = "93.184.215.14"
PUBLIC_V6 = "2606:2800:21f:cb07:6820:80da:af6b:8b2c"

ANSWERS = {
    "peer.test": [PUBLIC_V4, PUBLIC_V6],
    # One private answer among public ones, as a host aimed at the inside would give
    "rebind.test": [PUBLIC_V4, "10.0.0.7"],
    "empty.test": [],
}


async def fake_resolve(host: str) -> list[str]:
    if host not in ANSWERS:
        raise socket.gaierror(socket.EAI_NONAME, "Name or service not known")
    return ANSWERS[host]


async def never_resolve(host: str) -> list[str]:
    raise AssertionError(f"{host} should not have been resolved")


def policy(allow_private: bool = False) -> ResolvingPeerUrlPolicy:
    return ResolvingPeerUrlPolicy(allow_private=allow_private, resolve=fake_resolve)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    ["http://peer.test", "https://peer.test:8443/api", f"http://{PUBLIC_V4}:8000", "http://[2606:4700:4700::1111]"],
)
async def test_an_http_url_whose_every_address_is_public_is_accepted(url: str) -> None:
    await policy().check(url)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("url", "reason"),
    [
        ("ftp://peer.test", "http:// or https://"),
        ("file:///etc/passwd", "http:// or https://"),
        ("peer.test:8000", "http:// or https://"),
        ("http:///nodes", "needs a host"),
        ("http://127.0.0.1:8000", "not a public address"),
        ("http://0.0.0.0", "not a public address"),
        ("http://10.1.2.3", "not a public address"),
        ("http://172.16.0.1", "not a public address"),
        ("http://192.168.1.10", "not a public address"),
        ("http://169.254.169.254/latest/meta-data/", "not a public address"),
        ("http://100.64.0.1", "not a public address"),
        ("http://224.0.0.1", "not a public address"),
        ("http://[::1]:8000", "not a public address"),
        ("http://[fe80::1]", "not a public address"),
        ("http://[fc00::1]", "not a public address"),
        ("http://[::ffff:127.0.0.1]", "not a public address"),
        ("http://[::ffff:224.0.0.1]", "not a public address"),
        ("http://rebind.test", "not a public address"),
        ("http://empty.test", "not a public address"),
        ("http://unknown.test", "does not resolve"),
    ],
)
async def test_any_other_url_is_refused_with_its_reason(url: str, reason: str) -> None:
    with pytest.raises(UnsafePeerUrlError, match=reason):
        await policy().check(url)


@pytest.mark.asyncio
async def test_allowing_private_peers_lifts_the_address_rule_without_resolving() -> None:
    allowing = ResolvingPeerUrlPolicy(allow_private=True, resolve=never_resolve)

    await allowing.check("http://127.0.0.1:8001")
    await allowing.check("http://peer.example")
    with pytest.raises(UnsafePeerUrlError, match="http:// or https://"):
        await allowing.check("ftp://127.0.0.1")


@pytest.mark.asyncio
async def test_the_default_comes_from_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "allow_private_peers", True)
    await ResolvingPeerUrlPolicy(resolve=never_resolve).check("http://10.0.0.1")

    monkeypatch.setattr(settings, "allow_private_peers", False)
    with pytest.raises(UnsafePeerUrlError):
        await ResolvingPeerUrlPolicy(resolve=never_resolve).check("http://10.0.0.1")


@pytest.mark.asyncio
async def test_the_real_resolver_sees_that_localhost_is_this_machine() -> None:
    with pytest.raises(UnsafePeerUrlError, match="not a public address"):
        await ResolvingPeerUrlPolicy(allow_private=False).check("http://localhost:8000")
