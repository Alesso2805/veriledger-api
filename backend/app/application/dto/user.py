from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from backend.app.domain.entities.user import UserRole


class UserCreateDTO(BaseModel):
    email: EmailStr
    password: str
    role: UserRole = UserRole.VIEWER


class UserResponseDTO(BaseModel):
    id: str
    # Null for a demo account, whose display_name is "Guest XXXX"; otherwise the email
    email: str | None
    display_name: str
    role: UserRole
    # Only a demo account expires
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenDTO(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginDTO(BaseModel):
    email: EmailStr
    password: str
