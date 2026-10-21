import asyncio
import ipaddress
import socket
from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

from backend.app.core.config import settings
from backend.app.domain.errors import UnsafePeerUrlError
from backend.app.domain.ports.services.peer_url_policy import PeerUrlPolicy

Resolver = Callable[[str], Awaitable[list[str]]]


async def resolve_host(host: str) -> list[str]:
    infos = await asyncio.get_running_loop().getaddrinfo(host, None, type=socket.SOCK_STREAM)
    return [str(info[4][0]) for info in infos]


def is_public(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    # is_global leaves out loopback, private, link-local, shared and reserved ranges, but not multicast.
    # An IPv4 address written as IPv6 (::ffff:127.0.0.1) is judged as the IPv4 address it carries.
    return address.is_global and not address.is_multicast


class ResolvingPeerUrlPolicy(PeerUrlPolicy):
    def __init__(self, allow_private: bool | None = None, resolve: Resolver = resolve_host):
        self._allow_private = settings.allow_private_peers if allow_private is None else allow_private
        self._resolve = resolve

    async def check(self, url: str) -> None:
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https"):
            raise UnsafePeerUrlError("A peer URL starts with http:// or https://")
        host = parts.hostname
        if not host:
            raise UnsafePeerUrlError("A peer URL needs a host")
        if self._allow_private:
            return

        try:
            addresses = [ipaddress.ip_address(host)]
        except ValueError:
            try:
                addresses = [ipaddress.ip_address(answer) for answer in await self._resolve(host)]
            except (OSError, ValueError) as e:
                raise UnsafePeerUrlError(f"The peer's host does not resolve: {host}") from e
        # Every answer, since the connection may use any of them
        if not addresses or not all(is_public(address) for address in addresses):
            raise UnsafePeerUrlError(
                f"The peer's host is not a public address: {host}. "
                "Loopback, private, link-local and reserved addresses need ALLOW_PRIVATE_PEERS"
            )
