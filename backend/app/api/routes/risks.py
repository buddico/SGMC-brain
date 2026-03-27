"""Risk register CRUD routes with review cycles and linking."""

import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_actor, get_session
from app.core.auth import Actor
from app.models.audit import AuditLog
from app.models.event import Event
from app.models.policy import Policy
from app.models.risk import Risk, RiskAction, RiskCategory, RiskReview, RiskStatus

router = APIRouter(prefix="/risks", tags=["risks"])


class RiskCreate(BaseModel):
    title: str
    description: str
    category: RiskCategory
    likelihood: int  # 1-5
    impact: int  # 1-5
    existing_controls: str | None = None
    gaps_in_control: str | None = None
    owner_email: str
    owner_name: str
    linked_policy_ids: list[str] = []
    linked_event_ids: list[str] = []


class RiskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    category: RiskCategory | None = None
    likelihood: int | None = None
    impact: int | None = None
    existing_controls: str | None = None
    gaps_in_control: str | None = None
    owner_email: str | None = None
    owner_name: str | None = None
    status: RiskStatus | None = None


class RiskOut(BaseModel):
    id: str
    reference: str | None
    title: str
    description: str
    category: str
    status: str
    likelihood: int
    impact: int
    risk_score: int
    existing_controls: str | None
    gaps_in_control: str | None
    owner_name: str
    owner_email: str
    date_identified: date
    last_reviewed: date | None
    next_review_due: date | None
    linked_policy_ids: list | None
    linked_event_ids: list | None
    reviews_count: int = 0
    actions_count: int = 0
    created_at: str

    model_config = {"from_attributes": True}


class RiskDetailOut(RiskOut):
    reviews: list[dict]
    actions: list[dict]
    linked_policies: list[dict]
    linked_events: list[dict]


class LinkUpdate(BaseModel):
    linked_policy_ids: list[str] | None = None
    linked_event_ids: list[str] | None = None


class ReviewCreate(BaseModel):
    likelihood_after: int | None = None
    impact_after: int | None = None
    notes: str | None = None
    meeting_reference: str | None = None


class ActionCreate(BaseModel):
    description: str
    assigned_to_email: str | None = None
    assigned_to_name: str | None = None
    target_date: date | None = None


class ActionComplete(BaseModel):
    notes: str | None = None


def _risk_to_out(r: Risk) -> RiskOut:
    return RiskOut(
        id=str(r.id), reference=r.reference, title=r.title,
        description=r.description, category=r.category.value,
        status=r.status.value, likelihood=r.likelihood, impact=r.impact,
        risk_score=r.risk_score, existing_controls=r.existing_controls,
        gaps_in_control=r.gaps_in_control, owner_name=r.owner_name,
        owner_email=r.owner_email, date_identified=r.date_identified,
        last_reviewed=r.last_reviewed, next_review_due=r.next_review_due,
        linked_policy_ids=r.linked_policy_ids or [],
        linked_event_ids=r.linked_event_ids or [],
        reviews_count=len(r.reviews), actions_count=len(r.actions),
        created_at=r.created_at.isoformat() if r.created_at else "",
    )


def _risk_to_detail(r: Risk, db: Session) -> RiskDetailOut:
    # Resolve linked entities
    linked_policies = []
    for pid in (r.linked_policy_ids or []):
        try:
            p = db.get(Policy, uuid.UUID(pid))
            if p:
                linked_policies.append({"id": str(p.id), "title": p.title, "domain": p.domain.value, "status": p.status.value})
        except ValueError:
            pass

    linked_events = []
    for eid in (r.linked_event_ids or []):
        try:
            e = db.get(Event, uuid.UUID(eid))
            if e:
                linked_events.append({
                    "id": str(e.id), "reference": e.reference, "title": e.title,
                    "severity": e.severity.value if e.severity else None, "status": e.status.value,
                })
        except ValueError:
            pass

    return RiskDetailOut(
        **_risk_to_out(r).model_dump(),
        reviews=[
            {
                "id": str(rv.id), "reviewed_by_name": rv.reviewed_by_name,
                "review_date": rv.review_date.isoformat(),
                "likelihood_after": rv.likelihood_after, "impact_after": rv.impact_after,
                "score_after": rv.score_after, "notes": rv.notes,
                "meeting_reference": rv.meeting_reference,
            }
            for rv in sorted(r.reviews, key=lambda x: x.review_date, reverse=True)
        ],
        actions=[
            {
                "id": str(a.id), "description": a.description,
                "assigned_to_name": a.assigned_to_name, "target_date": a.target_date.isoformat() if a.target_date else None,
                "completed_at": a.completed_at.isoformat() if a.completed_at else None,
                "completed_by": a.completed_by, "notes": a.notes,
            }
            for a in r.actions
        ],
        linked_policies=linked_policies,
        linked_events=linked_events,
    )


@router.get("", response_model=list[RiskOut])
def list_risks(
    category: RiskCategory | None = None,
    status: RiskStatus | None = None,
    min_score: int | None = None,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    stmt = select(Risk)
    if category:
        stmt = stmt.where(Risk.category == category)
    if status:
        stmt = stmt.where(Risk.status == status)
    if min_score:
        stmt = stmt.where(Risk.risk_score >= min_score)
    stmt = stmt.order_by(Risk.risk_score.desc(), Risk.title)
    risks = db.scalars(stmt).all()
    return [_risk_to_out(r) for r in risks]


@router.get("/{risk_id}")
def get_risk(
    risk_id: uuid.UUID,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    risk = db.get(Risk, risk_id)
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")
    return _risk_to_detail(risk, db)


@router.post("", response_model=RiskOut, status_code=201)
def create_risk(
    body: RiskCreate,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    count = db.scalar(select(func.count(Risk.id))) or 0
    reference = f"RISK-{count + 1:03d}"

    risk = Risk(
        reference=reference,
        title=body.title,
        description=body.description,
        category=body.category,
        likelihood=body.likelihood,
        impact=body.impact,
        risk_score=body.likelihood * body.impact,
        existing_controls=body.existing_controls,
        gaps_in_control=body.gaps_in_control,
        owner_email=body.owner_email,
        owner_name=body.owner_name,
        date_identified=date.today(),
        next_review_due=date.today() + timedelta(days=90),
        linked_policy_ids=body.linked_policy_ids,
        linked_event_ids=body.linked_event_ids,
        created_by=actor.email,
    )
    db.add(risk)

    # Also update linked events to reference this risk
    db.flush()
    for eid in body.linked_event_ids:
        try:
            event = db.get(Event, uuid.UUID(eid))
            if event:
                existing = event.linked_risk_ids or []
                if str(risk.id) not in existing:
                    event.linked_risk_ids = existing + [str(risk.id)]
        except ValueError:
            pass

    db.add(AuditLog(
        actor_email=actor.email, actor_name=actor.name,
        action="risk.created", resource_type="risk", resource_id=str(risk.id),
        description=f"Risk {reference} created: {body.title} (score {risk.risk_score})",
    ))

    db.commit()
    db.refresh(risk)
    return _risk_to_out(risk)


@router.patch("/{risk_id}", response_model=RiskOut)
def update_risk(
    risk_id: uuid.UUID,
    body: RiskUpdate,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    risk = db.get(Risk, risk_id)
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(risk, field, value)

    # Recompute score if likelihood or impact changed
    if "likelihood" in update_data or "impact" in update_data:
        risk.risk_score = risk.likelihood * risk.impact

    db.commit()
    db.refresh(risk)
    return _risk_to_out(risk)


@router.put("/{risk_id}/links")
def update_risk_links(
    risk_id: uuid.UUID,
    body: LinkUpdate,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    """Update linked policies and/or events for a risk."""
    risk = db.get(Risk, risk_id)
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")

    if body.linked_policy_ids is not None:
        risk.linked_policy_ids = body.linked_policy_ids
    if body.linked_event_ids is not None:
        # Update bidirectional links on events
        old_event_ids = set(risk.linked_event_ids or [])
        new_event_ids = set(body.linked_event_ids)

        # Remove risk from events no longer linked
        for eid in old_event_ids - new_event_ids:
            try:
                event = db.get(Event, uuid.UUID(eid))
                if event and event.linked_risk_ids:
                    event.linked_risk_ids = [rid for rid in event.linked_risk_ids if rid != str(risk.id)]
            except ValueError:
                pass

        # Add risk to newly linked events
        for eid in new_event_ids - old_event_ids:
            try:
                event = db.get(Event, uuid.UUID(eid))
                if event:
                    existing = event.linked_risk_ids or []
                    if str(risk.id) not in existing:
                        event.linked_risk_ids = existing + [str(risk.id)]
            except ValueError:
                pass

        risk.linked_event_ids = body.linked_event_ids

    db.commit()
    db.refresh(risk)
    return _risk_to_detail(risk, db)


@router.post("/{risk_id}/reviews")
def add_risk_review(
    risk_id: uuid.UUID,
    body: ReviewCreate,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    risk = db.get(Risk, risk_id)
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")

    likelihood = body.likelihood_after or risk.likelihood
    impact = body.impact_after or risk.impact
    score = likelihood * impact

    review = RiskReview(
        risk_id=risk.id,
        reviewed_by_email=actor.email,
        reviewed_by_name=actor.name,
        review_date=date.today(),
        likelihood_after=likelihood,
        impact_after=impact,
        score_after=score,
        notes=body.notes,
        meeting_reference=body.meeting_reference,
    )
    db.add(review)

    # Update risk scores and dates
    risk.likelihood = likelihood
    risk.impact = impact
    risk.risk_score = score
    risk.last_reviewed = date.today()
    risk.next_review_due = date.today() + timedelta(days=90)

    db.commit()
    return {"id": str(review.id), "score_after": score}


@router.post("/{risk_id}/actions", status_code=201)
def add_risk_action(
    risk_id: uuid.UUID,
    body: ActionCreate,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    risk = db.get(Risk, risk_id)
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")

    action = RiskAction(
        risk_id=risk.id,
        description=body.description,
        assigned_to_email=body.assigned_to_email,
        assigned_to_name=body.assigned_to_name,
        target_date=body.target_date,
        created_by=actor.email,
    )
    db.add(action)
    db.commit()
    return {"id": str(action.id), "status": "created"}


@router.patch("/{risk_id}/actions/{action_id}/complete")
def complete_risk_action(
    risk_id: uuid.UUID,
    action_id: uuid.UUID,
    body: ActionComplete,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    action = db.get(RiskAction, action_id)
    if not action or action.risk_id != risk_id:
        raise HTTPException(status_code=404, detail="Action not found")

    from datetime import datetime
    action.completed_at = datetime.now()
    action.completed_by = actor.email
    action.notes = body.notes or action.notes
    db.commit()
    return {"id": str(action.id), "status": "completed"}
