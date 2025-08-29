# routers/creators.py
from fastapi import APIRouter, Depends, Form, status, UploadFile, File
import asyncpg
from typing import List, Optional

from app import crud, schemas, auth_utils, blob_storage
from app.database import get_db_connection

router = APIRouter()

@router.post("/", response_model=schemas.Video, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(auth_utils.require_creator)])
async def upload_video(
    title: str = Form(...),
    file: UploadFile = File(...),
    description: Optional[str] = None,
    thumbnail: Optional[UploadFile] = File(None),
    current_user: dict = Depends(auth_utils.get_current_active_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """Upload a video file and its metadata. Requires 'creator' role."""
    # Upload video to blob storage
    video_blob_url = await blob_storage.upload_file_to_blob(file, file_type="video")
    
    thumbnail_blob_url = None
    if thumbnail:
        # Upload thumbnail to blob storage
        thumbnail_blob_url = await blob_storage.upload_file_to_blob(thumbnail, file_type="thumbnail")
    print("got here")
    db_video = await crud.create_video(
        conn=conn,
        title=title,
        description=description,
        blob_url=video_blob_url,
        owner_id=current_user["id"],  # Access dict key instead of attribute
        thumbnail_url=thumbnail_blob_url
    )
    return schemas.Video(**db_video)

@router.get("/studio", response_model=List[schemas.Video],
             dependencies=[Depends(auth_utils.require_creator)])
async def list_creator_videos(
    current_user: dict = Depends(auth_utils.get_current_active_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    skip: int = 0,
    limit: int = 10
):
    """List videos uploaded by the current creator. Requires 'creator' role."""
    videos = await crud.get_creator_videos(conn, owner_id=current_user["id"], skip=skip, limit=limit)
    return [schemas.Video(**video) for video in videos]