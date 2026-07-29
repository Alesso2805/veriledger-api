import pytest
from unittest.mock import create_autospec, patch, MagicMock

from backend.app.application.use_cases.network.resolve_conflicts import ResolveConflictsUseCase
from backend.app.domain.entities.node import Node
from backend.app.domain.ports.repositories.node_repository import NodeRepository
from backend.app.domain.ports.repositories.block_repository import BlockRepository

@pytest.fixture
def mock_node_repo():
    return create_autospec(NodeRepository, instance=True)

@pytest.fixture
def mock_block_repo():
    return create_autospec(BlockRepository, instance=True)

@pytest.mark.asyncio
async def test_resolve_conflicts_no_replacement(mock_node_repo, mock_block_repo):
    use_case = ResolveConflictsUseCase(mock_node_repo, mock_block_repo)
    
    mock_node_repo.get_all.return_value = [Node(id="1", url="http://test", status="ACTIVE")]
    # Our chain has length 5
    mock_block_repo.get_all_blocks.return_value = [MagicMock()] * 5
    
    # Remote chain has length 3, so we won't replace
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"total": 3, "items": []}
    
    with patch("httpx.AsyncClient.get", return_value=mock_response):
        result = await use_case.execute()
        
    assert result is False
    mock_block_repo.replace_chain.assert_not_called()

@pytest.mark.asyncio
async def test_resolve_conflicts_replacement(mock_node_repo, mock_block_repo):
    use_case = ResolveConflictsUseCase(mock_node_repo, mock_block_repo)
    
    mock_node_repo.get_all.return_value = [Node(id="1", url="http://test", status="ACTIVE")]
    # Our chain has length 5
    mock_block_repo.get_all_blocks.return_value = [MagicMock()] * 5
    
    # Remote chain has length 10
    valid_chain = [
        {"block_hash": "hash2", "previous_hash": "hash1"},
        {"block_hash": "hash1", "previous_hash": "hash0"}
    ]
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"total": 10, "items": valid_chain}
    
    with patch("httpx.AsyncClient.get", return_value=mock_response):
        result = await use_case.execute()
        
    assert result is True
    mock_block_repo.replace_chain.assert_called_once_with(valid_chain)
