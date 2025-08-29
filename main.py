# main.py
import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from app.database import startup_database, shutdown_database
from app.routers import auth, creators, consumers, admin

# Create database tables
# models.Base.metadata.create_all(bind=engine)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await startup_database()
    yield

    await shutdown_database()

app = FastAPI(
    title="Video Platform API",
    description="A video platform with Azure PostgreSQL backend",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # or ["*"] to allow all
    allow_credentials=False,
    allow_methods=["*"],            # GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],            # Allow all headers
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(creators.router, prefix="/videos", tags=["Creators"]) # This path also serves general video uploads
app.include_router(consumers.router, prefix="/videos", tags=["Consumers"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])


@app.get("/health")
async def root():
    return {"message": "Welcome to the Video Sharing Platform API"}

# You can run this file using: uvicorn main:app --reload
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)