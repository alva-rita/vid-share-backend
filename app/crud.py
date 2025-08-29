# crud.py
import asyncpg
from typing import Optional, List, Dict, Any
from app.auth_utils import get_password_hash


# --- Helper Functions ---
def row_to_dict(row: asyncpg.Record) -> Dict[str, Any]:
    """Convert asyncpg Record to dictionary"""
    return dict(row) if row else None

def rows_to_dict_list(rows: List[asyncpg.Record]) -> List[Dict[str, Any]]:
    """Convert list of asyncpg Records to list of dictionaries"""
    return [dict(row) for row in rows]

# --- User CRUD ---
async def get_user(conn: asyncpg.Connection, user_id: int) -> Optional[Dict[str, Any]]:
    """Get user by ID"""
    query = "SELECT * FROM users WHERE id = $1"
    row = await conn.fetchrow(query, user_id)
    return row_to_dict(row)

async def get_user_by_username(conn: asyncpg.Connection, username: str) -> Optional[Dict[str, Any]]:
    """Get user by username"""
    query = "SELECT * FROM users WHERE username = $1"
    row = await conn.fetchrow(query, username)
    return row_to_dict(row)

async def get_user_by_email(conn: asyncpg.Connection, email: str) -> Optional[Dict[str, Any]]:
    """Get user by email"""
    query = "SELECT * FROM users WHERE email = $1"
    row = await conn.fetchrow(query, email)
    return row_to_dict(row)

async def create_user(conn: asyncpg.Connection, username: str, email: str, password: str, role: str = "consumer") -> Dict[str, Any]:
    """Create a new user"""
    hashed_password = get_password_hash(password)
    query = """
        INSERT INTO users (username, email, hashed_password, role)
        VALUES ($1, $2, $3, $4)
        RETURNING *
    """
    try:
        row = await conn.fetchrow(query, username, email, hashed_password, role)
        print(f"Created user: {username}")
        return row_to_dict(row)
    except asyncpg.UniqueViolationError as e:
        if 'username' in str(e):
            raise ValueError("Username already exists")
        elif 'email' in str(e):
            raise ValueError("Email already exists")
        else:
            raise ValueError("User creation failed: duplicate entry")

async def update_user_role(conn: asyncpg.Connection, user_id: int, new_role: str) -> Optional[Dict[str, Any]]:
    """Update user role"""
    query = """
        UPDATE users 
        SET role = $2 
        WHERE id = $1 
        RETURNING *
    """
    row = await conn.fetchrow(query, user_id, new_role)
    if row:
        print(f"Updated role for user {user_id} to {new_role}")
    return row_to_dict(row)

# --- Video CRUD ---
async def create_video(conn: asyncpg.Connection, title: str, description: Optional[str], 
                      blob_url: str, owner_id: int, thumbnail_url: Optional[str] = None) -> Dict[str, Any]:
    """Create a new video"""
    query = """
        INSERT INTO videos (title, description, blob_url, thumbnail_url, owner_id)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING *
    """
    row = await conn.fetchrow(query, title, description, blob_url, thumbnail_url, owner_id)
    print(f"Created video: {title} for user {owner_id}")
    return row_to_dict(row)

async def get_video(conn: asyncpg.Connection, video_id: int) -> Optional[Dict[str, Any]]:
    """Get video by ID"""
    query = "SELECT * FROM videos WHERE id = $1"
    row = await conn.fetchrow(query, video_id)
    return row_to_dict(row)

async def get_videos(conn: asyncpg.Connection, skip: int = 0, limit: int = 10) -> List[Dict[str, Any]]:
    """Get videos with pagination, ordered by upload timestamp (newest first)"""
    query = """
        SELECT * FROM videos 
        ORDER BY upload_timestamp DESC 
        LIMIT $1 OFFSET $2
    """
    rows = await conn.fetch(query, limit, skip)
    return rows_to_dict_list(rows)

async def get_creator_videos(conn: asyncpg.Connection, owner_id: int, skip: int = 0, limit: int = 10) -> List[Dict[str, Any]]:
    """Get videos by specific creator with pagination"""
    query = """
        SELECT * FROM videos 
        WHERE owner_id = $1 
        ORDER BY upload_timestamp DESC 
        LIMIT $2 OFFSET $3
    """
    rows = await conn.fetch(query, owner_id, limit, skip)
    return rows_to_dict_list(rows)

async def delete_video(conn: asyncpg.Connection, video_id: int, owner_id: int) -> bool:
    """Delete a video (only by owner)"""
    query = "DELETE FROM videos WHERE id = $1 AND owner_id = $2"
    result = await conn.execute(query, video_id, owner_id)
    deleted = result.split()[-1] == '1'  # Check if one row was deleted
    if deleted:
        print(f"Deleted video {video_id} by user {owner_id}")
    return deleted

# --- Comment CRUD ---
async def create_comment(conn: asyncpg.Connection, text: str, owner_id: int, video_id: int) -> Dict[str, Any]:
    """Create a new comment"""
    query = """
        INSERT INTO comments (text, owner_id, video_id)
        VALUES ($1, $2, $3)
        RETURNING *
    """
    row = await conn.fetchrow(query, text, owner_id, video_id)
    print(f"Created comment on video {video_id} by user {owner_id}")
    return row_to_dict(row)

async def get_comments_for_video(conn: asyncpg.Connection, video_id: int, skip: int = 0, limit: int = 10) -> List[Dict[str, Any]]:
    """Get comments for a specific video with pagination"""
    query = """
        SELECT c.*, u.username 
        FROM comments c
        JOIN users u ON c.owner_id = u.id
        WHERE c.video_id = $1 
        ORDER BY c.timestamp DESC 
        LIMIT $2 OFFSET $3
    """
    rows = await conn.fetch(query, video_id, limit, skip)
    return rows_to_dict_list(rows)

async def delete_comment(conn: asyncpg.Connection, comment_id: int, owner_id: int) -> bool:
    """Delete a comment (only by owner or admin)"""
    query = "DELETE FROM comments WHERE id = $1 AND owner_id = $2"
    result = await conn.execute(query, comment_id, owner_id)
    deleted = result.split()[-1] == '1'
    if deleted:
        print(f"Deleted comment {comment_id} by user {owner_id}")
    return deleted

# --- Rating CRUD ---
async def create_or_update_rating(conn: asyncpg.Connection, score: float, owner_id: int, video_id: int) -> Dict[str, Any]:
    """Create or update a rating for a video"""
    query = """
        INSERT INTO ratings (score, owner_id, video_id)
        VALUES ($1, $2, $3)
        ON CONFLICT (owner_id, video_id) 
        DO UPDATE SET score = $1, timestamp = CURRENT_TIMESTAMP
        RETURNING *
    """
    row = await conn.fetchrow(query, score, owner_id, video_id)
    print(f"Created/updated rating for video {video_id} by user {owner_id}: {score}")
    return row_to_dict(row)

async def get_average_rating_for_video(conn: asyncpg.Connection, video_id: int) -> float:
    """Get average rating for a video"""
    query = "SELECT AVG(score) as avg_score FROM ratings WHERE video_id = $1"
    row = await conn.fetchrow(query, video_id)
    avg_score = row['avg_score'] if row and row['avg_score'] else 0.0
    return float(avg_score)

async def get_rating_stats_for_video(conn: asyncpg.Connection, video_id: int) -> Dict[str, Any]:
    """Get comprehensive rating statistics for a video"""
    query = """
        SELECT 
            AVG(score) as avg_score,
            COUNT(*) as total_ratings,
            MIN(score) as min_score,
            MAX(score) as max_score
        FROM ratings 
        WHERE video_id = $1
    """
    row = await conn.fetchrow(query, video_id)
    return {
        'avg_score': float(row['avg_score']) if row['avg_score'] else 0.0,
        'total_ratings': row['total_ratings'] if row else 0,
        'min_score': float(row['min_score']) if row['min_score'] else 0.0,
        'max_score': float(row['max_score']) if row['max_score'] else 0.0
    }

async def get_user_rating_for_video(conn: asyncpg.Connection, user_id: int, video_id: int) -> Optional[Dict[str, Any]]:
    """Get a specific user's rating for a video"""
    query = "SELECT * FROM ratings WHERE owner_id = $1 AND video_id = $2"
    row = await conn.fetchrow(query, user_id, video_id)
    return row_to_dict(row)

async def delete_rating(conn: asyncpg.Connection, owner_id: int, video_id: int) -> bool:
    """Delete a user's rating for a video"""
    query = "DELETE FROM ratings WHERE owner_id = $1 AND video_id = $2"
    result = await conn.execute(query, owner_id, video_id)
    deleted = result.split()[-1] == '1'
    if deleted:
        print(f"Deleted rating for video {video_id} by user {owner_id}")
    return deleted
