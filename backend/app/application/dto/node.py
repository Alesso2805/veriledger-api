from pydantic import BaseModel

class NodeCreateRequestDTO(BaseModel):
    url: str

class NodeResponseDTO(BaseModel):
    id: str
    url: str
    status: str
