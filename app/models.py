# models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="consumer", nullable=False) # 'consumer', 'creator', 'admin'

    videos = relationship("Video", back_populates="owner")
    comments = relationship("Comment", back_populates="owner")
    ratings = relationship("Rating", back_populates="owner")

class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(Text)
    blob_url = Column(String, nullable=False) # URL to the video in Azure Blob Storage
    thumbnail_url = Column(String) # URL to the thumbnail in Azure Blob Storage
    upload_timestamp = Column(DateTime, default=func.now())
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="videos")
    comments = relationship("Comment", back_populates="video")
    ratings = relationship("Rating", back_populates="video")

class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=func.now())
    owner_id = Column(Integer, ForeignKey("users.id"))
    video_id = Column(Integer, ForeignKey("videos.id"))

    owner = relationship("User", back_populates="comments")
    video = relationship("Video", back_populates="comments")

class Rating(Base):
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True, index=True)
    score = Column(Float, nullable=False) # e.g., 1.0 to 5.0
    timestamp = Column(DateTime, default=func.now())
    owner_id = Column(Integer, ForeignKey("users.id"))
    video_id = Column(Integer, ForeignKey("videos.id"))

    owner = relationship("User", back_populates="ratings")
    video = relationship("Video", back_populates="ratings")