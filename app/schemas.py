# schemas.py
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, Dict

# --- User Schemas ---
class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    role: str

    class Config:
        from_attributes = True

class UserInDB(User):
    hashed_password: str

# --- Video Schemas ---
class VideoBase(BaseModel):
    title: str
    description: Optional[str] = None

class VideoCreate(VideoBase):
    pass # For now, no extra fields needed for creation beyond base

# class Video(VideoBase):
#     id: int
#     blob_url: str
#     thumbnail_url: Optional[str] = None
#     stream_url: Optional[str] = None
#     upload_timestamp: datetime
#     owner_id: int

#     class Config:
#         from_attributes = True
#         json_encoders = {
#             datetime: lambda v: v.isoformat(timespec='milliseconds')
#         }

class Video(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    blob_url: str
    thumbnail_url: Optional[str] = None
    stream_url: Optional[str] = None
    upload_timestamp: datetime     # original backend field
    owner_id: int                  # original backend field

    # Optional frontend-friendly fields
    created_at: Optional[datetime] = None
    owner: Optional[Dict[str, str]] = None   # {"username": "..."}

    class Config:
        orm_mode = True
        # Ensures datetime fields are serialized in milliseconds for JS
        json_encoders = {
            datetime: lambda v: v.isoformat(timespec="milliseconds")
        }

# --- Comment Schemas ---
class CommentBase(BaseModel):
    text: str

class CommentCreate(CommentBase):
    pass

# class Comment(CommentBase):
#     id: int
#     timestamp: datetime
#     owner_id: int
#     video_id: int

#     class Config:
#         from_attributes = True
class Comment(BaseModel):
    id: int
    content: str
    video_id: int
    owner_id: int
    created_at: datetime
    owner: Optional[Dict[str, str]] = None

    class Config:
        orm_mode = True
        json_encoders = {datetime: lambda v: v.isoformat(timespec="milliseconds")}

# --- Rating Schemas ---
class RatingBase(BaseModel):
    score: float # e.g., 1.0 to 5.0

class RatingCreate(RatingBase):
    pass

class Rating(BaseModel):
    id: int
    score: float
    video_id: int
    owner_id: int
    created_at: datetime

    class Config:
        orm_mode = True
        json_encoders = {datetime: lambda v: v.isoformat(timespec="milliseconds")}


# --- Auth Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    # role: Optional[str] = None # We'll fetch the role from the DB for simplicity here