# database.py
import asyncpg
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from app.config import settings

class DatabaseManager:
    def __init__(self):
        self.pool = None
        
    async def create_pool(self):
        """Create a connection pool to PostgreSQL"""
        try:
            # Build connection string from environment variables
            host = settings.pghost # os.getenv('PGHOST', 'assigment.postgres.database.azure.com')
            user = settings.pguser #os.getenv('PGUSER', 'Rita')
            port = settings.pgport #int(os.getenv('PGPORT', '5432'))
            database = settings.pgdatabase # os.getenv('PGDATABASE', 'postgres')
            password = settings.pgpassword # os.getenv('PGPASSWORD')
            
            if not password:
                raise ValueError("PGPASSWORD environment variable is required")
            
            # Azure PostgreSQL connection string with SSL
            dsn = f"postgresql://{user}:{password}@{host}:{port}/{database}?sslmode=require"
            
            self.pool = await asyncpg.create_pool(
                dsn,
                min_size=1,
                max_size=10,
                command_timeout=60,
                server_settings={
                    'application_name': 'video_platform_app',
                }
            )
            print("Database connection pool created successfully")
            return self.pool
        except Exception as e:
            print(f"Failed to create database pool: {e}")
            raise
    
    async def close_pool(self):
        """Close the connection pool"""
        if self.pool:
            await self.pool.close()
            print("Database connection pool closed")
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Get a database connection from the pool"""
        if not self.pool:
            await self.create_pool()
        
        async with self.pool.acquire() as connection:
            yield connection

# Global database manager instance
db_manager = DatabaseManager()

# Dependency function for FastAPI
async def get_db_connection():
    async with db_manager.get_connection() as connection:
        yield connection

# Initialize database tables
async def create_tables():
    """Create all necessary tables"""
    async with db_manager.get_connection() as conn:
        # Users table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                hashed_password VARCHAR(255) NOT NULL,
                role VARCHAR(50) DEFAULT 'consumer' NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        
        # Videos table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                blob_url VARCHAR(500) NOT NULL,
                thumbnail_url VARCHAR(500),
                upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                owner_id INTEGER REFERENCES users(id) ON DELETE CASCADE
            );
        ''')
        
        # Comments table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                id SERIAL PRIMARY KEY,
                text TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                owner_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                video_id INTEGER REFERENCES videos(id) ON DELETE CASCADE
            );
        ''')
        
        # Ratings table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS ratings (
                id SERIAL PRIMARY KEY,
                score REAL NOT NULL CHECK (score >= 0 AND score <= 5),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                owner_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                video_id INTEGER REFERENCES videos(id) ON DELETE CASCADE,
                UNIQUE(owner_id, video_id)
            );
        ''')
        
        # Create indexes for better performance
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_videos_owner_id ON videos(owner_id);')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_videos_upload_timestamp ON videos(upload_timestamp DESC);')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_comments_video_id ON comments(video_id);')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_comments_timestamp ON comments(timestamp DESC);')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_ratings_video_id ON ratings(video_id);')
        
        print("Database tables created/verified successfully")

# Startup and shutdown events
async def startup_database():
    """Initialize database on startup"""
    await db_manager.create_pool()
    await create_tables()

async def shutdown_database():
    """Cleanup database connections on shutdown"""
    await db_manager.close_pool()