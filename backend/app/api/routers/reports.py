"""Report generation router."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from app.db.base import get_db
from app.models.engagement import Engagement, Finding, Report, AgentRun
from app.services.report_service import generate_html_report, generate_sarif_report
import json

router = APIRouter(prefix="/reports", tags=["reports"])

class ReportRequest(BaseModel):
    engagement_id: int
    format: str = "html"

@router.post("")
async def generate_report(body: ReportRequest, db: AsyncSession = Depends(get_db)):
    eng_result = await db.execute(select(Engagement).where(Engagement.id == body.engagement_id))
    eng = eng_result.scalar_one_or_none()
    if not eng:
        raise HTTPException(404, "Engagement not found")

    # Fetch all findings for this engagement
    runs_result = await db.execute(
        select(AgentRun).where(AgentRun.engagement_id == body.engagement_id)
    )
    run_ids = [r.id for r in runs_result.scalars().all()]

    findings_result = await db.execute(
        select(Finding).where(Finding.agent_run_id.in_(run_ids))
    )
    findings = findings_result.scalars().all()
    findings_dicts = [
        {
            "title": f.title,
            "severity": f.severity,
            "description": f.description,
            "cwe_id": f.cwe_id,
            "cve_id": f.cve_id,
            "payload": f.payload,
            "file_path": f.file_path,
            "line_number": f.line_number,
            "confidence": f.confidence,
        }
        for f in findings
    ]

    if body.format == "html":
        content = generate_html_report(eng.name, findings_dicts)
    elif body.format == "sarif":
        content = json.dumps(generate_sarif_report(eng.name, findings_dicts), indent=2)
    elif body.format == "json":
        content = json.dumps({"engagement": eng.name, "findings": findings_dicts}, indent=2)
    else:
        content = generate_html_report(eng.name, findings_dicts)

    report = Report(
        engagement_id=eng.id,
        title=f"{eng.name} — {body.format.upper()} Report",
        format=body.format,
        content=content,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return {
        "id": report.id,
        "title": report.title,
        "format": body.format,
        "findings_count": len(findings_dicts),
        "status": "ready",
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "engagement_id": eng.id,
    }


@router.get("")
async def list_reports(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Report).order_by(Report.created_at.desc()).limit(100))
    reports = result.scalars().all()
    return [
        {
            "id": r.id,
            "title": r.title,
            "format": r.format,
            "report_type": getattr(r, "report_type", "combined") or "combined",
            "agent_name": getattr(r, "agent_name", None),
            "findings_count": getattr(r, "findings_count", 0) or 0,
            "engagement_id": r.engagement_id,
            "agent_run_id": getattr(r, "agent_run_id", None),
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "status": "ready",
        }
        for r in reports
    ]


@router.get("/{report_id}/download")
async def download_report(report_id: int, db: AsyncSession = Depends(get_db)):
    from fastapi.responses import Response
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Report not found")
    media = "text/html" if report.format == "html" else "application/json"
    filename = f"cyphermind-report-{report_id}.{report.format}"
    return Response(
        content=report.content or "",
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

@router.get("/{report_id}/html", response_class=HTMLResponse)
async def get_report_html(report_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Report not found")
    return HTMLResponse(content=report.content or "<p>No content</p>")
