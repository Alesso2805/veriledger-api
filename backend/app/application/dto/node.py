from pydantic import BaseModel


class NodeCreateRequestDTO(BaseModel):
    url: str


class NodeResponseDTO(BaseModel):
    id: str
    url: str
    status: str


class ResolveConflictsResponseDTO(BaseModel):
    message: str
    replaced: bool
