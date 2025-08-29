from fastapi import APIRouter, Depends, HTTPException, status
import asyncpg

from app import crud, schemas, auth_utils
from app.database import get_db_connection

router = APIRouter()

@router.post("/creators", response_model=schemas.User,
             dependencies=[Depends(auth_utils.require_admin)])
async def enroll_creator(
    user_id: int,
    conn: asyncpg.Connection = Depends(get_db_connection),
    current_user: dict = Depends(auth_utils.get_current_active_user)  # Now returns dict instead of model
):
    """Enroll a user as a creator (assign 'creator' role). Requires 'admin' role."""
    db_user = await crud.get_user(conn, user_id)
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    if db_user["role"] == "creator":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is already a creator")
    
    updated_user = await crud.update_user_role(conn, user_id=user_id, new_role="creator")
    return schemas.User(**updated_user)