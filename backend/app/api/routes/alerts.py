"""Alert routes - MHRA/NatPSA/CAS alert management with triage and acknowledgments."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_actor, get_session
from app.core.auth import Actor
from app.models.alert import (
    Alert, AlertAcknowledgment, AlertAction, AlertNotification,
    AlertPriority, AlertSource, AlertStatus,
)
from app.models.user import User

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
    is_relevant: bool | None
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
        is_relevant=a.is_relevant,
        actions_count=len(a.actions),
        created_at=a.created_at.isoformat() if a.created_at else "",
    )


@router.get("", response_model=list[AlertOut])
def list_alerts(
    source: AlertSource | None = None,
    status: AlertStatus | None = None,
    is_relevant: bool | None = Query(None),
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
    if is_relevant is not None:
        stmt = stmt.where(Alert.is_relevant == is_relevant)
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


# --- Pending alerts for current user (nav badge) — MUST be before /{alert_id} ---

@router.get("/my/pending", response_model=list[AlertOut])
def my_pending_alerts(
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    """Alerts the current user has not yet acknowledged."""
    alert_ids = db.scalars(
        select(AlertAcknowledgment.alert_id).where(
            AlertAcknowledgment.user_email == actor.email,
            AlertAcknowledgment.acknowledged_at.is_(None),
        )
    ).all()
    if not alert_ids:
        return []
    alerts = db.scalars(select(Alert).where(Alert.id.in_(alert_ids))).all()
    return [_alert_to_out(a) for a in alerts]


# --- Alert Detail ---

@router.get("/{alert_id}")
def get_alert_detail(
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
        "pharmacist_notes": alert.pharmacist_notes,
        "triaged_by_name": alert.triaged_by_name,
        "triaged_at": alert.triaged_at.isoformat() if alert.triaged_at else None,
        "actions": [
            {
                "id": str(act.id),
                "action_type": act.action_type,
                "description": act.description,
                "notes": act.notes,
                "assigned_to_name": act.assigned_to_name,
                "deadline": act.deadline.isoformat() if act.deadline else None,
                "performed_by_name": act.performed_by_name,
                "performed_at": act.performed_at.isoformat() if act.performed_at else None,
                "completed_at": act.completed_at.isoformat() if act.completed_at else None,
                "completed_by": act.completed_by,
                "patients_identified": act.patients_identified,
                "applies_to_practice": act.applies_to_practice,
            }
            for act in alert.actions
        ],
        "acknowledgments": [
            {
                "id": str(ack.id),
                "user_email": ack.user_email,
                "user_name": ack.user_name,
                "requested_at": ack.requested_at.isoformat() if ack.requested_at else None,
                "acknowledged_at": ack.acknowledged_at.isoformat() if ack.acknowledged_at else None,
                "method": ack.method,
            }
            for ack in alert.acknowledgments
        ],
    }


# --- Actions ---

class AlertActionCreate(BaseModel):
    action_type: str
    description: str | None = None
    notes: str | None = None
    assigned_to_name: str | None = None
    assigned_to_email: str | None = None
    deadline: str | None = None
    patients_identified: int | None = None
    applies_to_practice: bool | None = None


@router.post("/{alert_id}/actions", status_code=201)
def add_alert_action(
    alert_id: uuid.UUID,
    body: AlertActionCreate,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    from datetime import date as date_type
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    deadline = None
    if body.deadline:
        try:
            deadline = date_type.fromisoformat(body.deadline[:10])
        except ValueError:
            pass

    action = AlertAction(
        alert_id=alert.id,
        action_type=body.action_type,
        description=body.description,
        notes=body.notes,
        assigned_to_name=body.assigned_to_name,
        assigned_to_email=body.assigned_to_email,
        deadline=deadline,
        performed_by_email=actor.email,
        performed_by_name=actor.name,
        patients_identified=body.patients_identified,
        applies_to_practice=body.applies_to_practice,
    )
    db.add(action)
    db.commit()
    return {"id": str(action.id), "status": "created"}


@router.patch("/{alert_id}/actions/{action_id}/complete")
def complete_alert_action(
    alert_id: uuid.UUID,
    action_id: uuid.UUID,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    """Mark an alert action as completed."""
    action = db.scalar(
        select(AlertAction).where(AlertAction.id == action_id, AlertAction.alert_id == alert_id)
    )
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    action.completed_at = datetime.utcnow()
    action.completed_by = actor.name

    # Check if all non-triage actions are now complete — if so, mark alert complete
    alert = db.get(Alert, alert_id)
    real_actions = [a for a in alert.actions if a.action_type != "triage_relevance"]
    if real_actions and all(a.completed_at for a in real_actions):
        alert.status = AlertStatus.COMPLETE
    db.commit()
    return {"id": str(action.id), "completed_at": action.completed_at.isoformat()}


# --- Status ---

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


# --- Triage ---

class AlertTriageBody(BaseModel):
    is_relevant: bool
    notes: str | None = None


@router.patch("/{alert_id}/triage")
def triage_alert(
    alert_id: uuid.UUID,
    body: AlertTriageBody,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    """Pharmacist marks an alert as relevant or not relevant to the practice."""
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.is_relevant = body.is_relevant
    alert.triaged_by_email = actor.email
    alert.triaged_by_name = actor.name
    alert.triaged_at = datetime.utcnow()

    if body.is_relevant:
        alert.status = AlertStatus.IN_PROGRESS
    else:
        alert.status = AlertStatus.NOT_APPLICABLE

    # Audit action
    db.add(AlertAction(
        alert_id=alert.id,
        action_type="triage_relevance",
        notes=body.notes or f"Marked as {'relevant' if body.is_relevant else 'not relevant'}",
        performed_by_email=actor.email,
        performed_by_name=actor.name,
        applies_to_practice=body.is_relevant,
    ))

    # If relevant, create acknowledgment requests for all clinical staff
    if body.is_relevant:
        clinical_staff = db.scalars(
            select(User).where(User.is_clinical == True, User.is_active == True)
        ).all()
        for user in clinical_staff:
            db.add(AlertAcknowledgment(
                alert_id=alert.id,
                user_email=user.email,
                user_name=user.name,
            ))

    db.commit()
    return {"id": str(alert.id), "is_relevant": alert.is_relevant, "status": alert.status.value}


# --- Acknowledge ---

@router.post("/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: uuid.UUID,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    """Current user acknowledges they have read the alert (CQC read receipt)."""
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    ack = db.scalar(
        select(AlertAcknowledgment).where(
            AlertAcknowledgment.alert_id == alert_id,
            AlertAcknowledgment.user_email == actor.email,
        )
    )
    if ack:
        if not ack.acknowledged_at:
            ack.acknowledged_at = datetime.utcnow()
            ack.method = "in_app"
            db.commit()
        return {"status": "acknowledged", "acknowledged_at": ack.acknowledged_at.isoformat()}

    # Create one if not pre-created (e.g. user was added after triage)
    ack = AlertAcknowledgment(
        alert_id=alert_id,
        user_email=actor.email,
        user_name=actor.name,
        acknowledged_at=datetime.utcnow(),
        method="in_app",
    )
    db.add(ack)
    db.commit()
    return {"status": "acknowledged", "acknowledged_at": ack.acknowledged_at.isoformat()}


# --- Pharmacist notes ---

class PharmacistNotesBody(BaseModel):
    pharmacist_notes: str


@router.patch("/{alert_id}/notes")
def update_pharmacist_notes(
    alert_id: uuid.UUID,
    body: PharmacistNotesBody,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    """Save pharmacist's summary/notes for a composite alert or FSN."""
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.pharmacist_notes = body.pharmacist_notes
    db.commit()
    return {"status": "saved"}


# --- Manual acknowledgment (on behalf of another user, e.g. from email read receipt) ---

class ManualAckBody(BaseModel):
    user_email: str
    method: str = "email"  # email, clinical_meeting, verbal


@router.patch("/{alert_id}/acknowledge/{ack_id}")
def manual_acknowledge(
    alert_id: uuid.UUID,
    ack_id: uuid.UUID,
    body: ManualAckBody,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    """Manually mark a clinician as having acknowledged the alert (e.g. from email read receipt)."""
    ack = db.scalar(
        select(AlertAcknowledgment).where(
            AlertAcknowledgment.id == ack_id,
            AlertAcknowledgment.alert_id == alert_id,
        )
    )
    if not ack:
        raise HTTPException(status_code=404, detail="Acknowledgment not found")
    if not ack.acknowledged_at:
        ack.acknowledged_at = datetime.utcnow()
        ack.method = body.method
        db.commit()
    return {"status": "acknowledged", "acknowledged_at": ack.acknowledged_at.isoformat(), "method": ack.method}


# --- Completion report ---

@router.get("/{alert_id}/report")
def get_alert_report(
    alert_id: uuid.UUID,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    """Generate a completion report for a relevant alert — actions taken, acknowledgments, timeline."""
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    real_actions = [a for a in alert.actions if a.action_type != "triage_relevance"]
    completed_actions = [a for a in real_actions if a.completed_at]
    open_actions = [a for a in real_actions if not a.completed_at]
    acked = [a for a in alert.acknowledgments if a.acknowledged_at]
    pending_acks = [a for a in alert.acknowledgments if not a.acknowledged_at]

    return {
        "alert_id": str(alert.id),
        "title": alert.title,
        "source": alert.source.value,
        "issued_date": alert.issued_date.isoformat() if alert.issued_date else None,
        "status": alert.status.value,
        "is_relevant": alert.is_relevant,
        "triage": {
            "triaged_by": alert.triaged_by_name,
            "triaged_at": alert.triaged_at.isoformat() if alert.triaged_at else None,
        },
        "actions_summary": {
            "total": len(real_actions),
            "completed": len(completed_actions),
            "open": len(open_actions),
            "all_complete": len(open_actions) == 0 and len(real_actions) > 0,
        },
        "actions": [
            {
                "description": a.description or a.notes,
                "action_type": a.action_type,
                "assigned_to": a.assigned_to_name,
                "deadline": a.deadline.isoformat() if a.deadline else None,
                "completed_at": a.completed_at.isoformat() if a.completed_at else None,
                "completed_by": a.completed_by,
            }
            for a in real_actions
        ],
        "acknowledgments_summary": {
            "total": len(alert.acknowledgments),
            "acknowledged": len(acked),
            "pending": len(pending_acks),
        },
        "acknowledgments": [
            {
                "name": a.user_name,
                "acknowledged_at": a.acknowledged_at.isoformat() if a.acknowledged_at else None,
                "method": a.method,
            }
            for a in alert.acknowledgments
        ],
    }


# --- AI Suggest Actions (proxy to agent) ---

@router.post("/{alert_id}/suggest-actions")
async def suggest_alert_actions(
    alert_id: uuid.UUID,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    """Proxy to agent runtime for AI-suggested actions on an alert."""
    import httpx
    from app.core.config import settings

    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{settings.AGENT_RUNTIME_URL}/run/suggest-alert-actions",
                json={"alert_id": str(alert_id)},
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Agent runtime not available.")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Agent error: {e.response.text[:200]}")
    except httpx.ReadTimeout:
        raise HTTPException(status_code=504, detail="Agent timed out (>120s). Try again.")


