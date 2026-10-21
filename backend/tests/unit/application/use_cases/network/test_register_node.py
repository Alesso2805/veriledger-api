from typing import Any
from unittest.mock import create_autospec

import pytest

from backend.app.application.dto.node import NodeCreateRequestDTO
from backend.app.application.use_cases.network.register_node import RegisterNodeUseCase
from backend.app.domain.entities.node import Node
from backend.app.domain.errors import UnsafePeerUrlError
from backend.app.domain.ports.repositories.node_repository import NodeRepository
from backend.app.domain.ports.services.peer_url_policy import PeerUrlPolicy


@pytest.fixture
def mock_node_repo() -> Any:
    return create_autospec(NodeRepository, instance=True)


@pytest.fixture
def mock_url_policy() -> Any:
    return create_autospec(PeerUrlPolicy, instance=True)


@pytest.mark.asyncio
async def test_register_node_success(mock_node_repo: Any, mock_url_policy: Any) -> None:
    use_case = RegisterNodeUseCase(mock_node_repo, mock_url_policy)
    request = NodeCreateRequestDTO(url="http://new-node:8000")

    mock_node_repo.get_by_url.return_value = None

    async def mock_create(node: Any) -> Any:
        return node

    mock_node_repo.create.side_effect = mock_create

    result = await use_case.execute(request)

    assert result.url == "http://new-node:8000"
    assert result.status == "ACTIVE"
    mock_node_repo.create.assert_called_once()
    mock_url_policy.check.assert_awaited_once_with("http://new-node:8000")


@pytest.mark.asyncio
async def test_register_node_already_exists(mock_node_repo: Any, mock_url_policy: Any) -> None:
    use_case = RegisterNodeUseCase(mock_node_repo, mock_url_policy)
    request = NodeCreateRequestDTO(url="http://new-node:8000")

    existing = Node(id="1", url="http://new-node:8000", status="ACTIVE")
    mock_node_repo.get_by_url.return_value = existing

    with pytest.raises(ValueError, match="Node already registered"):
        await use_case.execute(request)


@pytest.mark.asyncio
async def test_a_url_the_policy_refuses_is_not_stored(mock_node_repo: Any, mock_url_policy: Any) -> None:
    mock_url_policy.check.side_effect = UnsafePeerUrlError("The peer's host is not a public address: 10.0.0.1")

    with pytest.raises(UnsafePeerUrlError):
        await RegisterNodeUseCase(mock_node_repo, mock_url_policy).execute(NodeCreateRequestDTO(url="http://10.0.0.1"))

    mock_node_repo.create.assert_not_called()
