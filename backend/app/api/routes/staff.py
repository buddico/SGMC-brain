"""Staff routes - read-only staff directory for the Brain UI."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_actor, get_session
from app.core.auth import Actor
from app.models.user import User

router = APIRouter(prefix="/staff", tags=["staff"])


class StaffOut(BaseModel):
    id: str
    name: str
    email: str
    job_title: str | None
    is_clinical: bool
    is_active: bool
    roles: list[str]

    model_config = {"from_attributes": True}


@router.get("", response_model=list[StaffOut])
def list_staff(
    active_only: bool = True,
    clinical_only: bool = False,
    q: str | None = Query(None),
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    stmt = select(User)
    if active_only:
        stmt = stmt.where(User.is_active == True)
    if clinical_only:
        stmt = stmt.where(User.is_clinical == True)
    if q:
        stmt = stmt.where(User.name.ilike(f"%{q}%"))
    stmt = stmt.order_by(User.name)
    users = db.scalars(stmt).all()
    return [
        StaffOut(
            id=str(u.id), name=u.name, email=u.email,
            job_title=u.job_title, is_clinical=u.is_clinical,
            is_active=u.is_active,
            roles=[r.name for r in u.roles],
        )
        for u in users
    ]
