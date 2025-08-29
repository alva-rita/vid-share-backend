# main.py
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

import crud, models, schemas, auth_utils
from database import engine, get_db
from routers import auth, creators, consumers, admin

# Create database tables
# models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Video Sharing Platform Backend")

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(creators.router, prefix="/videos", tags=["Creators"]) # This path also serves general video uploads
app.include_router(consumers.router, prefix="/videos", tags=["Consumers"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])


@app.get("/")
async def root():
    return {"message": "Welcome to the Video Sharing Platform API"}

# You can run this file using: uvicorn main:app --reload
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)