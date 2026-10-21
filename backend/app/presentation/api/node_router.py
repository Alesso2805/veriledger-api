from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.application.dto.node import NodeCreateRequestDTO, NodeResponseDTO, ResolveConflictsResponseDTO
from backend.app.application.use_cases.network.register_node import RegisterNodeUseCase
from backend.app.application.use_cases.network.resolve_conflicts import ResolveConflictsUseCase
from backend.app.core.config import settings
from backend.app.domain.chain_validator import ChainValidator
from backend.app.domain.entities.user import User, UserRole
from backend.app.infrastructure.peers.httpx_peer_client import HttpxPeerClient
from backend.app.infrastructure.peers.resolving_peer_url_policy import ResolvingPeerUrlPolicy
from backend.app.infrastructure.repositories.block_repository_impl import BlockRepositoryImpl
from backend.app.infrastructure.repositories.node_repository_impl import NodeRepositoryImpl
from backend.app.infrastructure.security.sha256_hasher import SHA256HasherImpl
from backend.app.presentation.dependencies.auth import RequireRole, RequireRoleOrPeer
from backend.app.presentation.dependencies.database import DbSession

router = APIRouter(prefix="/nodes", tags=["nodes"])


@router.post("/register", response_model=NodeResponseDTO, status_code=status.HTTP_201_CREATED)
async def register_node(
    request: NodeCreateRequestDTO,
    db: DbSession,
    current_user: User = Depends(RequireRole([UserRole.ADMIN])),
) -> NodeResponseDTO:
    node_repo = NodeRepositoryImpl(db)
    use_case = RegisterNodeUseCase(node_repo, ResolvingPeerUrlPolicy())

    try:
        node = await use_case.execute(request)
        return NodeResponseDTO(id=node.id, url=node.url, status=node.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("", response_model=list[NodeResponseDTO])
async def get_nodes(
    db: DbSession,
) -> list[NodeResponseDTO]:
    node_repo = NodeRepositoryImpl(db)
    nodes = await node_repo.get_all()
    return [NodeResponseDTO(id=n.id, url=n.url, status=n.status) for n in nodes]


@router.post("/resolve", response_model=ResolveConflictsResponseDTO)
async def resolve_conflicts(
    db: DbSession,
    # A peer that mined a block asks the others to resolve
    current_user: User | None = Depends(RequireRoleOrPeer([UserRole.ADMIN])),
) -> ResolveConflictsResponseDTO:
    node_repo = NodeRepositoryImpl(db)
    block_repo = BlockRepositoryImpl(db)
    # A peer's blocks are checked against this node's own difficulty (SPEC › Valid chain)
    validator = ChainValidator(SHA256HasherImpl(), difficulty=settings.mining_difficulty)
    use_case = ResolveConflictsUseCase(node_repo, block_repo, HttpxPeerClient(), validator)

    replaced = await use_case.execute()
    message = "Our chain was replaced" if replaced else "Our chain is authoritative"
    return ResolveConflictsResponseDTO(message=message, replaced=replaced)
