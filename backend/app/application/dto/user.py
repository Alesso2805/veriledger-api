from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from backend.app.domain.entities.user import UserRole


class UserCreateDTO(BaseModel):
    email: EmailStr
    password: str
    role: UserRole = UserRole.VIEWER


class UserResponseDTO(BaseModel):
    id: str
    email: str | None = Field(description='Null for a demo account, whose display_name is "Guest XXXX"')
    display_name: str
    role: UserRole
    expires_at: datetime | None = Field(description="Set only for a demo account")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenDTO(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginDTO(BaseModel):
    email: EmailStr
    password: str
