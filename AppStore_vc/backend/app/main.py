import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.api import router
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="App Store Review Analysis API",
    description="API for analyzing iOS App Store reviews and generating product requirements",
    version="1.0.0"
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