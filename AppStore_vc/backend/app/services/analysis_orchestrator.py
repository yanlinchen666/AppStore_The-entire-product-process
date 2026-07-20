"""
Async analysis orchestrator.
Runs the full pipeline in a background thread while emitting progress events.

IMPORTANT — DB session lifecycle:
MySQL's wait_timeout is 120s on this machine. A SQLAlchemy session held idle
across a long LLM/HTTP call will have its underlying connection closed by the
server, and the next DB operation raises
`mysql.connector.errors.OperationalError: MySQL Connection not available`.

To avoid this, `_run_pipeline` does NOT hold a single session for the whole
pipeline. Instead, each stage that needs the DB opens a short-lived session
via `with SessionLocal() as db:` and closes it before any long-running work.
Data passed between stages is plain dicts (never ORM instances), so it is
safe to use after the session that produced it has been closed.
"""
import logging
import threading
from typing import Optional, List, Dict, Any
from app.database import SessionLocal
from app.services.collector import (
    collect_reviews, save_reviews,
    extract_app_id_from_url, extract_app_name_from_url,
)
from app.services.cleaner import clean_reviews
from app.services.analysis_service import analysis_service
from app.services.prd_service import prd_service
from app.services.testcase_service import testcase_service
from app.services.evidence_service import evidence_service
from app.services.progress_service import progress_service
from app.config import settings
from app.models import AnalysisRun

logger = logging.getLogger(__name__)


class AnalysisOrchestrator:
    def __init__(self):
        pass

    def start_async_analysis(
        self,
        app_url: str,
        analysis_goal: str = "",
        max_reviews: int = 200,
        run_id: Optional[int] = None,
    ) -> int:
        """Launch a background thread that runs the analysis pipeline. Returns the run_id."""
        thread = threading.Thread(
            target=self._run_pipeline,
            args=(app_url, analysis_goal, max_reviews, run_id),
            daemon=True,
        )
        thread.start()
        return run_id

    def _run_pipeline(self, app_url: str, analysis_goal: str, max_reviews: int, run_id: int):
        app_id = extract_app_id_from_url(app_url)
        app_name = extract_app_name_from_url(app_url) or "Unknown App"

        if not app_id:
            progress_service.emit(run_id, "collection", "failed",
                                  f"Invalid App Store URL: {app_url}", 0.0)
            return

        # ---------------------------------------------------------------
        # Stage 1: Collection
        # ---------------------------------------------------------------
        progress_service.emit(run_id, "collection", "started",
                              f"Fetching up to {max_reviews} reviews from App Store...", 0.05)
        saved_count = 0
        try:
            # 1a: HTTP RSS fetch — no DB session held during network I/O.
            reviews_data = collect_reviews(
                app_id, app_name, settings.APP_STORE_COUNTRY, max_reviews
            )
            # 1b: short DB session for the save + run update.
            with SessionLocal() as db:
                saved_count = save_reviews(db, reviews_data)
                run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
                if run:
                    run.app_id = app_id
                    run.app_name = app_name
                    run.status = "running"
                    db.commit()
            progress_service.emit(run_id, "collection", "completed",
                                  f"Collected {saved_count} new reviews",
                                  0.15, {"reviews_collected": saved_count, "app_id": app_id, "app_name": app_name})
        except Exception as e:
            progress_service.emit(run_id, "collection", "failed",
                                  f"Collection failed: {str(e)}", 0.15)
            self._mark_run_failed(run_id, str(e))
            return

        if saved_count == 0:
            progress_service.emit(run_id, "collection", "failed",
                                  "No new reviews collected (already in database or no reviews available)", 0.15)

        # ---------------------------------------------------------------
        # Stage 2: Cleaning (short DB session)
        # ---------------------------------------------------------------
        progress_service.emit(run_id, "cleaning", "started",
                              "Cleaning and deduplicating reviews...", 0.20)
        try:
            with SessionLocal() as db:
                cleaned_count = clean_reviews(db, app_id)
            progress_service.emit(run_id, "cleaning", "completed",
                                  f"Cleaned {cleaned_count} reviews",
                                  0.30, {"reviews_cleaned": cleaned_count})
        except Exception as e:
            progress_service.emit(run_id, "cleaning", "failed", str(e), 0.30)
            self._mark_run_failed(run_id, str(e))
            return

        # ---------------------------------------------------------------
        # Stage 3: Vector index (evidence_service manages its own short sessions)
        # ---------------------------------------------------------------
        progress_service.emit(run_id, "vector_index", "started",
                              "Building vector index for evidence retrieval...", 0.35)
        try:
            evidence_service.build_vector_index(app_id)
            progress_service.emit(run_id, "vector_index", "completed",
                                  "Vector index built", 0.40)
        except Exception as e:
            progress_service.emit(run_id, "vector_index", "failed", str(e), 0.40)
            self._mark_run_failed(run_id, str(e))
            return

        # ---------------------------------------------------------------
        # Stage 4: Topic extraction
        # Step 4a: short DB session to load cleaned reviews into plain dicts.
        # Step 4b: long LLM call — NO DB session held.
        # ---------------------------------------------------------------
        progress_service.emit(run_id, "topic_extraction", "started",
                              "Extracting topics via LLM...", 0.45)
        reviews: List[Dict[str, Any]] = []
        topics: List[Dict[str, Any]] = []
        try:
            with SessionLocal() as db:
                reviews = analysis_service.get_cleaned_reviews(db, app_id)
            # reviews is List[Dict]; safe to use after session closed.

            if not reviews:
                progress_service.emit(run_id, "topic_extraction", "failed",
                                      "No cleaned reviews available for analysis", 0.45)
                self._mark_run_failed(run_id, "No cleaned reviews")
                return

            topics = analysis_service.extract_topics(reviews, analysis_goal)  # LLM call
            progress_service.emit(run_id, "topic_extraction", "completed",
                                  f"Extracted {len(topics)} topics",
                                  0.55, {"topics_count": len(topics), "topics": topics})
        except Exception as e:
            progress_service.emit(run_id, "topic_extraction", "failed", str(e), 0.55)
            self._mark_run_failed(run_id, str(e))
            return

        # ---------------------------------------------------------------
        # Stage 5: Finding generation (long LLM loop — no DB session held)
        # ---------------------------------------------------------------
        progress_service.emit(run_id, "finding_generation", "started",
                              "Generating findings via LLM...", 0.60)
        findings: List[Dict[str, Any]] = []
        try:
            findings = analysis_service.generate_findings(run_id, topics, reviews)
            progress_service.emit(run_id, "finding_generation", "completed",
                                  f"Generated {len(findings)} findings",
                                  0.65, {"findings_count": len(findings)})
        except Exception as e:
            progress_service.emit(run_id, "finding_generation", "failed", str(e), 0.65)
            self._mark_run_failed(run_id, str(e))
            return

        # ---------------------------------------------------------------
        # Stage 6: Evidence validation (vector search + embeddings — no SQL DB)
        # ---------------------------------------------------------------
        progress_service.emit(run_id, "evidence_validation", "started",
                              "Validating findings with vector search...", 0.70)
        validated_findings: List[Dict[str, Any]] = []
        try:
            validated_findings = analysis_service.validate_findings(findings)
            assumption_count = sum(1 for f in validated_findings if f.get('is_assumption'))
            progress_service.emit(run_id, "evidence_validation", "completed",
                                  f"Validated {len(validated_findings)} findings ({assumption_count} marked as assumptions)",
                                  0.80, {
                                      "validated_count": len(validated_findings),
                                      "assumption_count": assumption_count
                                  })
        except Exception as e:
            progress_service.emit(run_id, "evidence_validation", "failed", str(e), 0.80)
            self._mark_run_failed(run_id, str(e))
            return

        # ---------------------------------------------------------------
        # Persist topics + findings (single short session, because
        # save_topics_and_findings uses db.flush() to link findings to
        # topics within one transaction).
        # NOTE: We do NOT call complete_analysis() here — that would mark
        # the run as "completed" before PRD and test case stages have run.
        # The run is marked completed only in Stage 9 after ALL stages finish.
        # ---------------------------------------------------------------
        try:
            with SessionLocal() as db:
                analysis_service.save_topics_and_findings(db, run_id, topics, validated_findings)
        except Exception as e:
            progress_service.emit(run_id, "traceability", "failed",
                                  f"Failed to persist results: {str(e)}", 1.0)
            self._mark_run_failed(run_id, str(e))
            return

        # ---------------------------------------------------------------
        # Stage 7: PRD generation
        # Phase 7a: short DB session → load findings (plain dicts).
        # Phase 7b: LLM generation → NO DB session held.
        # Phase 7c: short DB session → persist requirements + versions.
        # ---------------------------------------------------------------
        progress_service.emit(run_id, "prd_generation", "started",
                              "Generating product requirements via LLM...", 0.85)
        try:
            prd_result: Dict[str, Any] = {}
            with SessionLocal() as db_read:
                prd_findings = prd_service.get_findings_for_prd(db_read, run_id)

            if not prd_findings:
                progress_service.emit(run_id, "prd_generation", "failed",
                                      "No findings available for PRD generation", 0.90)
                # Non-fatal, continue to test cases (there won't be any either).
            else:
                # LLM call — no DB session held.
                prd_requirements = prd_service.generate_requirements(prd_findings)
                prd_versions = prd_service.plan_versions(prd_requirements)

                # Persist with a fresh short session.
                with SessionLocal() as db_write:
                    prd_service.save_prd(db_write, run_id, prd_requirements, prd_versions)

                prd_result = {
                    "status": "completed",
                    "requirements_count": len(prd_requirements),
                    "versions_count": len(prd_versions),
                    "versions": prd_versions,
                }

            progress_service.emit(run_id, "prd_generation", "completed",
                                  f"Generated {prd_result.get('requirements_count', 0)} requirements",
                                  0.90, prd_result)
        except Exception as e:
            progress_service.emit(run_id, "prd_generation", "failed", str(e), 0.90)
            logger.exception(f"PRD generation failed for run {run_id}")
            # Non-fatal, continue to test cases

        # ---------------------------------------------------------------
        # Stage 8: Test case generation
        # Phase 8a: short DB session → load requirements (plain dicts).
        # Phase 8b: LLM generation → NO DB session held.
        # Phase 8c: short DB session → persist test cases.
        # ---------------------------------------------------------------
        progress_service.emit(run_id, "testcase_generation", "started",
                              "Generating test cases via LLM...", 0.93)
        try:
            testcase_result: Dict[str, Any] = {}
            with SessionLocal() as db_read:
                tc_requirements = testcase_service.get_requirements(db_read, run_id)

            if not tc_requirements:
                progress_service.emit(run_id, "testcase_generation", "failed",
                                      "No requirements available for test case generation", 0.98)
            else:
                # LLM call — no DB session held.
                test_cases = testcase_service.generate_test_cases(tc_requirements)

                # Persist with a fresh short session.
                with SessionLocal() as db_write:
                    testcase_service.save_test_cases(db_write, run_id, test_cases)

                testcase_result = {
                    "status": "completed",
                    "test_cases_count": len(test_cases),
                    "requirements_count": len(tc_requirements),
                }

            progress_service.emit(run_id, "testcase_generation", "completed",
                                  f"Generated {testcase_result.get('test_cases_count', 0)} test cases",
                                  0.98, testcase_result)
        except Exception as e:
            progress_service.emit(run_id, "testcase_generation", "failed", str(e), 0.98)
            logger.exception(f"Test case generation failed for run {run_id}")
            # Non-fatal

        # ---------------------------------------------------------------
        # Stage 9: Done — NOW it's safe to mark the run as completed,
        # because ALL stages (including PRD and test cases) have finished.
        # ---------------------------------------------------------------
        progress_service.emit(run_id, "traceability", "completed",
                              "Analysis pipeline completed", 1.0,
                              {"run_id": run_id, "status": "completed"})
        try:
            with SessionLocal() as db:
                analysis_service.complete_analysis(db, run_id, len(reviews), len(reviews))
        except Exception as e:
            logger.error(f"Failed to mark run {run_id} as completed: {str(e)}")

    def _mark_run_failed(self, run_id: int, error: str):
        """Open a fresh short session to mark the run as failed.
        We must not reuse the caller's session — by the time this is called,
        that session's connection may already be dead (which is often what
        triggered the failure)."""
        try:
            with SessionLocal() as db:
                run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
                if run:
                    run.status = "failed"
                    run.error_message = error
                    db.commit()
        except Exception as e:
            logger.error(f"Failed to mark run {run_id} as failed: {str(e)}")


analysis_orchestrator = AnalysisOrchestrator()
