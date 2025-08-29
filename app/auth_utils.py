# auth_utils.py
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import asyncpg

from app import schemas, crud
from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from app.database import get_db_connection

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def verify_password(plain_password, hashed_password):
    """Verify a plain password against a hashed password"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    conn: asyncpg.Connection = Depends(get_db_connection)
) -> dict:
    """Get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    # Get user from database
    user = await crud.get_user_by_username(conn, username=token_data.username)
    if user is None:
        raise credentials_exception
    
    return user  # Returns dict instead of model

async def get_current_active_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Get current active user - you could add additional checks here"""
    # Example: Check if user is active/enabled
    # if not current_user.get("is_active", True):
    #     raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Role-based access control dependencies
def role_required(required_role: str):
    """Factory function to create role-specific dependencies"""
    async def role_checker(current_user: dict = Depends(get_current_active_user)) -> dict:
        if current_user["role"] != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized. Requires '{required_role}' role.",
            )
        return current_user
    return role_checker

def roles_required(allowed_roles: list):
    """Factory function to create dependencies that allow multiple roles"""
    async def role_checker(current_user: dict = Depends(get_current_active_user)) -> dict:
        if current_user["role"] not in allowed_roles:
            roles_str = ", ".join(allowed_roles)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized. Requires one of these roles: {roles_str}",
            )
        return current_user
    return role_checker

# Specific role dependencies for convenience
require_consumer = role_required("consumer")
require_creator = role_required("creator") 
require_admin = role_required("admin")

# Common role combinations
require_creator_or_admin = roles_required(["creator", "admin"])
require_any_authenticated = get_current_active_user  # Just requires valid token

# Helper function to check if user owns a resource
async def require_owner_or_admin(
    resource_owner_id: int,
    current_user: dict = Depends(get_current_active_user)
) -> dict:
    """Require user to be owner of resource or admin"""
    if current_user["role"] != "admin" and current_user["id"] != resource_owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized. Must be resource owner or admin."
        )
    return current_user