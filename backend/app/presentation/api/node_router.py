from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from backend.app.application.dto.node import NodeCreateRequestDTO, NodeResponseDTO
from backend.app.application.use_cases.network.register_node import RegisterNodeUseCase
from backend.app.application.use_cases.network.resolve_conflicts import ResolveConflictsUseCase
from backend.app.domain.entities.user import User
from backend.app.infrastructure.database import get_db_session
from backend.app.infrastructure.repositories.node_repository_impl import NodeRepositoryImpl
from backend.app.infrastructure.repositories.block_repository_impl import BlockRepositoryImpl
from backend.app.presentation.dependencies.auth import get_current_user

router = APIRouter(prefix="/nodes", tags=["nodes"])

@router.post("/register", response_model=NodeResponseDTO, status_code=status.HTTP_201_CREATED)
async def register_node(
    request: NodeCreateRequestDTO,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> NodeResponseDTO:
    node_repo = NodeRepositoryImpl(db)
    use_case = RegisterNodeUseCase(node_repo)
    
    try:
        node = await use_case.execute(request)
        return NodeResponseDTO(id=node.id, url=node.url, status=node.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("", response_model=List[NodeResponseDTO])
async def get_nodes(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> List[NodeResponseDTO]:
    node_repo = NodeRepositoryImpl(db)
    nodes = await node_repo.get_all()
    return [NodeResponseDTO(id=n.id, url=n.url, status=n.status) for n in nodes]

@router.post("/resolve")
async def resolve_conflicts(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    node_repo = NodeRepositoryImpl(db)
    block_repo = BlockRepositoryImpl(db)
    use_case = ResolveConflictsUseCase(node_repo, block_repo)
    
    replaced = await use_case.execute()
    return {
        "message": "Our chain was replaced" if replaced else "Our chain is authoritative",
        "replaced": replaced
    }
