from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

app = FastAPI(
    title="AI Revenue Agent",
    description="AI-powered merchant revenue optimization platform",
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "message": "AI Revenue Agent API is running",
        "status": "healthy",
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok",
    }


@app.get("/health/database")
def database_health_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))

    return {
        "database": "connected",
    }