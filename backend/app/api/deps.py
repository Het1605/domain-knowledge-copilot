from typing import Generator
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.core.database import SessionLocal
from backend.app.core.security import ALGORITHM
from backend.app.models.user import User
from backend.app.schemas.user import TokenData

# OAuth2PasswordBearer standard scheme mapping to token exchange router path
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl="/api/auth/token"
)

def get_db() -> Generator:
    """SessionLocal generator yielding database transactional contexts."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(reusable_oauth2)
) -> User:
    """Extracts, decodes, and validates JWT headers to scope the calling User.
    
    Throws 401 Unauthorized if verification credentials fail.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Decode signed token signature
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except jwt.PyJWTError:
        raise credentials_exception
        
    # Query database record matching token subject
    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
        
    return user
