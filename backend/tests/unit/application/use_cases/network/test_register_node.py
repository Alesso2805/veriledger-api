import pytest
from unittest.mock import create_autospec, AsyncMock

from backend.app.application.use_cases.network.register_node import RegisterNodeUseCase
from backend.app.application.dto.node import NodeCreateRequestDTO
from backend.app.domain.entities.node import Node
from backend.app.domain.ports.repositories.node_repository import NodeRepository

@pytest.fixture
def mock_node_repo():
    return create_autospec(NodeRepository, instance=True)

@pytest.mark.asyncio
async def test_register_node_success(mock_node_repo):
    use_case = RegisterNodeUseCase(mock_node_repo)
    request = NodeCreateRequestDTO(url="http://new-node:8000")
    
    mock_node_repo.get_by_url.return_value = None
    
    async def mock_create(node):
        return node
    mock_node_repo.create.side_effect = mock_create
    
    result = await use_case.execute(request)
    
    assert result.url == "http://new-node:8000"
    assert result.status == "ACTIVE"
    mock_node_repo.create.assert_called_once()

@pytest.mark.asyncio
async def test_register_node_already_exists(mock_node_repo):
    use_case = RegisterNodeUseCase(mock_node_repo)
    request = NodeCreateRequestDTO(url="http://new-node:8000")
    
    existing = Node(id="1", url="http://new-node:8000", status="ACTIVE")
    mock_node_repo.get_by_url.return_value = existing
    
    with pytest.raises(ValueError, match="Node already registered"):
        await use_case.execute(request)
