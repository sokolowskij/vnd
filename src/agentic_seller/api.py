"""FastAPI backend for agentic seller pipeline."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .cli import main as run_cli_pipeline
from .config import load_settings

app = FastAPI(title="Agentic Seller API", version="0.1.0")

# Add CORS middleware for Streamlit access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class JobRequest(BaseModel):
    """Request to run a pipeline job."""

    data_dir: str
    mode: str = "dry_run"
    marketplaces: list[str] = ["olx", "facebook"]


class JobResponse(BaseModel):
    """Response with job details."""

    job_id: str
    status: str
    created_at: str
    data_dir: str
    mode: str


class JobResult(BaseModel):
    """Result of a completed job."""

    job_id: str
    status: str
    created_at: str
    completed_at: Optional[str] = None
    data_dir: str
    mode: str
    result_path: Optional[str] = None


def get_jobs_dir() -> Path:
    """Get or create jobs directory."""
    jobs_dir = Path("/app/data/jobs") if Path("/app").exists() else Path("./data/jobs")
    jobs_dir.mkdir(parents=True, exist_ok=True)
    return jobs_dir


def get_job_path(job_id: str) -> Path:
    """Get path to job metadata file."""
    return get_jobs_dir() / f"{job_id}.json"


def create_job_metadata(
    job_id: str, data_dir: str, mode: str, marketplaces: list[str]
) -> dict:
    """Create job metadata."""
    return {
        "job_id": job_id,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "completed_at": None,
        "data_dir": data_dir,
        "mode": mode,
        "marketplaces": marketplaces,
        "result_path": None,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.post("/jobs", response_model=JobResponse)
async def submit_job(request: JobRequest):
    """Submit a new pipeline job."""
    job_id = str(uuid.uuid4())
    metadata = create_job_metadata(job_id, request.data_dir, request.mode, request.marketplaces)

    job_path = get_job_path(job_id)
    job_path.write_text(json.dumps(metadata, indent=2))

    # In a production setup, you'd queue this and process asynchronously
    # For now, we just return the job info
    return JobResponse(
        job_id=job_id,
        status="pending",
        created_at=metadata["created_at"],
        data_dir=request.data_dir,
        mode=request.mode,
    )


@app.get("/jobs/{job_id}", response_model=JobResult)
async def get_job(job_id: str):
    """Get job status and results."""
    job_path = get_job_path(job_id)

    if not job_path.exists():
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    metadata = json.loads(job_path.read_text())
    return JobResult(**metadata)


@app.get("/jobs")
async def list_jobs():
    """List all jobs."""
    jobs_dir = get_jobs_dir()
    jobs = []

    for job_file in sorted(jobs_dir.glob("*.json"), reverse=True):
        metadata = json.loads(job_file.read_text())
        jobs.append(metadata)

    return {"jobs": jobs, "total": len(jobs)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
