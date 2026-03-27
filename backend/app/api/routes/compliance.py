"""Compliance check routes - training matrix, mandatory checks."""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_actor, get_session
from app.core.auth import Actor
from app.models.compliance import CheckCategory, CheckDocument, CheckTemplate, StaffCheck

router = APIRouter(prefix="/compliance", tags=["compliance"])


# --- Check Templates ---

class CheckTemplateCreate(BaseModel):
    name: str
    description: str | None = None
    category: CheckCategory
    frequency_months: int = 0
    requires_document: bool = False
    document_description: str | None = None
    applicable_roles: list[str] = []
    cqc_relevant: bool = False
    cqc_quality_statement: str | None = None
    linked_policy_id: str | None = None


class CheckTemplateOut(BaseModel):
    id: str
    name: str
    description: str | None
    category: str
    frequency_months: int
    requires_document: bool
    document_description: str | None
    applicable_roles: list | None
    cqc_relevant: bool
    cqc_quality_statement: str | None
    is_active: bool
    staff_checks_count: int = 0

    model_config = {"from_attributes": True}


def _template_to_out(t: CheckTemplate) -> CheckTemplateOut:
    return CheckTemplateOut(
        id=str(t.id), name=t.name, description=t.description,
        category=t.category.value, frequency_months=t.frequency_months,
        requires_document=t.requires_document,
        document_description=t.document_description,
        applicable_roles=t.applicable_roles or [],
        cqc_relevant=t.cqc_relevant,
        cqc_quality_statement=t.cqc_quality_statement,
        is_active=t.is_active,
        staff_checks_count=len(t.staff_checks),
    )


@router.get("/templates", response_model=list[CheckTemplateOut])
def list_check_templates(
    category: CheckCategory | None = None,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    stmt = select(CheckTemplate).where(CheckTemplate.is_active)
    if category:
        stmt = stmt.where(CheckTemplate.category == category)
    stmt = stmt.order_by(CheckTemplate.category, CheckTemplate.sort_order, CheckTemplate.name)
    templates = db.scalars(stmt).all()
    return [_template_to_out(t) for t in templates]


@router.post("/templates", response_model=CheckTemplateOut, status_code=201)
def create_check_template(
    body: CheckTemplateCreate,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    tmpl = CheckTemplate(
        name=body.name,
        description=body.description,
        category=body.category,
        frequency_months=body.frequency_months,
        requires_document=body.requires_document,
        document_description=body.document_description,
        applicable_roles=body.applicable_roles,
        cqc_relevant=body.cqc_relevant,
        cqc_quality_statement=body.cqc_quality_statement,
        linked_policy_id=uuid.UUID(body.linked_policy_id) if body.linked_policy_id else None,
        created_by=actor.email,
    )
    db.add(tmpl)
    db.commit()
    db.refresh(tmpl)
    return _template_to_out(tmpl)


# --- Staff Checks ---

class StaffCheckCreate(BaseModel):
    check_template_id: str
    staff_email: str
    staff_name: str
    completed_date: date | None = None
    expiry_date: date | None = None
    notes: str | None = None


class StaffCheckOut(BaseModel):
    id: str
    check_template_id: str
    template_name: str | None = None
    template_category: str | None = None
    staff_email: str
    staff_name: str
    completed_date: date | None
    expiry_date: date | None
    status: str
    notes: str | None
    documents_count: int = 0

    model_config = {"from_attributes": True}


def _compute_status(sc: StaffCheck) -> str:
    if not sc.completed_date:
        return "pending"
    if sc.check_template and sc.check_template.frequency_months == 0:
        return "completed"
    if not sc.expiry_date:
        return "completed"
    today = date.today()
    if sc.expiry_date < today:
        return "overdue"
    from datetime import timedelta
    if sc.expiry_date <= today + timedelta(days=30):
        return "due_soon"
    return "completed"


def _check_to_out(sc: StaffCheck) -> StaffCheckOut:
    return StaffCheckOut(
        id=str(sc.id),
        check_template_id=str(sc.check_template_id),
        template_name=sc.check_template.name if sc.check_template else None,
        template_category=sc.check_template.category.value if sc.check_template else None,
        staff_email=sc.staff_email,
        staff_name=sc.staff_name,
        completed_date=sc.completed_date,
        expiry_date=sc.expiry_date,
        status=_compute_status(sc),
        notes=sc.notes,
        documents_count=len(sc.documents),
    )


@router.get("/checks", response_model=list[StaffCheckOut])
def list_staff_checks(
    staff_email: str | None = None,
    template_id: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    stmt = select(StaffCheck).join(CheckTemplate)
    if staff_email:
        stmt = stmt.where(StaffCheck.staff_email == staff_email)
    if template_id:
        stmt = stmt.where(StaffCheck.check_template_id == uuid.UUID(template_id))
    checks = db.scalars(stmt.order_by(StaffCheck.staff_name)).all()
    results = [_check_to_out(sc) for sc in checks]
    if status_filter:
        results = [r for r in results if r.status == status_filter]
    return results


@router.post("/checks", response_model=StaffCheckOut, status_code=201)
def create_staff_check(
    body: StaffCheckCreate,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    sc = StaffCheck(
        check_template_id=uuid.UUID(body.check_template_id),
        staff_email=body.staff_email,
        staff_name=body.staff_name,
        completed_date=body.completed_date,
        expiry_date=body.expiry_date,
        notes=body.notes,
        completed_by=actor.email,
    )
    db.add(sc)
    db.commit()
    db.refresh(sc)
    return _check_to_out(sc)


@router.patch("/checks/{check_id}", response_model=StaffCheckOut)
def update_staff_check(
    check_id: uuid.UUID,
    body: StaffCheckCreate,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    sc = db.get(StaffCheck, check_id)
    if not sc:
        raise HTTPException(status_code=404, detail="Check not found")
    sc.completed_date = body.completed_date
    sc.expiry_date = body.expiry_date
    sc.notes = body.notes
    sc.completed_by = actor.email
    db.commit()
    db.refresh(sc)
    return _check_to_out(sc)
