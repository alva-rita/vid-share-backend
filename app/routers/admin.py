# routers/admin.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, schemas, auth_utils, models
from app.database import get_db

router = APIRouter()

@router.post("/creators", response_model=schemas.User,
             dependencies=[Depends(auth_utils.require_admin)])
async def enroll_creator(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user) # Ensure an admin is making this call
):
    """Enroll a user as a creator (assign 'creator' role). Requires 'admin' role."""
    db_user = crud.get_user(db, user_id)
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    if db_user.role == "creator":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is already a creator")
    
    updated_user = crud.update_user_role(db, user_id=user_id, new_role="creator")
    return updated_user