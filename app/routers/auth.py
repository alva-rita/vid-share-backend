# routers/auth.py
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
import asyncpg

from app import crud, schemas, auth_utils
from app.database import get_db_connection
from app.config import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter()

@router.post("/signup", response_model=schemas.User)
async def signup_user(
    user: schemas.UserCreate, 
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    # Check if username already exists
    db_user_by_username = await crud.get_user_by_username(conn, username=user.username)
    if db_user_by_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Username already registered"
        )
    
    # Check if email already exists
    db_user_by_email = await crud.get_user_by_email(conn, email=user.email)
    if db_user_by_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email already registered"
        )
    
    try:
        db_user = await crud.create_user(
            conn, 
            username=user.username, 
            email=user.email, 
            password=user.password
        )
        return schemas.User(**db_user)
    except ValueError as e:
        # Handle duplicate errors from crud layer
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/login", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    user = await crud.get_user_by_username(conn, username=form_data.username)
    if not user or not auth_utils.verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_utils.create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=schemas.User)
async def read_users_me(
    current_user: dict = Depends(auth_utils.get_current_active_user)
):
    return schemas.User(**current_user)