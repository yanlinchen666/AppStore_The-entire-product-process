from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
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
from app.models import AnalysisRun, AnalysisTopic, AnalysisFinding, PRDRequirement, PRDVersion, TestCase, Review, CleanedReview

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

@router.post("/analyze")
async def analyze_app(
    request: AnalyzeRequest,
    db: Session = Depends(get_db)
):
    try:
        app_id = extract_app_id_from_url(request.app_url)
        app_name = extract_app_name_from_url(request.app_url) or "Unknown App"
        
        if not app_id:
            raise HTTPException(status_code=400, detail="Invalid app URL")
        
        saved_count, app_id, app_name = collect_and_save_reviews(db, request.app_url, max_reviews=request.max_reviews)
        
        if saved_count == 0:
            raise HTTPException(status_code=404, detail="No reviews collected")
        
        cleaned_count = clean_reviews(db, app_id)
        
        evidence_service.build_vector_index(app_id)
        
        analysis_result = analysis_service.analyze(db, app_id, app_name, request.analysis_goal)
        
        prd_result = prd_service.generate_prd(db, analysis_result['run_id'])
        
        testcase_result = testcase_service.generate_test_cases_for_prd(db, analysis_result['run_id'])
        
        return {
            "status": "success",
            "run_id": analysis_result['run_id'],
            "app_id": app_id,
            "app_name": app_name,
            "reviews_collected": saved_count,
            "reviews_cleaned": cleaned_count,
            "analysis": analysis_result,
            "prd": prd_result,
            "test_cases": testcase_result
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
        "completed_at": run.completed_at.isoformat() if run.completed_at else None
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
            "error_message": run.error_message
        },
        "topics": [{
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "confidence": t.confidence,
            "sample_count": t.sample_count
        } for t in topics],
        "findings": [{
            "id": f.id,
            "finding_text": f.finding_text,
            "topic_id": f.topic_id,
            "confidence": f.confidence,
            "has_conflict": f.has_conflict,
            "sample_count": f.sample_count,
            "evidence_review_ids": f.evidence_review_ids,
            "conflicting_review_ids": f.conflicting_review_ids
        } for f in findings],
        "requirements": [{
            "id": r.id,
            "requirement_text": r.requirement_text,
            "requirement_type": r.requirement_type,
            "priority": r.priority,
            "version": r.version,
            "status": r.status,
            "finding_id": r.finding_id
        } for r in requirements],
        "versions": [{
            "id": v.id,
            "version_name": v.version_name,
            "description": v.description,
            "priority": v.priority,
            "estimated_effort": v.estimated_effort,
            "requirements_count": v.requirements_count
        } for v in versions],
        "test_cases": [{
            "id": tc.id,
            "case_title": tc.case_title,
            "case_description": tc.case_description,
            "test_steps": tc.test_steps,
            "expected_result": tc.expected_result,
            "test_type": tc.test_type,
            "priority": tc.priority,
            "requirement_id": tc.requirement_id
        } for tc in test_cases]
    }

@router.get("/runs/{run_id}/reviews")
async def get_run_reviews(run_id: int, db: Session = Depends(get_db)):
    run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    reviews = db.query(Review).filter(Review.app_id == run.app_id).all()
    return [{
        "id": r.id,
        "author": r.author,
        "rating": r.rating,
        "title": r.title,
        "content": r.content,
        "version": r.app_version,
        "date": r.review_date.isoformat() if r.review_date else None
    } for r in reviews]

@router.get("/runs/{run_id}/traceability")
async def get_traceability(run_id: int, db: Session = Depends(get_db)):
    run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    findings = db.query(AnalysisFinding).filter(AnalysisFinding.run_id == run_id).all()
    requirements = db.query(PRDRequirement).filter(PRDRequirement.run_id == run_id).all()
    test_cases = db.query(TestCase).filter(TestCase.run_id == run_id).all()
    
    trace_map = {}
    
    for finding in findings:
        trace_map[f"finding_{finding.id}"] = {
            "type": "finding",
            "text": finding.finding_text,
            "evidence_count": len(finding.evidence_review_ids or []),
            "requirements": [],
            "confidence": finding.confidence
        }
    
    for req in requirements:
        req_key = f"requirement_{req.id}"
        trace_map[req_key] = {
            "type": "requirement",
            "text": req.requirement_text,
            "finding_id": req.finding_id,
            "test_cases": [],
            "priority": req.priority
        }
        
        if req.finding_id:
            finding_key = f"finding_{req.finding_id}"
            if finding_key in trace_map:
                trace_map[finding_key]["requirements"].append(req.id)
    
    for tc in test_cases:
        tc_key = f"testcase_{tc.id}"
        trace_map[tc_key] = {
            "type": "test_case",
            "text": tc.case_title,
            "requirement_id": tc.requirement_id,
            "priority": tc.priority
        }
        
        if tc.requirement_id:
            req_key = f"requirement_{tc.requirement_id}"
            if req_key in trace_map:
                trace_map[req_key]["test_cases"].append(tc.id)
    
    return trace_map

@router.get("/evidence/search")
async def search_evidence(
    query: str,
    top_k: int = 5,
    db: Session = Depends(get_db)
):
    try:
        results = evidence_service.search_evidence(query, top_k)
        return {
            "query": query,
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/evidence/validate")
async def validate_finding(
    finding_text: str,
    topic: str = "",
    db: Session = Depends(get_db)
):
    try:
        result = evidence_service.validate_finding_with_evidence(finding_text, topic)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))