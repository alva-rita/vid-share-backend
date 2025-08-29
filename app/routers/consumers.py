# routers/consumers.py
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Header
import asyncpg
from typing import List, Optional
from starlette.responses import StreamingResponse

from app import crud, schemas, auth_utils, blob_storage
from app.database import get_db_connection

router = APIRouter()

@router.get("/", response_model=List[schemas.Video])
async def list_latest_videos(
    conn: asyncpg.Connection = Depends(get_db_connection),
    skip: int = 0,
    limit: int = 10,
    current_user: dict = Depends(auth_utils.get_current_active_user)  # Returns dict now
):
    """List the latest videos. Accessible by any authenticated user."""
    videos = await crud.get_videos(conn, skip=skip, limit=limit)
    res_videos = []
    for video in videos:
        video["stream_url"] = await blob_storage.generate_sas_url(video["blob_url"])
        res_videos.append(schemas.Video(**video))
    return res_videos #[schemas.Video(**video) for video in videos]

@router.get("/{video_id}", response_model=schemas.Video)
async def get_video_metadata(
    video_id: int,
    conn: asyncpg.Connection = Depends(get_db_connection),
    current_user: dict = Depends(auth_utils.get_current_active_user)  # Any authenticated user
):
    """Fetch metadata for a specific video. Accessible by any authenticated user."""
    db_video = await crud.get_video(conn, video_id=video_id)
    if db_video is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    
    db_video["stream_url"] = await blob_storage.generate_sas_url(db_video["blob_url"])

    return schemas.Video(**db_video)

@router.get("/{video_id}/stream")
async def stream_video(
    video_id: int,
    request: Request,
    conn: asyncpg.Connection = Depends(get_db_connection),
    current_user: dict = Depends(auth_utils.get_current_active_user),  # Any authenticated user
    range: Optional[str] = Header(None)  # For partial content streaming
):
    """Stream a video from Azure Blob Storage. Accessible by any authenticated user.
    Supports range requests for seeking/resuming playback."""
    db_video = await crud.get_video(conn, video_id=video_id)
    if db_video is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    blob_url = db_video["blob_url"]  # Dictionary access instead of attribute
    
    file_size = await blob_storage.get_blob_size(blob_url)
    
    start_byte = 0
    end_byte = file_size - 1

    if range:
        range_parts = range.replace("bytes=", "").split("-")
        start_byte = int(range_parts[0])
        if len(range_parts) > 1 and range_parts[1]:
            end_byte = int(range_parts[1])
        else:
            end_byte = file_size - 1

    if start_byte >= file_size or start_byte < 0:
        raise HTTPException(status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE)

    async def generate_chunks():
        # Adjust chunk size as needed
        chunk_size = 1024 * 1024  # 1 MB
        current_offset = start_byte

        while current_offset <= end_byte:
            chunk_end = min(current_offset + chunk_size - 1, end_byte)
            chunk = await blob_storage.download_blob_chunk(blob_url, current_offset, chunk_end)
            yield chunk
            current_offset += len(chunk)

    headers = {
        "Content-Type": "video/mp4",  # Assuming MP4, adjust if other formats are expected
        "Accept-Ranges": "bytes",
        "Content-Length": str(end_byte - start_byte + 1),
        "Content-Range": f"bytes {start_byte}-{end_byte}/{file_size}",
    }

    return StreamingResponse(generate_chunks(), status_code=status.HTTP_206_PARTIAL_CONTENT, headers=headers)


@router.post("/{video_id}/comments", response_model=schemas.Comment, status_code=status.HTTP_201_CREATED)
async def add_comment_to_video(
    video_id: int,
    comment: schemas.CommentCreate,
    conn: asyncpg.Connection = Depends(get_db_connection),
    current_user: dict = Depends(auth_utils.get_current_active_user)  # Any authenticated user
):
    """Add a comment to a video. Accessible by any authenticated user."""
    db_video = await crud.get_video(conn, video_id=video_id)
    if db_video is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    
    db_comment = await crud.create_comment(
        conn, 
        text=comment.text, 
        owner_id=current_user["id"],  # Dictionary access
        video_id=video_id
    )
    return schemas.Comment(**db_comment)

@router.get("/{video_id}/comments", response_model=List[dict])
async def list_comments_for_video(
    video_id: int,
    conn: asyncpg.Connection = Depends(get_db_connection),
    skip: int = 0,
    limit: int = 10,
    current_user: dict = Depends(auth_utils.get_current_active_user)  # Any authenticated user
):
    """List comments for a specific video. Accessible by any authenticated user."""
    db_video = await crud.get_video(conn, video_id=video_id)
    if db_video is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    comments = await crud.get_comments_for_video(conn, video_id=video_id, skip=skip, limit=limit)
    # Note: comments already include username from the JOIN in crud.py
    return comments

@router.post("/{video_id}/ratings", response_model=schemas.Rating)
async def add_or_update_rating_for_video(
    video_id: int,
    rating: schemas.RatingCreate,
    conn: asyncpg.Connection = Depends(get_db_connection),
    current_user: dict = Depends(auth_utils.get_current_active_user)  # Any authenticated user
):
    """Add or update a rating for a video. Accessible by any authenticated user."""
    if not (1.0 <= rating.score <= 5.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Rating score must be between 1.0 and 5.0"
        )
    
    db_video = await crud.get_video(conn, video_id=video_id)
    if db_video is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    
    db_rating = await crud.create_or_update_rating(
        conn, 
        score=rating.score, 
        owner_id=current_user["id"],  # Dictionary access
        video_id=video_id
    )
    return schemas.Rating(**db_rating)

@router.get("/{video_id}/ratings/average")
async def get_video_average_rating(
    video_id: int,
    conn: asyncpg.Connection = Depends(get_db_connection),
    current_user: dict = Depends(auth_utils.get_current_active_user)
):
    """Get average rating for a video. Accessible by any authenticated user."""
    db_video = await crud.get_video(conn, video_id=video_id)
    if db_video is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    
    avg_rating = await crud.get_average_rating_for_video(conn, video_id)
    return {
        "video_id": video_id,
        "average_rating": avg_rating
    }

@router.get("/{video_id}/ratings/stats")
async def get_video_rating_stats(
    video_id: int,
    conn: asyncpg.Connection = Depends(get_db_connection),
    current_user: dict = Depends(auth_utils.get_current_active_user)
):
    """Get comprehensive rating statistics for a video. Accessible by any authenticated user."""
    db_video = await crud.get_video(conn, video_id=video_id)
    if db_video is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    
    stats = await crud.get_rating_stats_for_video(conn, video_id)
    return {
        "video_id": video_id,
        **stats
    }