from datetime import datetime
from pydantic import BaseModel, Field

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Unique login identifier")

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, description="Plaintext security password")

class UserOut(UserBase):
    id: int
    created_at: datetime

    class Config:
        # Enable ORM compatibility so Pydantic can read attributes from SQLAlchemy objects
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None
