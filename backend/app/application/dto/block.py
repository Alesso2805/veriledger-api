from datetime import datetime

from pydantic import BaseModel

from backend.app.application.dto.transaction import TransactionResponseDTO


class MineBlockRequestDTO(BaseModel):
    miner_address: str


class BlockResponseDTO(BaseModel):
    id: str
    block_number: int
    previous_hash: str
    timestamp: datetime
    nonce: int
    block_hash: str
    transaction_ids: list[str]


class FullBlockResponseDTO(BaseModel):
    id: str
    block_number: int
    previous_hash: str
    timestamp: datetime
    nonce: int
    block_hash: str
    transactions: list[TransactionResponseDTO]


class PaginatedBlockResponseDTO(BaseModel):
    items: list[BlockResponseDTO]
    total: int
    page: int
    size: int


class PaginatedFullBlockResponseDTO(BaseModel):
    items: list[FullBlockResponseDTO]
    total: int
    page: int
    size: int
