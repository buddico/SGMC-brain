"""Policy CRUD routes with review workflow."""

import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_actor, get_session
from app.core.auth import Actor
from app.models.audit import AuditLog
from app.models.policy import (
    CQCKeyQuestion,
    Policy,
    PolicyAcknowledgment,
    PolicyCQCMapping,
    PolicyDomain,
    PolicyStatus,
    PolicyVersion,
)

router = APIRouter(prefix="/policies", tags=["policies"])

# Valid status transitions
ALLOWED_TRANSITIONS = {
    PolicyStatus.DRAFT: [PolicyStatus.UNDER_REVIEW, PolicyStatus.ACTIVE],
    PolicyStatus.ACTIVE: [PolicyStatus.UNDER_REVIEW, PolicyStatus.ARCHIVED],
    PolicyStatus.UNDER_REVIEW: [PolicyStatus.ACTIVE, PolicyStatus.DRAFT],
    PolicyStatus.SUPERSEDED: [PolicyStatus.ARCHIVED],
    PolicyStatus.ARCHIVED: [PolicyStatus.DRAFT],
}


class PolicyCreate(BaseModel):
    title: str
    domain: PolicyDomain
    summary: str | None = None
    scope: str | None = None
    policy_lead_email: str | None = None
    policy_lead_name: str | None = None
    review_frequency_months: int = 12
    key_workflows: dict | None = None
    audit_checkpoints: list | None = None
    tags: list[str] = []
    applicable_roles: list[str] = []


class PolicyUpdate(BaseModel):
    title: str | None = None
    summary: str | None = None
    scope: str | None = None
    policy_lead_email: str | None = None
    policy_lead_name: str | None = None
    review_frequency_months: int | None = None
    key_workflows: dict | None = None
    audit_checkpoints: list | None = None
    tags: list[str] | None = None
    applicable_roles: list[str] | None = None


class PolicyOut(BaseModel):
    id: str
    title: str
    slug: str
    domain: str
    status: str
    policy_lead_email: str | None
    policy_lead_name: str | None
    review_frequency_months: int
    last_reviewed: date | None
    next_review_due: date | None
    summary: str | None
    scope: str | None
    tags: list | None
    applicable_roles: list | None
    key_workflows: dict | None
    audit_checkpoints: list | None
    created_at: str
    updated_at: str
    created_by: str | None
    updated_by: str | None

    model_config = {"from_attributes": True}


class PolicyDetailOut(PolicyOut):
    versions: list[dict]
    cqc_mappings: list[dict]
    acknowledgments_count: int
    allowed_transitions: list[str]


class VersionOut(BaseModel):
    id: str
    version: str
    change_summary: str | None
    created_at: str
    created_by: str | None


class StatusTransition(BaseModel):
    status: PolicyStatus
    change_summary: str | None = None


class ReviewComplete(BaseModel):
    change_summary: str | None = None
    next_review_months: int | None = None  # override review frequency if needed


class AcknowledgmentCreate(BaseModel):
    version_acknowledged: str | None = None


def _to_slug(title: str) -> str:
    return title.lower().replace(" ", "-").replace("&", "and")[:300]


def _policy_to_out(p: Policy) -> PolicyOut:
    return PolicyOut(
        id=str(p.id),
        title=p.title,
        slug=p.slug,
        domain=p.domain.value,
        status=p.status.value,
        policy_lead_email=p.policy_lead_email,
        policy_lead_name=p.policy_lead_name,
        review_frequency_months=p.review_frequency_months,
        last_reviewed=p.last_reviewed,
        next_review_due=p.next_review_due,
        summary=p.summary,
        scope=p.scope,
        tags=p.tags or [],
        applicable_roles=p.applicable_roles or [],
        key_workflows=p.key_workflows,
        audit_checkpoints=p.audit_checkpoints,
        created_at=p.created_at.isoformat() if p.created_at else "",
        updated_at=p.updated_at.isoformat() if p.updated_at else "",
        created_by=p.created_by,
        updated_by=p.updated_by,
    )


def _policy_to_detail(p: Policy) -> PolicyDetailOut:
    allowed = ALLOWED_TRANSITIONS.get(p.status, [])
    return PolicyDetailOut(
        **_policy_to_out(p).model_dump(),
        versions=[
            {
                "id": str(v.id),
                "version": v.version,
                "change_summary": v.change_summary,
                "created_at": v.created_at.isoformat() if v.created_at else "",
                "created_by": v.created_by,
            }
            for v in sorted(p.versions, key=lambda v: v.created_at, reverse=True)
        ],
        cqc_mappings=[
            {
                "id": str(m.id),
                "key_question": m.key_question.value,
                "quality_statement": m.quality_statement,
                "evidence_description": m.evidence_description,
            }
            for m in p.cqc_mappings
        ],
        acknowledgments_count=len(p.acknowledgments),
        allowed_transitions=[t.value for t in allowed],
    )


def _next_version(db: Session, policy_id: uuid.UUID) -> str:
    """Compute next version number (1.0, 1.1, 1.2, ...)."""
    latest = db.scalar(
        select(PolicyVersion)
        .where(PolicyVersion.policy_id == policy_id)
        .order_by(PolicyVersion.created_at.desc())
        .limit(1)
    )
    if not latest:
        return "1.0"
    parts = latest.version.split(".")
    major = int(parts[0]) if parts else 1
    minor = int(parts[1]) if len(parts) > 1 else 0
    return f"{major}.{minor + 1}"


@router.get("", response_model=list[PolicyOut])
def list_policies(
    domain: PolicyDomain | None = None,
    status: PolicyStatus | None = None,
    review_due: bool = False,
    q: str | None = Query(None, description="Search title/summary"),
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    stmt = select(Policy)
    if domain:
        stmt = stmt.where(Policy.domain == domain)
    if status:
        stmt = stmt.where(Policy.status == status)
    if review_due:
        stmt = stmt.where(
            Policy.status == PolicyStatus.ACTIVE,
            Policy.next_review_due <= date.today(),
        )
    if q:
        stmt = stmt.where(Policy.title.ilike(f"%{q}%"))
    stmt = stmt.order_by(Policy.domain, Policy.title)
    policies = db.scalars(stmt).all()
    return [_policy_to_out(p) for p in policies]


@router.get("/{policy_id}")
def get_policy(
    policy_id: uuid.UUID,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    policy = db.get(Policy, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return _policy_to_detail(policy)


@router.post("", response_model=PolicyOut, status_code=201)
def create_policy(
    body: PolicyCreate,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    policy = Policy(
        title=body.title,
        slug=_to_slug(body.title),
        domain=body.domain,
        summary=body.summary,
        scope=body.scope,
        policy_lead_email=body.policy_lead_email,
        policy_lead_name=body.policy_lead_name,
        review_frequency_months=body.review_frequency_months,
        key_workflows=body.key_workflows,
        audit_checkpoints=body.audit_checkpoints,
        tags=body.tags,
        applicable_roles=body.applicable_roles,
        created_by=actor.email,
        updated_by=actor.email,
    )
    db.add(policy)
    db.flush()

    # Create initial version
    version = PolicyVersion(
        policy_id=policy.id,
        version="1.0",
        change_summary="Initial policy creation",
        created_by=actor.email,
    )
    db.add(version)
    db.commit()
    db.refresh(policy)
    return _policy_to_out(policy)


@router.patch("/{policy_id}", response_model=PolicyOut)
def update_policy(
    policy_id: uuid.UUID,
    body: PolicyUpdate,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    policy = db.get(Policy, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(policy, field, value)
    policy.updated_by = actor.email

    db.commit()
    db.refresh(policy)
    return _policy_to_out(policy)


@router.post("/{policy_id}/transition")
def transition_policy(
    policy_id: uuid.UUID,
    body: StatusTransition,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    """Transition policy status with validation."""
    policy = db.get(Policy, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    allowed = ALLOWED_TRANSITIONS.get(policy.status, [])
    if body.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from '{policy.status.value}' to '{body.status.value}'. Allowed: {[s.value for s in allowed]}",
        )

    old_status = policy.status.value
    policy.status = body.status
    policy.updated_by = actor.email

    # Audit log
    db.add(AuditLog(
        actor_email=actor.email,
        actor_name=actor.name,
        action="policy.status_changed",
        resource_type="policy",
        resource_id=str(policy.id),
        description=f"Status changed from {old_status} to {body.status.value}",
        changes={"old_status": old_status, "new_status": body.status.value, "reason": body.change_summary},
    ))

    db.commit()
    db.refresh(policy)
    return _policy_to_detail(policy)


@router.post("/{policy_id}/complete-review")
def complete_review(
    policy_id: uuid.UUID,
    body: ReviewComplete,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    """Complete a review cycle: mark as reviewed, create new version, set next review date, activate."""
    policy = db.get(Policy, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    if policy.status not in (PolicyStatus.UNDER_REVIEW, PolicyStatus.ACTIVE):
        raise HTTPException(status_code=400, detail="Policy must be under review or active to complete a review")

    # Create new version
    new_version = _next_version(db, policy.id)
    version = PolicyVersion(
        policy_id=policy.id,
        version=new_version,
        change_summary=body.change_summary or "Reviewed - no changes",
        content_snapshot={
            "summary": policy.summary,
            "scope": policy.scope,
            "key_workflows": policy.key_workflows,
            "audit_checkpoints": policy.audit_checkpoints,
        },
        created_by=actor.email,
    )
    db.add(version)

    # Update review dates
    review_months = body.next_review_months or policy.review_frequency_months
    policy.last_reviewed = date.today()
    policy.next_review_due = date.today() + timedelta(days=review_months * 30)
    policy.status = PolicyStatus.ACTIVE
    policy.updated_by = actor.email

    # Audit log
    db.add(AuditLog(
        actor_email=actor.email,
        actor_name=actor.name,
        action="policy.review_completed",
        resource_type="policy",
        resource_id=str(policy.id),
        description=f"Review completed. Version {new_version}. Next review: {policy.next_review_due}",
        changes={"version": new_version, "change_summary": body.change_summary},
    ))

    db.commit()
    db.refresh(policy)
    return _policy_to_detail(policy)


@router.post("/{policy_id}/acknowledge")
def acknowledge_policy(
    policy_id: uuid.UUID,
    body: AcknowledgmentCreate,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    """Staff acknowledges they have read the policy."""
    policy = db.get(Policy, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    # Get latest version
    latest_version = db.scalar(
        select(PolicyVersion)
        .where(PolicyVersion.policy_id == policy.id)
        .order_by(PolicyVersion.created_at.desc())
        .limit(1)
    )
    version_str = body.version_acknowledged or (latest_version.version if latest_version else "1.0")

    # Check if already acknowledged this version
    existing = db.scalar(
        select(PolicyAcknowledgment).where(
            PolicyAcknowledgment.policy_id == policy.id,
            PolicyAcknowledgment.user_email == actor.email,
            PolicyAcknowledgment.version_acknowledged == version_str,
        )
    )
    if existing:
        return {"status": "already_acknowledged", "version": version_str}

    ack = PolicyAcknowledgment(
        policy_id=policy.id,
        user_email=actor.email,
        user_name=actor.name,
        version_acknowledged=version_str,
    )
    db.add(ack)
    db.commit()
    return {"status": "acknowledged", "version": version_str}


@router.get("/{policy_id}/versions", response_model=list[VersionOut])
def list_policy_versions(
    policy_id: uuid.UUID,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    versions = db.scalars(
        select(PolicyVersion)
        .where(PolicyVersion.policy_id == policy_id)
        .order_by(PolicyVersion.created_at.desc())
    ).all()
    return [
        VersionOut(
            id=str(v.id), version=v.version,
            change_summary=v.change_summary,
            created_at=v.created_at.isoformat() if v.created_at else "",
            created_by=v.created_by,
        )
        for v in versions
    ]


@router.get("/{policy_id}/acknowledgments")
def list_policy_acknowledgments(
    policy_id: uuid.UUID,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    acks = db.scalars(
        select(PolicyAcknowledgment)
        .where(PolicyAcknowledgment.policy_id == policy_id)
        .order_by(PolicyAcknowledgment.acknowledged_at.desc())
    ).all()
    return [
        {
            "id": str(a.id),
            "user_email": a.user_email,
            "user_name": a.user_name,
            "version_acknowledged": a.version_acknowledged,
            "acknowledged_at": a.acknowledged_at.isoformat() if a.acknowledged_at else "",
        }
        for a in acks
    ]
