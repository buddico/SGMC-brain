"""Alert routes - MHRA/NatPSA/CAS alert management."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_actor, get_session
from app.core.auth import Actor
from app.models.alert import Alert, AlertAction, AlertPriority, AlertSource, AlertStatus

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertOut(BaseModel):
    id: str
    source: str
    title: str
    summary: str | None
    url: str | None
    issued_date: str | None
    message_type: str | None
    severity: str | None
    status: str
    priority: str | None
    due_date: str | None
    actions_count: int = 0
    created_at: str

    model_config = {"from_attributes": True}


def _alert_to_out(a: Alert) -> AlertOut:
    return AlertOut(
        id=str(a.id), source=a.source.value, title=a.title,
        summary=a.summary, url=a.url,
        issued_date=a.issued_date.isoformat() if a.issued_date else None,
        message_type=a.message_type, severity=a.severity,
        status=a.status.value,
        priority=a.priority.value if a.priority else None,
        due_date=a.due_date.isoformat() if a.due_date else None,
        actions_count=len(a.actions),
        created_at=a.created_at.isoformat() if a.created_at else "",
    )


@router.get("", response_model=list[AlertOut])
def list_alerts(
    source: AlertSource | None = None,
    status: AlertStatus | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    stmt = select(Alert)
    if source:
        stmt = stmt.where(Alert.source == source)
    if status:
        stmt = stmt.where(Alert.status == status)
    stmt = stmt.order_by(Alert.created_at.desc()).limit(limit).offset(offset)
    alerts = db.scalars(stmt).all()
    return [_alert_to_out(a) for a in alerts]


class AlertCreate(BaseModel):
    source: AlertSource
    title: str
    summary: str | None = None
    url: str | None = None
    content_id: str | None = None
    issued_date: str | None = None
    message_type: str | None = None
    severity: str | None = None


@router.post("", response_model=AlertOut, status_code=201)
def create_alert(
    body: AlertCreate,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    from datetime import date as date_type
    issued = None
    if body.issued_date:
        try:
            issued = date_type.fromisoformat(body.issued_date[:10])
        except ValueError:
            pass

    # Dedup by content_id
    if body.content_id:
        existing = db.scalar(select(Alert).where(Alert.content_id == body.content_id))
        if existing:
            return _alert_to_out(existing)

    alert = Alert(
        source=body.source,
        title=body.title,
        summary=body.summary,
        url=body.url,
        content_id=body.content_id,
        issued_date=issued,
        message_type=body.message_type,
        severity=body.severity,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return _alert_to_out(alert)


@router.get("/{alert_id}")
def get_alert(
    alert_id: uuid.UUID,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {
        **_alert_to_out(alert).model_dump(),
        "html_content": alert.html_content,
        "actions": [
            {
                "id": str(act.id),
                "action_type": act.action_type,
                "notes": act.notes,
                "performed_by_name": act.performed_by_name,
                "performed_at": act.performed_at.isoformat() if act.performed_at else None,
                "patients_identified": act.patients_identified,
                "applies_to_practice": act.applies_to_practice,
            }
            for act in alert.actions
        ],
    }


class AlertActionCreate(BaseModel):
    action_type: str
    notes: str | None = None
    patients_identified: int | None = None
    applies_to_practice: bool | None = None


@router.post("/{alert_id}/actions", status_code=201)
def add_alert_action(
    alert_id: uuid.UUID,
    body: AlertActionCreate,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    action = AlertAction(
        alert_id=alert.id,
        action_type=body.action_type,
        notes=body.notes,
        performed_by_email=actor.email,
        performed_by_name=actor.name,
        patients_identified=body.patients_identified,
        applies_to_practice=body.applies_to_practice,
    )
    db.add(action)
    db.commit()
    return {"id": str(action.id), "status": "created"}


class AlertStatusUpdate(BaseModel):
    status: AlertStatus
    priority: AlertPriority | None = None


@router.patch("/{alert_id}/status")
def update_alert_status(
    alert_id: uuid.UUID,
    body: AlertStatusUpdate,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = body.status
    if body.priority is not None:
        alert.priority = body.priority
    db.commit()
    return {"id": str(alert.id), "status": alert.status.value}
