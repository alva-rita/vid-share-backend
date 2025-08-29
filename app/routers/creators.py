# routers/creators.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional

import crud, schemas, auth_utils, models, blob_storage
from database import get_db

router = APIRouter()

@router.post("/", response_model=schemas.Video, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(auth_utils.require_creator)])
async def upload_video(
    title: str,
    file: UploadFile = File(...),
    description: Optional[str] = None,
    thumbnail: Optional[UploadFile] = File(None),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload a video file and its metadata. Requires 'creator' role."""
    # Upload video to blob storage
    video_blob_url = await blob_storage.upload_file_to_blob(file, file_type="video")
    
    thumbnail_blob_url = None
    if thumbnail:
        # Upload thumbnail to blob storage
        thumbnail_blob_url = await blob_storage.upload_file_to_blob(thumbnail, file_type="thumbnail")
    
    video_create = schemas.VideoCreate(title=title, description=description)
    db_video = crud.create_video(
        db=db,
        video=video_create,
        owner_id=current_user.id,
        blob_url=video_blob_url,
        thumbnail_url=thumbnail_blob_url
    )
    return db_video

@router.get("/studio", response_model=List[schemas.Video],
             dependencies=[Depends(auth_utils.require_creator)])
async def list_creator_videos(
    current_user: models.User = Depends(auth_utils.get_current_active_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 10
):
    """List videos uploaded by the current creator. Requires 'creator' role."""
    videos = crud.get_creator_videos(db, owner_id=current_user.id, skip=skip, limit=limit)
    return videos