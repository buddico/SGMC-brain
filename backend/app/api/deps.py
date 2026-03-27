"""Dependency injection for FastAPI routes."""

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.auth import Actor
from app.core.database import get_db


def get_current_actor(request: Request) -> Actor:
    actor = getattr(request.state, "actor", None)
    if actor is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return actor


def get_session(db: Session = Depends(get_db)) -> Session:
    return db
