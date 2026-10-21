from typing import Any
from unittest.mock import create_autospec

import pytest

from backend.app.application.use_cases.network.resolve_conflicts import ResolveConflictsUseCase
from backend.app.domain.entities.node import Node
from backend.app.domain.ports.repositories.block_repository import BlockRepository
from backend.app.domain.ports.repositories.node_repository import NodeRepository
from backend.app.domain.ports.services.peer_client import PeerClient

PEERS = [Node(id="1", url="http://a", status="ACTIVE"), Node(id="2", url="http://b", status="ACTIVE")]


@pytest.fixture
def mock_node_repo() -> Any:
    repo = create_autospec(NodeRepository, instance=True)
    repo.get_all.return_value = PEERS
    return repo


@pytest.fixture
def mock_block_repo() -> Any:
    return create_autospec(BlockRepository, instance=True)


@pytest.fixture
def mock_peer_client() -> Any:
    return create_autospec(PeerClient, instance=True)


def chain(length: int, prefix: str = "h") -> list[dict[str, Any]]:
    # Newest first, each block pointing at the next one
    hashes = [f"{prefix}{n}" for n in range(length - 1, -1, -1)]
    return [
        {"block_hash": h, "previous_hash": hashes[i + 1] if i + 1 < length else "0" * 64} for i, h in enumerate(hashes)
    ]


def use_case(node_repo: Any, block_repo: Any, peer_client: Any, local_length: int, chains: dict[str, Any]) -> Any:
    block_repo.count.return_value = local_length
    peer_client.fetch_chain.side_effect = lambda url: chains[url]
    return ResolveConflictsUseCase(node_repo, block_repo, peer_client)


@pytest.mark.asyncio
async def test_a_chain_no_longer_than_ours_is_not_adopted(
    mock_node_repo: Any, mock_block_repo: Any, mock_peer_client: Any
) -> None:
    resolve = use_case(
        mock_node_repo, mock_block_repo, mock_peer_client, 3, {"http://a": chain(3), "http://b": chain(2)}
    )

    assert await resolve.execute() is False
    mock_block_repo.replace_chain.assert_not_called()


@pytest.mark.asyncio
async def test_the_longest_valid_chain_among_peers_is_adopted(
    mock_node_repo: Any, mock_block_repo: Any, mock_peer_client: Any
) -> None:
    longest = chain(5, "b")
    resolve = use_case(
        mock_node_repo, mock_block_repo, mock_peer_client, 2, {"http://a": chain(4), "http://b": longest}
    )

    assert await resolve.execute() is True
    mock_block_repo.replace_chain.assert_called_once_with(longest)


@pytest.mark.asyncio
async def test_a_longer_chain_that_does_not_link_up_is_not_adopted(
    mock_node_repo: Any, mock_block_repo: Any, mock_peer_client: Any
) -> None:
    broken = chain(5)
    broken[2]["previous_hash"] = "forged"
    resolve = use_case(mock_node_repo, mock_block_repo, mock_peer_client, 1, {"http://a": broken, "http://b": None})

    assert await resolve.execute() is False
    mock_block_repo.replace_chain.assert_not_called()


@pytest.mark.asyncio
async def test_an_unreadable_peer_is_skipped(mock_node_repo: Any, mock_block_repo: Any, mock_peer_client: Any) -> None:
    resolve = use_case(mock_node_repo, mock_block_repo, mock_peer_client, 1, {"http://a": None, "http://b": chain(3)})

    assert await resolve.execute() is True


@pytest.mark.asyncio
async def test_our_length_is_the_whole_chain_not_one_page(
    mock_node_repo: Any, mock_block_repo: Any, mock_peer_client: Any
) -> None:
    # With 150 blocks of ours, a peer's 120 must not look longer, as it did when only one page was counted
    resolve = use_case(
        mock_node_repo, mock_block_repo, mock_peer_client, 150, {"http://a": chain(120), "http://b": None}
    )

    assert await resolve.execute() is False
    mock_block_repo.get_all_blocks.assert_not_called()
