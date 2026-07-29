from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from backend.app.domain.entities.user import UserRole


class UserCreateDTO(BaseModel):
    email: EmailStr
    password: str
    role: UserRole = UserRole.VIEWER


class UserResponseDTO(BaseModel):
    id: str
    email: str
    role: UserRole
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenDTO(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginDTO(BaseModel):
    email: EmailStr
    password: str
