import csv
import io
import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from app.database import SessionLocal
from app.services.collector import collect_and_save_reviews, extract_app_id_from_url, extract_app_name_from_url
from app.services.cleaner import clean_reviews
from app.services.analysis_service import analysis_service
from app.services.prd_service import prd_service
from app.services.testcase_service import testcase_service
from app.services.evidence_service import evidence_service
from app.services.import_service import import_service
from app.services.analysis_orchestrator import analysis_orchestrator
from app.services.progress_service import progress_service
from app.models import (
    AnalysisRun, AnalysisTopic, AnalysisFinding,
    PRDRequirement, PRDVersion, TestCase, Review, CleanedReview
)

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class AnalyzeRequest(BaseModel):
    app_url: str
    analysis_goal: str = ""
    max_reviews: int = 200


class ImportAnalyzeRequest(BaseModel):
    app_id: Optional[str] = None
    app_name: Optional[str] = None
    analysis_goal: str = ""
    format: str = "json"


# ============================================================
# Analysis endpoints
# ============================================================

@router.post("/analyze")
async def analyze_app(
    request: AnalyzeRequest,
    db: Session = Depends(get_db)
):
    """
    Start an async analysis pipeline. Returns immediately with run_id;
    the pipeline runs in a background thread. Poll /analyze/{run_id}/progress
    or subscribe to /analyze/{run_id}/stream for live updates.
    """
    try:
        app_id = extract_app_id_from_url(request.app_url)
        app_name = extract_app_name_from_url(request.app_url) or "Unknown App"

        if not app_id:
            raise HTTPException(status_code=400, detail="Invalid app URL: could not extract app_id")

        # Pre-create the analysis run so we have an ID
        run = AnalysisRun(
            app_id=app_id,
            app_name=app_name,
            analysis_goal=request.analysis_goal,
            status="running"
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        analysis_orchestrator.start_async_analysis(
            app_url=request.app_url,
            analysis_goal=request.analysis_goal,
            max_reviews=request.max_reviews,
            run_id=run.id,
        )

        return {
            "status": "started",
            "run_id": run.id,
            "app_id": app_id,
            "app_name": app_name,
            "message": "Analysis pipeline started. Poll /api/analyze/{run_id}/progress for updates."
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analyze/{run_id}/progress")
async def get_analysis_progress(run_id: int, db: Session = Depends(get_db)):
    """Get all progress events for a run."""
    run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    events = progress_service.get_all_events(run_id)
    is_done = progress_service.is_completed(run_id)

    return {
        "run_id": run_id,
        "status": run.status,
        "is_completed": is_done,
        "events": events,
        "current_stage": events[-1]["stage"] if events else None,
        "progress": events[-1]["progress"] if events else 0.0,
    }


@router.get("/analyze/{run_id}/stream")
async def stream_analysis_progress(run_id: int, request: Request):
    """Server-Sent Events stream for live progress updates."""
    async def event_generator():
        cursor = 0
        while True:
            if await request.is_disconnected():
                break

            events, cursor, is_done = progress_service.get_events_since(run_id, cursor)

            for evt in events:
                yield f"data: {json.dumps(evt)}\n\n"

            if is_done:
                yield f"data: {json.dumps({'type': 'done', 'run_id': run_id})}\n\n"
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ============================================================
# Import endpoints (JSON / CSV)
# ============================================================

@router.post("/import")
async def import_reviews(
    file: UploadFile = File(...),
    format: str = Form("json"),
    app_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Import reviews from a JSON or CSV file.
    The file format is documented in app/services/import_service.py.
    Imported reviews can then be analyzed via /api/analyze/imported.
    """
    try:
        content_bytes = await file.read()
        content = content_bytes.decode("utf-8")

        saved_count, detected_app_id, app_name = import_service.import_reviews(
            db, content, format=format, app_id_override=app_id
        )

        return {
            "status": "success",
            "reviews_imported": saved_count,
            "app_id": detected_app_id,
            "app_name": app_name,
            "format": format,
            "message": f"Imported {saved_count} reviews. Use /api/analyze/imported to analyze."
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import/analyze")
async def analyze_imported(
    app_id: str,
    app_name: str = "Imported App",
    analysis_goal: str = "",
    db: Session = Depends(get_db),
):
    """Run the analysis pipeline on previously imported reviews for a given app_id."""
    existing = db.query(Review).filter(Review.app_id == app_id).count()
    if existing == 0:
        raise HTTPException(status_code=404, detail=f"No reviews found for app_id={app_id}. Import first via /api/import.")

    run = AnalysisRun(
        app_id=app_id,
        app_name=app_name,
        analysis_goal=analysis_goal,
        status="running"
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    # Build a fake URL that the orchestrator can parse
    fake_url = f"https://apps.apple.com/us/app/imported/id{app_id}"

    # We bypass collection by pre-marking the collection stage as completed
    progress_service.emit(run.id, "collection", "completed",
                          f"Using {existing} imported reviews (no fetching required)",
                          0.15, {"reviews_collected": existing, "app_id": app_id, "app_name": app_name})

    # Run the rest of the pipeline in background (orchestrator will skip collection if reviews exist)
    analysis_orchestrator.start_async_analysis(
        app_url=fake_url,
        analysis_goal=analysis_goal,
        max_reviews=existing,
        run_id=run.id,
    )

    return {
        "status": "started",
        "run_id": run.id,
        "app_id": app_id,
        "app_name": app_name,
        "message": "Analysis started on imported data."
    }


# ============================================================
# Run endpoints
# ============================================================

@router.get("/runs")
async def list_runs(db: Session = Depends(get_db)):
    runs = db.query(AnalysisRun).order_by(AnalysisRun.started_at.desc()).all()
    return [{
        "id": run.id,
        "app_id": run.app_id,
        "app_name": run.app_name,
        "analysis_goal": run.analysis_goal,
        "status": run.status,
        "total_reviews": run.total_reviews,
        "cleaned_reviews": run.cleaned_reviews,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "error_message": run.error_message,
    } for run in runs]


@router.get("/runs/{run_id}")
async def get_run(run_id: int, db: Session = Depends(get_db)):
    run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    topics = db.query(AnalysisTopic).filter(AnalysisTopic.run_id == run_id).all()
    findings = db.query(AnalysisFinding).filter(AnalysisFinding.run_id == run_id).all()
    requirements = db.query(PRDRequirement).filter(PRDRequirement.run_id == run_id).all()
    versions = db.query(PRDVersion).filter(PRDVersion.run_id == run_id).all()
    test_cases = db.query(TestCase).filter(TestCase.run_id == run_id).all()

    return {
        "run": {
            "id": run.id,
            "app_id": run.app_id,
            "app_name": run.app_name,
            "analysis_goal": run.analysis_goal,
            "status": run.status,
            "total_reviews": run.total_reviews,
            "cleaned_reviews": run.cleaned_reviews,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "error_message": run.error_message,
        },
        "topics": [{
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "confidence": t.confidence,
            "sample_count": t.sample_count,
            "is_model_generated": t.is_model_generated,
        } for t in topics],
        "findings": [_serialize_finding(f) for f in findings],
        "requirements": [_serialize_requirement(r) for r in requirements],
        "versions": [{
            "id": v.id,
            "version_name": v.version_name,
            "description": v.description,
            "priority": v.priority,
            "estimated_effort": v.estimated_effort,
            "requirements_count": v.requirements_count,
        } for v in versions],
        "test_cases": [_serialize_test_case(tc) for tc in test_cases],
    }


@router.get("/runs/{run_id}/reviews")
async def get_run_reviews(run_id: int, limit: int = 100, offset: int = 0, db: Session = Depends(get_db)):
    run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    reviews = db.query(Review).filter(Review.app_id == run.app_id).offset(offset).limit(limit).all()
    return [{
        "id": r.id,
        "author": r.author,
        "rating": r.rating,
        "title": r.title or "",
        "content": r.content,
        "version": r.app_version or "",
        "date": r.review_date.isoformat() if r.review_date else None,
    } for r in reviews]


@router.get("/runs/{run_id}/findings")
async def get_run_findings(run_id: int, db: Session = Depends(get_db)):
    run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    findings = db.query(AnalysisFinding).filter(AnalysisFinding.run_id == run_id).all()
    return [_serialize_finding(f) for f in findings]


@router.get("/runs/{run_id}/requirements")
async def get_run_requirements(run_id: int, db: Session = Depends(get_db)):
    run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    requirements = db.query(PRDRequirement).filter(PRDRequirement.run_id == run_id).all()
    return [_serialize_requirement(r) for r in requirements]


@router.get("/runs/{run_id}/testcases")
async def get_run_testcases(run_id: int, db: Session = Depends(get_db)):
    run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    test_cases = db.query(TestCase).filter(TestCase.run_id == run_id).all()
    return [_serialize_test_case(tc) for tc in test_cases]


@router.get("/runs/{run_id}/traceability")
async def get_traceability(run_id: int, db: Session = Depends(get_db)):
    run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    findings = db.query(AnalysisFinding).filter(AnalysisFinding.run_id == run_id).all()
    requirements = db.query(PRDRequirement).filter(PRDRequirement.run_id == run_id).all()
    test_cases = db.query(TestCase).filter(TestCase.run_id == run_id).all()

    # Build forward chain: review -> finding -> requirement -> test_case
    chain = {
        "findings": [],
        "requirements": [],
        "test_cases": [],
        "reviews_count": run.total_reviews or 0,
        "assumption_count": sum(1 for f in findings if f.is_assumption),
        "conflict_count": sum(1 for f in findings if f.has_conflict),
    }

    for finding in findings:
        chain["findings"].append({
            "id": finding.id,
            "type": "finding",
            "text": finding.finding_text,
            "finding_type": finding.finding_type,
            "impact": finding.impact,
            "confidence": finding.confidence,
            "sample_count": finding.sample_count,
            "has_conflict": finding.has_conflict,
            "is_assumption": finding.is_assumption,
            "validation_status": finding.validation_status,
            "evidence_review_ids": finding.evidence_review_ids or [],
            "conflicting_review_ids": finding.conflicting_review_ids or [],
            "requirements": [r.id for r in requirements if r.finding_id == finding.id],
        })

    for req in requirements:
        chain["requirements"].append({
            "id": req.id,
            "type": "requirement",
            "text": req.requirement_text,
            "description": req.description,
            "priority": req.priority,
            "version": req.version,
            "finding_id": req.finding_id,
            "source_review_ids": req.source_review_ids or [],
            "test_cases": [tc.id for tc in test_cases if tc.requirement_id == req.id],
        })

    for tc in test_cases:
        chain["test_cases"].append({
            "id": tc.id,
            "type": "test_case",
            "text": tc.case_title,
            "description": tc.case_description,
            "test_type": tc.test_type,
            "priority": tc.priority,
            "requirement_id": tc.requirement_id,
        })

    return chain


# ============================================================
# Evidence endpoints
# ============================================================

@router.get("/evidence/search")
async def search_evidence(
    query: str,
    top_k: int = 5,
    db: Session = Depends(get_db),
):
    try:
        results = evidence_service.search_evidence(query, top_k)
        return {"query": query, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evidence/validate")
async def validate_finding_endpoint(request: Request):
    try:
        body = await request.json()
        finding_text = body.get("finding_text", "")
        topic = body.get("topic", "")
        result = evidence_service.validate_finding_with_evidence(finding_text, topic)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Serialization helpers
# ============================================================

def _serialize_finding(f: AnalysisFinding) -> Dict[str, Any]:
    return {
        "id": f.id,
        "run_id": f.run_id,
        "topic_id": f.topic_id,
        "finding_text": f.finding_text,
        "description": f.finding_text,  # alias for frontend
        "finding_type": f.finding_type,
        "impact": f.impact,
        "evidence_review_ids": f.evidence_review_ids or [],
        "sample_count": f.sample_count,
        "supporting_count": f.sample_count,  # alias for frontend
        "confidence": f.confidence or 0.0,
        "has_conflict": f.has_conflict,
        "conflicting_review_ids": f.conflicting_review_ids or [],
        "conflicting_count": len(f.conflicting_review_ids or []),  # alias for frontend
        "is_model_generated": f.is_model_generated,
        "is_assumption": f.is_assumption,
        "validation_status": f.validation_status,
    }


def _serialize_requirement(r: PRDRequirement) -> Dict[str, Any]:
    return {
        "id": r.id,
        "run_id": r.run_id,
        "finding_id": r.finding_id,
        "requirement_text": r.requirement_text,
        "title": r.requirement_text,  # alias for frontend
        "description": r.description or r.requirement_text,
        "user_value": r.user_value or "",
        "business_value": r.business_value or "",
        "requirement_type": r.requirement_type,
        "priority": r.priority,
        "version": r.version,
        "status": r.status,
        "estimated_effort": r.estimated_effort,
        "source_review_ids": r.source_review_ids or [],
        "is_model_generated": r.is_model_generated,
    }


def _serialize_test_case(tc: TestCase) -> Dict[str, Any]:
    return {
        "id": tc.id,
        "run_id": tc.run_id,
        "requirement_id": tc.requirement_id,
        "case_title": tc.case_title,
        "title": tc.case_title,  # alias for frontend
        "case_description": tc.case_description or "",
        "description": tc.case_description or "",  # alias for frontend
        "test_steps": tc.test_steps or [],
        "expected_result": tc.expected_result,
        "test_type": tc.test_type,
        "priority": tc.priority,
        "source_review_ids": tc.source_review_ids or [],
        "is_model_generated": tc.is_model_generated,
    }
