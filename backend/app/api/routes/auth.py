"""Auth routes - current user info."""

from fastapi import APIRouter, Depends

from app.api.deps import get_current_actor
from app.core.auth import Actor

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
def get_current_user(actor: Actor = Depends(get_current_actor)):
    return {
        "email": actor.email,
        "name": actor.name,
        "roles": actor.roles,
    }
