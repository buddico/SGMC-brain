"""Event CRUD routes - full lifecycle with actions and investigation workflow."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_actor, get_session
from app.core.auth import Actor
from app.models.event import Event, EventAction, EventHistory, EventSeverity, EventStatus, EventType

router = APIRouter(prefix="/events", tags=["events"])


# --- Event Types ---

class EventTypeOut(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None
    version: str
    is_active: bool
    json_schema: dict
    ui_schema: dict | None
    category: str | None
    display_order: int
    tags: list | None
    examples: list | None
    typical_actions: list | None
    cqc_category: str | None

    model_config = {"from_attributes": True}


@router.get("/types", response_model=list[EventTypeOut])
def list_event_types(
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    types = db.scalars(select(EventType).where(EventType.is_active).order_by(EventType.display_order, EventType.name)).all()
    return [
        EventTypeOut(
            id=str(t.id), name=t.name, slug=t.slug, description=t.description,
            version=t.version, is_active=t.is_active, json_schema=t.json_schema,
            ui_schema=t.ui_schema, category=t.category, display_order=t.display_order or 0,
            tags=t.tags, examples=t.examples, typical_actions=t.typical_actions,
            cqc_category=t.cqc_category,
        )
        for t in types
    ]


# --- Events ---

class EventCreate(BaseModel):
    event_type_id: str
    title: str
    severity: EventSeverity | None = None
    occurred_at: str | None = None
    payload: dict
    involved_staff: list[dict] = []  # [{name, email, job_title}]


class EventOut(BaseModel):
    id: str
    event_type_id: str
    event_type_name: str | None = None
    reference: str | None
    title: str
    severity: str | None
    status: str
    occurred_at: str | None
    reported_by_name: str
    reported_by_email: str
    discussed_at_meeting: bool
    duty_of_candour_required: bool
    created_at: str
    actions_count: int = 0

    model_config = {"from_attributes": True}


def _generate_reference(db: Session, event_type: EventType) -> str:
    year = datetime.now().year
    prefix = event_type.slug[:2].upper()
    count = db.scalar(
        select(func.count(Event.id)).where(Event.event_type_id == event_type.id)
    ) or 0
    return f"{prefix}-{year}-{count + 1:03d}"


@router.get("", response_model=list[EventOut])
def list_events(
    event_type_id: str | None = None,
    status: EventStatus | None = None,
    severity: EventSeverity | None = None,
    q: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    stmt = select(Event).join(EventType)
    if event_type_id:
        stmt = stmt.where(Event.event_type_id == uuid.UUID(event_type_id))
    if status:
        stmt = stmt.where(Event.status == status)
    if severity:
        stmt = stmt.where(Event.severity == severity)
    if q:
        stmt = stmt.where(Event.title.ilike(f"%{q}%"))
    stmt = stmt.order_by(Event.created_at.desc()).limit(limit).offset(offset)

    events = db.scalars(stmt).all()
    return [
        EventOut(
            id=str(e.id), event_type_id=str(e.event_type_id),
            event_type_name=e.event_type.name if e.event_type else None,
            reference=e.reference, title=e.title,
            severity=e.severity.value if e.severity else None,
            status=e.status.value,
            occurred_at=e.occurred_at.isoformat() if e.occurred_at else None,
            reported_by_name=e.reported_by_name, reported_by_email=e.reported_by_email,
            discussed_at_meeting=e.discussed_at_meeting,
            duty_of_candour_required=e.duty_of_candour_required,
            created_at=e.created_at.isoformat() if e.created_at else "",
            actions_count=len(e.actions),
        )
        for e in events
    ]


@router.post("", response_model=EventOut, status_code=201)
def create_event(
    body: EventCreate,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    event_type = db.get(EventType, uuid.UUID(body.event_type_id))
    if not event_type:
        raise HTTPException(status_code=400, detail="Invalid event type")

    reference = _generate_reference(db, event_type)
    event = Event(
        event_type_id=event_type.id, reference=reference, title=body.title,
        severity=body.severity, status=EventStatus.SUBMITTED, payload=body.payload,
        reported_by_email=actor.email, reported_by_name=actor.name,
        involved_staff=body.involved_staff if body.involved_staff else None,
    )
    db.add(event)
    db.flush()
    db.add(EventHistory(
        event_id=event.id, action="created", actor_email=actor.email,
        actor_name=actor.name, changes={"status": "submitted"},
    ))
    db.commit()
    db.refresh(event)
    return EventOut(
        id=str(event.id), event_type_id=str(event.event_type_id),
        event_type_name=event_type.name, reference=event.reference, title=event.title,
        severity=event.severity.value if event.severity else None,
        status=event.status.value,
        occurred_at=event.occurred_at.isoformat() if event.occurred_at else None,
        reported_by_name=event.reported_by_name, reported_by_email=event.reported_by_email,
        discussed_at_meeting=event.discussed_at_meeting,
        duty_of_candour_required=event.duty_of_candour_required,
        created_at=event.created_at.isoformat() if event.created_at else "",
    )


# --- Event Detail ---

@router.get("/{event_id}")
def get_event(
    event_id: uuid.UUID,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    from app.models.policy import Policy
    from app.models.risk import Risk

    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    linked_policies = []
    for pid in (event.linked_policy_ids or []):
        try:
            p = db.get(Policy, uuid.UUID(pid))
            if p:
                linked_policies.append({
                    "id": str(p.id), "title": p.title, "domain": p.domain.value,
                    "policy_lead_name": p.policy_lead_name, "policy_lead_email": p.policy_lead_email,
                })
        except ValueError:
            pass

    linked_risks = []
    for rid in (event.linked_risk_ids or []):
        try:
            r = db.get(Risk, uuid.UUID(rid))
            if r:
                linked_risks.append({"id": str(r.id), "reference": r.reference, "title": r.title, "risk_score": r.risk_score})
        except ValueError:
            pass

    return {
        "id": str(event.id),
        "event_type_id": str(event.event_type_id),
        "event_type_name": event.event_type.name if event.event_type else None,
        "reference": event.reference,
        "title": event.title,
        "severity": event.severity.value if event.severity else None,
        "status": event.status.value,
        "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
        "payload": event.payload,
        "reported_by_name": event.reported_by_name,
        "reported_by_email": event.reported_by_email,
        "involved_staff": event.involved_staff or [],
        "investigator_email": event.investigator_email,
        "investigation_notes": event.investigation_notes,
        "learning_outcomes": event.learning_outcomes,
        "discussed_at_meeting": event.discussed_at_meeting,
        "meeting_date": event.meeting_date.isoformat() if event.meeting_date else None,
        "meeting_notes": event.meeting_notes,
        "duty_of_candour_required": event.duty_of_candour_required,
        "duty_of_candour_completed": event.duty_of_candour_completed,
        "linked_policy_ids": event.linked_policy_ids or [],
        "linked_risk_ids": event.linked_risk_ids or [],
        "linked_policies": linked_policies,
        "linked_risks": linked_risks,
        "actions": [
            {
                "id": str(a.id), "description": a.description,
                "assigned_to_name": a.assigned_to_name, "assigned_to_email": a.assigned_to_email,
                "deadline": a.deadline.isoformat() if a.deadline else None,
                "completed_at": a.completed_at.isoformat() if a.completed_at else None,
                "completed_by": a.completed_by, "notes": a.notes,
                "created_by": a.created_by,
            }
            for a in event.actions
        ],
        "history": [
            {
                "id": str(h.id), "action": h.action, "actor_name": h.actor_name,
                "timestamp": h.timestamp.isoformat() if h.timestamp else None,
                "changes": h.changes,
            }
            for h in sorted(event.history, key=lambda x: x.timestamp, reverse=True)
        ],
        "created_at": event.created_at.isoformat() if event.created_at else "",
    }


# --- Involved Staff ---

class InvolvedStaffUpdate(BaseModel):
    involved_staff: list[dict]  # [{name, email, job_title}]


@router.put("/{event_id}/involved-staff")
def update_involved_staff(
    event_id: uuid.UUID,
    body: InvolvedStaffUpdate,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event.involved_staff = body.involved_staff
    db.add(EventHistory(
        event_id=event.id, action="involved_staff_updated",
        actor_email=actor.email, actor_name=actor.name,
        changes={"involved_staff": [s.get("name") for s in body.involved_staff]},
    ))
    db.commit()
    return {"status": "updated", "count": len(body.involved_staff)}


# --- Stage-specific updates ---

class InvestigationUpdate(BaseModel):
    investigator_email: str | None = None
    investigation_notes: str | None = None
    contributing_factors: str | None = None


class DiscussionUpdate(BaseModel):
    meeting_date: str | None = None
    meeting_notes: str | None = None


class LearningUpdate(BaseModel):
    learning_outcomes: str | None = None
    duty_of_candour_required: bool | None = None
    duty_of_candour_completed: bool | None = None


@router.patch("/{event_id}/investigate")
def update_investigation(
    event_id: uuid.UUID,
    body: InvestigationUpdate,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if body.investigator_email is not None:
        event.investigator_email = body.investigator_email
    if body.investigation_notes is not None:
        event.investigation_notes = body.investigation_notes

    # Auto-advance to under_investigation if still submitted
    if event.status == EventStatus.SUBMITTED:
        event.status = EventStatus.UNDER_INVESTIGATION

    db.add(EventHistory(
        event_id=event.id, action="investigation_updated",
        actor_email=actor.email, actor_name=actor.name,
        changes=body.model_dump(exclude_unset=True),
    ))
    db.commit()
    return {"status": event.status.value}


@router.patch("/{event_id}/discussion")
def update_discussion(
    event_id: uuid.UUID,
    body: DiscussionUpdate,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if body.meeting_date:
        event.discussed_at_meeting = True
        event.meeting_date = datetime.fromisoformat(body.meeting_date)
    if body.meeting_notes is not None:
        event.meeting_notes = body.meeting_notes

    if event.status in (EventStatus.SUBMITTED, EventStatus.UNDER_INVESTIGATION):
        event.status = EventStatus.DISCUSSED

    db.add(EventHistory(
        event_id=event.id, action="discussion_recorded",
        actor_email=actor.email, actor_name=actor.name,
        changes=body.model_dump(exclude_unset=True),
    ))
    db.commit()
    return {"status": event.status.value}


@router.patch("/{event_id}/learning")
def update_learning(
    event_id: uuid.UUID,
    body: LearningUpdate,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if body.learning_outcomes is not None:
        event.learning_outcomes = body.learning_outcomes
    if body.duty_of_candour_required is not None:
        event.duty_of_candour_required = body.duty_of_candour_required
    if body.duty_of_candour_completed is not None:
        event.duty_of_candour_completed = body.duty_of_candour_completed

    db.add(EventHistory(
        event_id=event.id, action="learning_recorded",
        actor_email=actor.email, actor_name=actor.name,
        changes=body.model_dump(exclude_unset=True),
    ))
    db.commit()
    return {"status": "updated"}


# --- Actions CRUD ---

class ActionCreate(BaseModel):
    description: str
    assigned_to_email: str | None = None
    assigned_to_name: str | None = None
    deadline: str | None = None


class ActionComplete(BaseModel):
    notes: str | None = None


@router.post("/{event_id}/actions", status_code=201)
def add_event_action(
    event_id: uuid.UUID,
    body: ActionCreate,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    deadline = datetime.fromisoformat(body.deadline) if body.deadline else None
    action = EventAction(
        event_id=event.id,
        description=body.description,
        assigned_to_email=body.assigned_to_email,
        assigned_to_name=body.assigned_to_name,
        deadline=deadline,
        created_by=actor.email,
    )
    db.add(action)

    # Auto-advance to actions_assigned
    if event.status in (EventStatus.SUBMITTED, EventStatus.UNDER_INVESTIGATION, EventStatus.DISCUSSED):
        event.status = EventStatus.ACTIONS_ASSIGNED

    db.add(EventHistory(
        event_id=event.id, action="action_added",
        actor_email=actor.email, actor_name=actor.name,
        changes={"description": body.description, "assigned_to": body.assigned_to_name},
    ))
    db.commit()
    db.refresh(action)
    return {
        "id": str(action.id), "description": action.description,
        "assigned_to_name": action.assigned_to_name,
        "deadline": action.deadline.isoformat() if action.deadline else None,
    }


@router.patch("/{event_id}/actions/{action_id}/complete")
def complete_event_action(
    event_id: uuid.UUID,
    action_id: uuid.UUID,
    body: ActionComplete,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    action = db.get(EventAction, action_id)
    if not action or action.event_id != event_id:
        raise HTTPException(status_code=404, detail="Action not found")

    action.completed_at = datetime.now()
    action.completed_by = actor.email
    if body.notes:
        action.notes = body.notes

    db.add(EventHistory(
        event_id=event_id, action="action_completed",
        actor_email=actor.email, actor_name=actor.name,
        changes={"action_id": str(action_id), "description": action.description},
    ))
    db.commit()
    return {"id": str(action.id), "status": "completed"}


@router.patch("/{event_id}/close")
def close_event(
    event_id: uuid.UUID,
    body: LearningUpdate,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Check all actions are complete
    open_actions = [a for a in event.actions if not a.completed_at]
    if open_actions:
        raise HTTPException(status_code=400, detail=f"{len(open_actions)} action(s) still open. Complete all actions before closing.")

    if body.learning_outcomes is not None:
        event.learning_outcomes = body.learning_outcomes
    event.status = EventStatus.CLOSED

    db.add(EventHistory(
        event_id=event.id, action="closed",
        actor_email=actor.email, actor_name=actor.name,
        changes={"learning_outcomes": body.learning_outcomes},
    ))
    db.commit()
    return {"status": "closed"}


# --- Links ---

class EventLinkUpdate(BaseModel):
    linked_policy_ids: list[str] | None = None
    linked_risk_ids: list[str] | None = None


@router.put("/{event_id}/links")
def update_event_links(
    event_id: uuid.UUID,
    body: EventLinkUpdate,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if body.linked_policy_ids is not None:
        event.linked_policy_ids = body.linked_policy_ids
    if body.linked_risk_ids is not None:
        event.linked_risk_ids = body.linked_risk_ids

    db.add(EventHistory(
        event_id=event.id, action="links_updated",
        actor_email=actor.email, actor_name=actor.name,
        changes={"linked_policy_ids": body.linked_policy_ids, "linked_risk_ids": body.linked_risk_ids},
    ))
    db.commit()
    return {"status": "updated"}


# --- AI Agent proxies ---

async def _proxy_agent(event_id: uuid.UUID, agent_path: str, db: Session):
    """Proxy a request to the agent runtime, validating the event exists first."""
    import httpx
    from app.core.config import settings

    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{settings.AGENT_RUNTIME_URL}/run/{agent_path}",
                json={"event_id": str(event_id)},
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Agent runtime not available. Start it with: cd agent && uvicorn main:app --port 8091")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Agent error: {e.response.text[:200]}")
    except httpx.ReadTimeout:
        raise HTTPException(status_code=504, detail="Agent timed out (>120s). Try again.")


@router.post("/{event_id}/triage")
async def triage_event(
    event_id: uuid.UUID,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    """AI triage — link relevant policies and risks to the event."""
    return await _proxy_agent(event_id, "event-triage", db)


@router.post("/{event_id}/suggest-investigation")
async def suggest_investigation(
    event_id: uuid.UUID,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    """AI-suggested investigation notes based on linked policies/risks and best practice."""
    return await _proxy_agent(event_id, "suggest-investigation", db)


@router.post("/{event_id}/suggest-actions")
async def suggest_actions(
    event_id: uuid.UUID,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    """AI-suggested actions with staff assignments based on linked policies/risks and best practice."""
    return await _proxy_agent(event_id, "suggest-actions", db)


# --- Status (legacy, keep for backward compat) ---

class EventStatusUpdate(BaseModel):
    status: EventStatus
    investigation_notes: str | None = None
    learning_outcomes: str | None = None


@router.patch("/{event_id}/status")
def update_event_status(
    event_id: uuid.UUID,
    body: EventStatusUpdate,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    old_status = event.status.value
    event.status = body.status
    if body.investigation_notes is not None:
        event.investigation_notes = body.investigation_notes
    if body.learning_outcomes is not None:
        event.learning_outcomes = body.learning_outcomes

    db.add(EventHistory(
        event_id=event.id, action="status_changed",
        actor_email=actor.email, actor_name=actor.name,
        changes={"old_status": old_status, "new_status": body.status.value},
    ))
    db.commit()
    return {"status": event.status.value}
