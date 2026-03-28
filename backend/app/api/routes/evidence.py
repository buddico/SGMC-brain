"""Evidence routes - CQC evidence pack generation structured by key questions."""

import csv
import io
import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_actor, get_session
from app.core.auth import Actor
from app.models.alert import Alert, AlertStatus
from app.models.audit import AuditLog
from app.models.compliance import CheckTemplate, StaffCheck
from app.models.event import Event, EventAction, EventStatus
from app.models.evidence import EvidenceItem, EvidencePack, EvidencePackStatus
from app.models.policy import Policy, PolicyCQCMapping, PolicyStatus, PolicyVersion
from app.models.risk import Risk, RiskReview

router = APIRouter(prefix="/evidence", tags=["evidence"])

# CQC domain → key question mapping
DOMAIN_TO_CQC = {
    "clinical_safety": "safe",
    "ipc_health_safety": "safe",
    "clinical_quality": "effective",
    "workforce": "effective",
    "patient_experience": "caring",
    "patient_access": "responsive",
    "business_resilience": "well_led",
    "information_governance": "well_led",
    "governance": "well_led",
}

CQC_QUESTIONS = {
    "safe": "Safe – Are people protected from abuse and avoidable harm?",
    "effective": "Effective – Do outcomes reflect current evidence-based guidance?",
    "caring": "Caring – Do staff treat people with compassion and dignity?",
    "responsive": "Responsive – Are services organised to meet people's needs?",
    "well_led": "Well-led – Does leadership assure high-quality, person-centred care?",
}


class EvidencePackOut(BaseModel):
    id: str
    title: str
    description: str | None
    cqc_key_question: str | None
    period_start: date
    period_end: date
    status: str
    summary: dict | None
    items_count: int = 0
    generated_by: str | None
    created_at: str

    model_config = {"from_attributes": True}


@router.get("/packs", response_model=list[EvidencePackOut])
def list_evidence_packs(
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    packs = db.scalars(
        select(EvidencePack).order_by(EvidencePack.created_at.desc())
    ).all()
    return [
        EvidencePackOut(
            id=str(p.id), title=p.title, description=p.description,
            cqc_key_question=p.cqc_key_question,
            period_start=p.period_start, period_end=p.period_end,
            status=p.status.value, summary=p.summary,
            items_count=len(p.items),
            generated_by=p.generated_by,
            created_at=p.created_at.isoformat() if p.created_at else "",
        )
        for p in packs
    ]


class GeneratePackRequest(BaseModel):
    title: str | None = None
    cqc_key_question: str | None = None
    period_start: date
    period_end: date


@router.post("/generate", status_code=201)
def generate_evidence_pack(
    body: GeneratePackRequest,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    """Generate a CQC evidence pack structured by the 5 key questions."""
    title = body.title or f"CQC Evidence Pack: {body.period_start} to {body.period_end}"
    period_start_dt = datetime.combine(body.period_start, datetime.min.time())
    period_end_dt = datetime.combine(body.period_end, datetime.max.time())

    pack = EvidencePack(
        title=title,
        cqc_key_question=body.cqc_key_question,
        period_start=body.period_start,
        period_end=body.period_end,
        status=EvidencePackStatus.GENERATING,
        generated_by=actor.email,
    )
    db.add(pack)
    db.flush()

    items = []
    sort_order = 0

    # Load all data
    policies = db.scalars(
        select(Policy).where(Policy.status == PolicyStatus.ACTIVE).order_by(Policy.domain, Policy.title)
    ).all()
    events = db.scalars(
        select(Event).where(
            Event.created_at >= period_start_dt,
            Event.created_at <= period_end_dt,
        ).order_by(Event.created_at)
    ).all()
    risks = db.scalars(select(Risk).order_by(Risk.risk_score.desc())).all()
    alerts = db.scalars(
        select(Alert).where(
            Alert.created_at >= period_start_dt,
            Alert.created_at <= period_end_dt,
        ).order_by(Alert.created_at)
    ).all()
    audit_entries = db.scalars(
        select(AuditLog).where(
            AuditLog.timestamp >= period_start_dt,
            AuditLog.timestamp <= period_end_dt,
        ).order_by(AuditLog.timestamp)
    ).all()

    # --- Structure by CQC key question ---

    for cqc_key, cqc_title in CQC_QUESTIONS.items():
        if body.cqc_key_question and body.cqc_key_question != cqc_key:
            continue

        # Section header
        sort_order += 1
        items.append(EvidenceItem(
            pack_id=pack.id, item_type="section_header", item_id=cqc_key,
            title=cqc_title,
            cqc_quality_statement=cqc_key,
            sort_order=sort_order,
        ))

        # Policies for this key question
        cqc_policies = [p for p in policies if DOMAIN_TO_CQC.get(p.domain.value) == cqc_key]
        if cqc_policies:
            sort_order += 1
            items.append(EvidenceItem(
                pack_id=pack.id, item_type="subsection", item_id=f"{cqc_key}_policies",
                title=f"Policies ({len(cqc_policies)})",
                summary=f"{sum(1 for p in cqc_policies if p.last_reviewed)} reviewed in cycle, "
                         f"{sum(1 for p in cqc_policies if p.next_review_due and p.next_review_due <= date.today())} overdue for review",
                cqc_quality_statement=cqc_key,
                sort_order=sort_order,
            ))
            for p in cqc_policies:
                sort_order += 1
                # Count versions in period
                versions_in_period = [
                    v for v in p.versions
                    if v.created_at and period_start_dt <= v.created_at <= period_end_dt
                ]
                items.append(EvidenceItem(
                    pack_id=pack.id, item_type="policy", item_id=str(p.id),
                    title=p.title,
                    summary=(
                        f"Lead: {p.policy_lead_name or 'Unassigned'} | "
                        f"Last reviewed: {p.last_reviewed or 'Never'} | "
                        f"Next review: {p.next_review_due or 'Not set'} | "
                        f"Versions this period: {len(versions_in_period)} | "
                        f"Acknowledgments: {len(p.acknowledgments)}"
                    ),
                    evidence_data={
                        "domain": p.domain.value, "status": p.status.value,
                        "lead": p.policy_lead_name, "last_reviewed": str(p.last_reviewed),
                        "next_review_due": str(p.next_review_due),
                        "versions_in_period": len(versions_in_period),
                        "acknowledgments": len(p.acknowledgments),
                    },
                    cqc_quality_statement=cqc_key,
                    sort_order=sort_order,
                ))

        # Risks for this key question category
        cqc_risk_categories = [cat for cat, q in DOMAIN_TO_CQC.items() if q == cqc_key]
        cqc_risks = [r for r in risks if r.category.value in cqc_risk_categories]
        if cqc_risks:
            sort_order += 1
            items.append(EvidenceItem(
                pack_id=pack.id, item_type="subsection", item_id=f"{cqc_key}_risks",
                title=f"Risk Register ({len(cqc_risks)} risks)",
                summary=f"High risks (>=15): {sum(1 for r in cqc_risks if r.risk_score >= 15)}, "
                         f"Reviewed in period: {sum(1 for r in cqc_risks if r.last_reviewed and r.last_reviewed >= body.period_start)}",
                cqc_quality_statement=cqc_key,
                sort_order=sort_order,
            ))
            for r in cqc_risks:
                sort_order += 1
                reviews_in_period = [
                    rv for rv in r.reviews
                    if rv.review_date and rv.review_date >= body.period_start
                ]
                items.append(EvidenceItem(
                    pack_id=pack.id, item_type="risk", item_id=str(r.id),
                    title=f"{r.reference}: {r.title}",
                    summary=(
                        f"Score: {r.risk_score} (L{r.likelihood}xI{r.impact}) | "
                        f"Status: {r.status.value} | Owner: {r.owner_name} | "
                        f"Controls: {'Yes' if r.existing_controls else 'None documented'} | "
                        f"Reviews this period: {len(reviews_in_period)} | "
                        f"Open actions: {sum(1 for a in r.actions if not a.completed_at)}"
                    ),
                    evidence_data={
                        "reference": r.reference, "score": r.risk_score,
                        "status": r.status.value, "category": r.category.value,
                        "owner": r.owner_name, "has_controls": bool(r.existing_controls),
                        "reviews_in_period": len(reviews_in_period),
                        "open_actions": sum(1 for a in r.actions if not a.completed_at),
                    },
                    cqc_quality_statement=cqc_key,
                    sort_order=sort_order,
                ))

    # --- Events section (cross-cutting) ---
    if events:
        sort_order += 1
        items.append(EvidenceItem(
            pack_id=pack.id, item_type="section_header", item_id="events",
            title=f"Significant Events & Incidents ({len(events)} in period)",
            sort_order=sort_order,
        ))

        # Learning loop evidence
        events_with_learning = [e for e in events if e.learning_outcomes]
        events_discussed = [e for e in events if e.discussed_at_meeting]
        events_with_actions = [e for e in events if e.actions]
        actions_completed = sum(1 for e in events for a in e.actions if a.completed_at)
        actions_total = sum(len(e.actions) for e in events)

        sort_order += 1
        items.append(EvidenceItem(
            pack_id=pack.id, item_type="learning_loop_summary", item_id="learning_loop",
            title="Learning Loop Evidence",
            summary=(
                f"Events reported: {len(events)} | "
                f"Discussed at meeting: {len(events_discussed)} | "
                f"Learning outcomes recorded: {len(events_with_learning)} | "
                f"Actions raised: {actions_total} | "
                f"Actions completed: {actions_completed}"
            ),
            evidence_data={
                "reported": len(events),
                "discussed": len(events_discussed),
                "with_learning": len(events_with_learning),
                "actions_total": actions_total,
                "actions_completed": actions_completed,
                "completion_rate": round(actions_completed / actions_total * 100) if actions_total > 0 else 0,
            },
            sort_order=sort_order,
        ))

        for e in events:
            sort_order += 1
            items.append(EvidenceItem(
                pack_id=pack.id, item_type="event", item_id=str(e.id),
                title=f"{e.reference}: {e.title}",
                summary=(
                    f"Type: {e.event_type.name if e.event_type else 'N/A'} | "
                    f"Severity: {e.severity.value if e.severity else 'N/A'} | "
                    f"Status: {e.status.value} | "
                    f"Meeting discussed: {'Yes' if e.discussed_at_meeting else 'No'} | "
                    f"Learning recorded: {'Yes' if e.learning_outcomes else 'No'} | "
                    f"Actions: {len(e.actions)} ({sum(1 for a in e.actions if a.completed_at)} complete) | "
                    f"Linked risks: {len(e.linked_risk_ids or [])} | "
                    f"Linked policies: {len(e.linked_policy_ids or [])} | "
                    f"Duty of candour: {'Required' if e.duty_of_candour_required else 'N/A'}"
                ),
                evidence_data={
                    "reference": e.reference,
                    "event_type": e.event_type.name if e.event_type else None,
                    "severity": e.severity.value if e.severity else None,
                    "status": e.status.value,
                    "discussed": e.discussed_at_meeting,
                    "learning_recorded": bool(e.learning_outcomes),
                    "learning_outcomes": e.learning_outcomes,
                    "actions_count": len(e.actions),
                    "actions_completed": sum(1 for a in e.actions if a.completed_at),
                    "linked_risks": len(e.linked_risk_ids or []),
                    "linked_policies": len(e.linked_policy_ids or []),
                    "duty_of_candour": e.duty_of_candour_required,
                },
                sort_order=sort_order,
            ))

    # --- Alerts section ---
    if alerts:
        sort_order += 1
        items.append(EvidenceItem(
            pack_id=pack.id, item_type="section_header", item_id="alerts",
            title=f"Safety Alerts ({len(alerts)} in period)",
            sort_order=sort_order,
        ))
        for a in alerts:
            sort_order += 1
            ack_data = [
                {"name": ack.user_name, "acknowledged_at": ack.acknowledged_at.isoformat() if ack.acknowledged_at else None}
                for ack in a.acknowledgments
            ]
            items.append(EvidenceItem(
                pack_id=pack.id, item_type="alert", item_id=str(a.id),
                title=a.title,
                summary=(
                    f"Source: {a.source.value} | Status: {a.status.value} | "
                    f"Relevant: {'Yes' if a.is_relevant else 'No' if a.is_relevant is False else 'Untriaged'} | "
                    f"Triaged by: {a.triaged_by_name or 'N/A'} | "
                    f"Actions: {len(a.actions)} | "
                    f"Read receipts: {sum(1 for ack in a.acknowledgments if ack.acknowledged_at)}/{len(a.acknowledgments)}"
                ),
                evidence_data={
                    "source": a.source.value,
                    "status": a.status.value,
                    "is_relevant": a.is_relevant,
                    "triaged_by": a.triaged_by_name,
                    "triaged_at": a.triaged_at.isoformat() if a.triaged_at else None,
                    "actions": len(a.actions),
                    "acknowledgments": ack_data,
                    "acknowledgment_rate": f"{sum(1 for ack in a.acknowledgments if ack.acknowledged_at)}/{len(a.acknowledgments)}",
                },
                sort_order=sort_order,
            ))

    # --- Governance activity (audit trail summary) ---
    if audit_entries:
        sort_order += 1
        action_counts: dict[str, int] = {}
        for entry in audit_entries:
            action_counts[entry.action] = action_counts.get(entry.action, 0) + 1
        items.append(EvidenceItem(
            pack_id=pack.id, item_type="governance_activity", item_id="audit_summary",
            title=f"Governance Activity ({len(audit_entries)} actions in period)",
            summary=" | ".join(f"{action}: {count}" for action, count in sorted(action_counts.items())),
            evidence_data={"total": len(audit_entries), "by_action": action_counts},
            sort_order=sort_order,
        ))

    db.add_all(items)

    # Summary
    pack.summary = {
        "policies_count": len(policies),
        "policies_reviewed": sum(1 for p in policies if p.last_reviewed and p.last_reviewed >= body.period_start),
        "policies_overdue": sum(1 for p in policies if p.next_review_due and p.next_review_due <= date.today()),
        "events_count": len(events),
        "events_closed": sum(1 for e in events if e.status == EventStatus.CLOSED),
        "events_with_learning": sum(1 for e in events if e.learning_outcomes),
        "events_discussed": sum(1 for e in events if e.discussed_at_meeting),
        "risks_count": len(risks),
        "risks_high": sum(1 for r in risks if r.risk_score >= 15),
        "risks_reviewed": sum(1 for r in risks if r.last_reviewed and r.last_reviewed >= body.period_start),
        "alerts_count": len(alerts),
        "alerts_actioned": sum(1 for a in alerts if a.status in (AlertStatus.COMPLETE, AlertStatus.NOT_APPLICABLE)),
        "audit_actions": len(audit_entries),
    }
    pack.status = EvidencePackStatus.READY
    db.commit()
    db.refresh(pack)

    return {
        "id": str(pack.id),
        "title": pack.title,
        "status": pack.status.value,
        "items_count": len(items),
        "summary": pack.summary,
    }


@router.get("/packs/{pack_id}")
def get_evidence_pack(
    pack_id: uuid.UUID,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    pack = db.get(EvidencePack, pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail="Evidence pack not found")

    # Group items by section
    sections: list[dict] = []
    current_section: dict | None = None
    for item in sorted(pack.items, key=lambda i: i.sort_order or 0):
        if item.item_type == "section_header":
            current_section = {"title": item.title, "key": item.item_id, "items": []}
            sections.append(current_section)
        elif current_section is not None:
            current_section["items"].append({
                "id": str(item.id),
                "item_type": item.item_type,
                "item_id": item.item_id,
                "title": item.title,
                "summary": item.summary,
                "evidence_data": item.evidence_data,
                "cqc_quality_statement": item.cqc_quality_statement,
            })
        else:
            # Items before any section header (shouldn't happen with new generation)
            if not sections:
                sections.append({"title": "General", "key": "general", "items": []})
            sections[-1]["items"].append({
                "id": str(item.id),
                "item_type": item.item_type,
                "item_id": item.item_id,
                "title": item.title,
                "summary": item.summary,
                "evidence_data": item.evidence_data,
                "cqc_quality_statement": item.cqc_quality_statement,
            })

    return {
        "id": str(pack.id),
        "title": pack.title,
        "cqc_key_question": pack.cqc_key_question,
        "period_start": pack.period_start.isoformat(),
        "period_end": pack.period_end.isoformat(),
        "status": pack.status.value,
        "summary": pack.summary,
        "generated_by": pack.generated_by,
        "created_at": pack.created_at.isoformat() if pack.created_at else "",
        "sections": sections,
        "total_items": len(pack.items),
    }


@router.get("/packs/{pack_id}/export.csv")
def export_evidence_csv(
    pack_id: uuid.UUID,
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    """Export evidence pack as CSV for CQC submission."""
    pack = db.get(EvidencePack, pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail="Evidence pack not found")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "CQC Key Question", "Section", "Item Type", "Reference/Title",
        "Summary", "Status", "Owner/Reporter", "Date",
    ])

    current_section = ""
    current_cqc = ""
    for item in sorted(pack.items, key=lambda i: i.sort_order or 0):
        if item.item_type == "section_header":
            current_section = item.title
            current_cqc = item.cqc_quality_statement or ""
            continue
        if item.item_type == "subsection":
            current_section = item.title
            continue

        data = item.evidence_data or {}
        owner = data.get("lead") or data.get("owner") or ""
        status = data.get("status") or ""
        ref_date = data.get("last_reviewed") or ""

        writer.writerow([
            current_cqc,
            current_section,
            item.item_type,
            item.title,
            item.summary or "",
            status,
            owner,
            ref_date,
        ])

    output.seek(0)
    filename = f"sgmc_evidence_{pack.period_start}_{pack.period_end}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/dashboard")
def evidence_dashboard(
    db: Session = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    policies_active = db.scalar(select(func.count(Policy.id)).where(Policy.status == PolicyStatus.ACTIVE)) or 0
    policies_review_due = db.scalar(
        select(func.count(Policy.id)).where(
            Policy.status == PolicyStatus.ACTIVE,
            Policy.next_review_due <= date.today(),
        )
    ) or 0
    events_open = db.scalar(
        select(func.count(Event.id)).where(Event.status != EventStatus.CLOSED)
    ) or 0
    events_total = db.scalar(select(func.count(Event.id))) or 0
    risks_open = db.scalar(select(func.count(Risk.id)).where(Risk.status == "open")) or 0
    risks_high = db.scalar(select(func.count(Risk.id)).where(Risk.risk_score >= 15)) or 0
    alerts_new = db.scalar(select(func.count(Alert.id)).where(Alert.status == AlertStatus.NEW)) or 0

    return {
        "policies_active": policies_active,
        "policies_review_due": policies_review_due,
        "events_open": events_open,
        "events_total": events_total,
        "risks_open": risks_open,
        "risks_high": risks_high,
        "alerts_new": alerts_new,
        "checks_overdue": 0,
    }
