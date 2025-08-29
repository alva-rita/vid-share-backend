# crud.py
import psycopg
from psycopg import AsyncConnection  # For type hints
from psycopg.rows import dict_row
from typing import Optional, List, Dict, Any
from app.auth_utils import get_password_hash

# --- User CRUD ---
async def get_user(conn: AsyncConnection, user_id: int) -> Optional[Dict[str, Any]]:
    async with conn.cursor(row_factory=dict_row) as cursor:
        await cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        return await cursor.fetchone()

async def get_user_by_username(conn: AsyncConnection, username: str) -> Optional[Dict[str, Any]]:
    async with conn.cursor(row_factory=dict_row) as cursor:
        await cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        return await cursor.fetchone()

async def get_user_by_email(conn: AsyncConnection, email: str) -> Optional[Dict[str, Any]]:
    async with conn.cursor(row_factory=dict_row) as cursor:
        await cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        return await cursor.fetchone()

async def create_user(conn: AsyncConnection, username: str, email: str, password: str, role: str = "consumer") -> Dict[str, Any]:
    hashed_password = get_password_hash(password)
    query = """
        INSERT INTO users (username, email, hashed_password, role)
        VALUES (%s, %s, %s, %s)
        RETURNING *
    """
    try:
        async with conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(query, (username, email, hashed_password, role))
            row = await cursor.fetchone()
            await conn.commit()
        print(f"Created user: {username}")
        return row
    except psycopg.errors.UniqueViolation as e:
        await conn.rollback()
        if 'username' in str(e):
            raise ValueError("Username already exists")
        elif 'email' in str(e):
            raise ValueError("Email already exists")
        else:
            raise ValueError("User creation failed: duplicate entry")
    except Exception as e:
        await conn.rollback()
        raise ValueError(f"User creation failed: {e}")

async def update_user_role(conn: AsyncConnection, user_id: int, new_role: str) -> Optional[Dict[str, Any]]:
    query = "UPDATE users SET role = %s WHERE id = %s RETURNING *"
    async with conn.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(query, (new_role, user_id))
        row = await cursor.fetchone()
        await conn.commit()
    if row:
        print(f"Updated role for user {user_id} to {new_role}")
    return row

# --- Video CRUD ---
async def create_video(conn: AsyncConnection, title: str, description: Optional[str], 
                      blob_url: str, owner_id: int, thumbnail_url: Optional[str] = None) -> Dict[str, Any]:
    query = """
        INSERT INTO videos (title, description, blob_url, thumbnail_url, owner_id)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING *
    """
    async with conn.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(query, (title, description, blob_url, thumbnail_url, owner_id))
        row = await cursor.fetchone()
        await conn.commit()
    print(f"Created video: {title} for user {owner_id}")
    return row

# async def get_video(conn: AsyncConnection, video_id: int) -> Optional[Dict[str, Any]]:
#     async with conn.cursor(row_factory=dict_row) as cursor:
#         await cursor.execute("SELECT * FROM videos WHERE id = %s", (video_id,))
#         return await cursor.fetchone()

async def get_video(conn: AsyncConnection, video_id: int) -> Optional[Dict[str, Any]]:
    query = """
        SELECT 
            v.id,
            v.title,
            v.description,
            v.blob_url,
            v.thumbnail_url,
            v.upload_timestamp,
            v.owner_id,
            u.username AS owner_username,
            v.upload_timestamp AS created_at
        FROM videos v
        JOIN users u ON v.owner_id = u.id
        WHERE v.id = %s
    """
    async with conn.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(query, (video_id,))
        row = await cursor.fetchone()
        if row:
            # Optional mapping for frontend
            row["owner"] = {"username": row.pop("owner_username", "Unknown")}
            row["created_at"] = row.pop("created_at", row["upload_timestamp"])
        return row


# async def get_videos(conn: AsyncConnection, skip: int = 0, limit: int = 10) -> List[Dict[str, Any]]:
#     query = "SELECT * FROM videos ORDER BY upload_timestamp DESC LIMIT %s OFFSET %s"
#     async with conn.cursor(row_factory=dict_row) as cursor:
#         await cursor.execute(query, (limit, skip))
#         return await cursor.fetchall()

async def get_videos(conn: AsyncConnection, skip: int = 0, limit: int = 10) -> List[Dict[str, Any]]:
    query = """
        SELECT
            v.id,
            v.title,
            v.description,
            v.blob_url,
            v.thumbnail_url,
            v.upload_timestamp,
            v.owner_id,
            u.username AS owner_username,
            v.upload_timestamp AS created_at
        FROM videos v
        JOIN users u ON v.owner_id = u.id
        ORDER BY v.upload_timestamp DESC
        LIMIT %s OFFSET %s
    """
    async with conn.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(query, (limit, skip))
        rows = await cursor.fetchall()

        # Map optional frontend fields
        for row in rows:
            row["owner"] = {"username": row.pop("owner_username", "Unknown")}
            row["created_at"] = row.pop("created_at", row["upload_timestamp"])

        return rows


async def get_creator_videos(conn: AsyncConnection, owner_id: int, skip: int = 0, limit: int = 10) -> List[Dict[str, Any]]:
    query = "SELECT * FROM videos WHERE owner_id = %s ORDER BY upload_timestamp DESC LIMIT %s OFFSET %s"
    async with conn.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(query, (owner_id, limit, skip))
        return await cursor.fetchall()

async def delete_video(conn: AsyncConnection, video_id: int, owner_id: int) -> bool:
    query = "DELETE FROM videos WHERE id = %s AND owner_id = %s"
    async with conn.cursor() as cursor:
        await cursor.execute(query, (video_id, owner_id))
        deleted_rows = cursor.rowcount
        await conn.commit()
    if deleted_rows > 0:
        print(f"Deleted video {video_id} by user {owner_id}")
        return True
    return False

# --- Comment CRUD ---
async def create_comment(conn: AsyncConnection, text: str, owner_id: int, video_id: int) -> Dict[str, Any]:
    query = """
        INSERT INTO comments (text, owner_id, video_id)
        VALUES (%s, %s, %s)
        RETURNING id, text AS content, owner_id, video_id, timestamp AS created_at
    """
    async with conn.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(query, (text, owner_id, video_id))
        row = await cursor.fetchone()

    # Get username for owner
    async with conn.cursor(row_factory=dict_row) as cursor:
        await cursor.execute("SELECT username FROM users WHERE id = %s", (owner_id,))
        user_row = await cursor.fetchone()
        row["owner"] = {"username": user_row["username"] if user_row else "Anonymous"}

    await conn.commit()
    return row

# async def create_comment(conn: AsyncConnection, text: str, owner_id: int, video_id: int) -> Dict[str, Any]:
#     query = "INSERT INTO comments (text, owner_id, video_id) VALUES (%s, %s, %s) RETURNING *"
#     async with conn.cursor(row_factory=dict_row) as cursor:
#         await cursor.execute(query, (text, owner_id, video_id))
#         row = await cursor.fetchone()
#         await conn.commit()
#     print(f"Created comment on video {video_id} by user {owner_id}")
#     return row

async def get_comments_for_video(conn: AsyncConnection, video_id: int, skip: int = 0, limit: int = 10) -> List[Dict[str, Any]]:
    query = """
        SELECT 
            c.id,
            c.text AS content,          -- rename text -> content
            c.owner_id,
            c.video_id,
            c.timestamp AS created_at,  -- rename timestamp -> created_at
            u.username AS owner_username
        FROM comments c
        JOIN users u ON c.owner_id = u.id
        WHERE c.video_id = %s
        ORDER BY c.timestamp DESC
        LIMIT %s OFFSET %s
    """
    async with conn.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(query, (video_id, limit, skip))
        rows = await cursor.fetchall()
        for row in rows:
            row["owner"] = {"username": row.pop("owner_username", "Anonymous")}
        return rows


# async def get_comments_for_video(conn: AsyncConnection, video_id: int, skip: int = 0, limit: int = 10) -> List[Dict[str, Any]]:
#     query = """
#         SELECT c.*, u.username
#         FROM comments c
#         JOIN users u ON c.owner_id = u.id
#         WHERE c.video_id = %s
#         ORDER BY c.timestamp DESC
#         LIMIT %s OFFSET %s
#     """
#     async with conn.cursor(row_factory=dict_row) as cursor:
#         await cursor.execute(query, (video_id, limit, skip))
#         return await cursor.fetchall()

async def delete_comment(conn: AsyncConnection, comment_id: int, owner_id: int) -> bool:
    query = "DELETE FROM comments WHERE id = %s AND owner_id = %s"
    async with conn.cursor() as cursor:
        await cursor.execute(query, (comment_id, owner_id))
        deleted_rows = cursor.rowcount
        await conn.commit()
    if deleted_rows > 0:
        print(f"Deleted comment {comment_id} by user {owner_id}")
        return True
    return False

# --- Rating CRUD ---
# async def create_or_update_rating(conn: AsyncConnection, score: float, owner_id: int, video_id: int) -> Dict[str, Any]:
#     query = """
#         INSERT INTO ratings (score, owner_id, video_id)
#         VALUES (%s, %s, %s)
#         ON CONFLICT (owner_id, video_id)
#         DO UPDATE SET score = EXCLUDED.score, timestamp = CURRENT_TIMESTAMP
#         RETURNING *
#     """
#     async with conn.cursor(row_factory=dict_row) as cursor:
#         await cursor.execute(query, (score, owner_id, video_id))
#         row = await cursor.fetchone()
#         await conn.commit()
#     print(f"Created/updated rating for video {video_id} by user {owner_id}: {score}")
#     return row

async def create_or_update_rating(conn: AsyncConnection, score: float, owner_id: int, video_id: int) -> Dict[str, Any]:
    query = """
        INSERT INTO ratings (score, owner_id, video_id)
        VALUES (%s, %s, %s)
        ON CONFLICT (owner_id, video_id)
        DO UPDATE SET score = EXCLUDED.score, timestamp = CURRENT_TIMESTAMP
        RETURNING id, score, video_id, owner_id, timestamp
    """
    async with conn.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(query, (score, owner_id, video_id))
        row = await cursor.fetchone()

    # Rename timestamp -> created_at
    row["created_at"] = row.pop("timestamp")
    await conn.commit()
    return row


async def get_average_rating_for_video(conn: AsyncConnection, video_id: int) -> float:
    async with conn.cursor(row_factory=dict_row) as cursor:
        await cursor.execute("SELECT AVG(score) as avg_score FROM ratings WHERE video_id = %s", (video_id,))
        row = await cursor.fetchone()
    return float(row['avg_score']) if row and row['avg_score'] else 0.0

async def get_rating_stats_for_video(conn: AsyncConnection, video_id: int) -> Dict[str, Any]:
    query = """
        SELECT AVG(score) as avg_score, COUNT(*) as total_ratings, MIN(score) as min_score, MAX(score) as max_score
        FROM ratings
        WHERE video_id = %s
    """
    async with conn.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(query, (video_id,))
        row = await cursor.fetchone()
    return {
        'avg_score': float(row['avg_score']) if row and row['avg_score'] else 0.0,
        'total_ratings': row['total_ratings'] if row and row['total_ratings'] else 0,
        'min_score': float(row['min_score']) if row and row['min_score'] else 0.0,
        'max_score': float(row['max_score']) if row and row['max_score'] else 0.0
    }

# async def get_user_rating_for_video(conn: AsyncConnection, user_id: int, video_id: int) -> Optional[Dict[str, Any]]:
#     async with conn.cursor(row_factory=dict_row) as cursor:
#         await cursor.execute("SELECT * FROM ratings WHERE owner_id = %s AND video_id = %s", (user_id, video_id))
#         return await cursor.fetchone()

async def get_user_rating_for_video(conn: AsyncConnection, user_id: int, video_id: int) -> Optional[Dict[str, Any]]:
    async with conn.cursor(row_factory=dict_row) as cursor:
        await cursor.execute("SELECT id, score, owner_id, video_id, timestamp FROM ratings WHERE owner_id = %s AND video_id = %s", (user_id, video_id))
        row = await cursor.fetchone()
        if row:
            row["created_at"] = row.pop("timestamp")
        return row

async def delete_rating(conn: AsyncConnection, owner_id: int, video_id: int) -> bool:
    query = "DELETE FROM ratings WHERE owner_id = %s AND video_id = %s"
    async with conn.cursor() as cursor:
        await cursor.execute(query, (owner_id, video_id))
        deleted_rows = cursor.rowcount
        await conn.commit()
    if deleted_rows > 0:
        print(f"Deleted rating for video {video_id} by user {owner_id}")
        return True
    return False
