import logging
from contextlib import asynccontextmanager
from datetime import datetime
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.routes.api import router
from app.config import settings
from app.database import SessionLocal
from app.models import AnalysisRun

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup recovery: any AnalysisRun left in 'running' status is a zombie —
    the background pipeline thread died with the previous process, and the
    in-memory progress events are gone. Mark them as 'failed' so the
    frontend doesn't show them stuck at 0% forever.
    """
    db: Session = SessionLocal()
    try:
        zombies = db.query(AnalysisRun).filter(AnalysisRun.status == "running").all()
        if zombies:
            for z in zombies:
                z.status = "failed"
                z.error_message = "后端重启导致分析中断（pipeline 线程已销毁，进度事件已丢失）"
                z.completed_at = datetime.now()
                logger.warning(
                    f"Recovered zombie run id={z.id} app='{z.app_name}' "
                    f"started={z.started_at} -> marked as failed"
                )
            db.commit()
            logger.info(f"Startup recovery: marked {len(zombies)} zombie run(s) as failed.")
        else:
            logger.info("Startup recovery: no zombie runs found.")
    except Exception as e:
        logger.error(f"Startup recovery failed: {e}", exc_info=True)
    finally:
        db.close()

    yield  # app runs


app = FastAPI(
    title="App Store Review Analysis API",
    description="API for analyzing iOS App Store reviews and generating product requirements",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.get("/")
async def root():
    return {
        "message": "App Store Review Analysis API",
        "version": "1.0.0",
        "endpoints": [
            "/api/analyze - Start analysis of an app",
            "/api/runs - List analysis runs",
            "/api/runs/{run_id} - Get run details",
            "/api/runs/{run_id}/reviews - Get reviews for a run",
            "/api/runs/{run_id}/traceability - Get traceability chain",
            "/api/evidence/search - Search evidence",
            "/api/evidence/validate - Validate a finding"
        ]
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    logger.info(f"Starting API server on http://{settings.HOST}:{settings.PORT}")
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)