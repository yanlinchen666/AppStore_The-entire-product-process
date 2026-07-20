"""
One-time cleanup script: inspect and delete zombie analysis runs
(runs stuck in "running" status after backend restart).

Usage: python -m app.cleanup_zombies         # dry-run, just inspect
       python -m app.cleanup_zombies --apply  # actually delete
"""
import argparse
import logging
import sys

from app.database import SessionLocal
from app.models import (
    AnalysisRun, AnalysisTopic, AnalysisFinding,
    PRDRequirement, PRDVersion, TestCase,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def inspect(db) -> list:
    zombies = db.query(AnalysisRun).filter(AnalysisRun.status == "running").all()
    if not zombies:
        logger.info("No zombie runs found.")
        return []

    for z in zombies:
        topics = db.query(AnalysisTopic).filter(AnalysisTopic.run_id == z.id).count()
        findings = db.query(AnalysisFinding).filter(AnalysisFinding.run_id == z.id).count()
        reqs = db.query(PRDRequirement).filter(PRDRequirement.run_id == z.id).count()
        vers = db.query(PRDVersion).filter(PRDVersion.run_id == z.id).count()
        tcs = db.query(TestCase).filter(TestCase.run_id == z.id).count()
        logger.info(
            f"Zombie run id={z.id} app={z.app_name} started={z.started_at} | "
            f"topics={topics} findings={findings} requirements={reqs} versions={vers} testcases={tcs}"
        )
    return zombies


def delete_zombies(db) -> int:
    zombies = db.query(AnalysisRun).filter(AnalysisRun.status == "running").all()
    if not zombies:
        logger.info("Nothing to delete.")
        return 0

    run_ids = [z.id for z in zombies]
    logger.info(f"Deleting zombie runs: {run_ids}")

    # Delete children first (no ON DELETE CASCADE in schema)
    deleted = 0
    deleted += db.query(TestCase).filter(TestCase.run_id.in_(run_ids)).delete(synchronize_session=False)
    deleted += db.query(PRDVersion).filter(PRDVersion.run_id.in_(run_ids)).delete(synchronize_session=False)
    deleted += db.query(PRDRequirement).filter(PRDRequirement.run_id.in_(run_ids)).delete(synchronize_session=False)
    deleted += db.query(AnalysisFinding).filter(AnalysisFinding.run_id.in_(run_ids)).delete(synchronize_session=False)
    deleted += db.query(AnalysisTopic).filter(AnalysisTopic.run_id.in_(run_ids)).delete(synchronize_session=False)

    runs_deleted = db.query(AnalysisRun).filter(AnalysisRun.id.in_(run_ids)).delete(synchronize_session=False)
    db.commit()

    logger.info(f"Deleted {runs_deleted} runs and {deleted} related child records.")
    logger.info("Reviews in 'reviews' / 'cleaned_reviews' tables are preserved (tied to app_id, not run_id).")
    return runs_deleted


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Actually delete; otherwise dry-run.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.apply:
            delete_zombies(db)
        else:
            inspect(db)
            logger.info("Dry-run only. Re-run with --apply to actually delete.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
