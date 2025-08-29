# crud.py
from sqlalchemy.orm import Session
from typing import Optional
from sqlalchemy import func
from app import models, schemas
from app.auth_utils import get_password_hash

# --- User CRUD ---
def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate, role: str = "consumer"):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        role=role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user_role(db: Session, user_id: int, new_role: str):
    db_user = get_user(db, user_id)
    if db_user:
        db_user.role = new_role
        db.commit()
        db.refresh(db_user)
    return db_user


# --- Video CRUD ---
def create_video(db: Session, video: schemas.VideoCreate, owner_id: int, blob_url: str, thumbnail_url: Optional[str] = None):
    db_video = models.Video(
        title=video.title,
        description=video.description,
        blob_url=blob_url,
        thumbnail_url=thumbnail_url,
        owner_id=owner_id
    )
    db.add(db_video)
    db.commit()
    db.refresh(db_video)
    return db_video

def get_video(db: Session, video_id: int):
    return db.query(models.Video).filter(models.Video.id == video_id).first()

def get_videos(db: Session, skip: int = 0, limit: int = 10):
    return db.query(models.Video).order_by(models.Video.upload_timestamp.desc()).offset(skip).limit(limit).all()

def get_creator_videos(db: Session, owner_id: int, skip: int = 0, limit: int = 10):
    return db.query(models.Video).filter(models.Video.owner_id == owner_id).offset(skip).limit(limit).all()


# --- Comment CRUD ---
def create_comment(db: Session, comment: schemas.CommentCreate, owner_id: int, video_id: int):
    db_comment = models.Comment(
        text=comment.text,
        owner_id=owner_id,
        video_id=video_id
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment

def get_comments_for_video(db: Session, video_id: int, skip: int = 0, limit: int = 10):
    return db.query(models.Comment).filter(models.Comment.video_id == video_id).order_by(models.Comment.timestamp.desc()).offset(skip).limit(limit).all()


# --- Rating CRUD ---
def create_or_update_rating(db: Session, rating: schemas.RatingCreate, owner_id: int, video_id: int):
    db_rating = db.query(models.Rating).filter(
        models.Rating.owner_id == owner_id,
        models.Rating.video_id == video_id
    ).first()

    if db_rating:
        db_rating.score = rating.score
    else:
        db_rating = models.Rating(
            score=rating.score,
            owner_id=owner_id,
            video_id=video_id
        )
        db.add(db_rating)
    db.commit()
    db.refresh(db_rating)
    return db_rating

def get_average_rating_for_video(db: Session, video_id: int):
    average_score = db.query(func.avg(models.Rating.score)).filter(models.Rating.video_id == video_id).scalar()
    return average_score if average_score is not None else 0.0