"""FastAPI backend for agentic seller pipeline."""

from __future__ import annotations

import json
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import load_settings
from .orchestrator import run_pipeline

app = FastAPI(title="Agentic Seller API", version="0.1.0")
executor = ThreadPoolExecutor(max_workers=1)

ALLOWED_UPLOAD_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".txt", ".md", ".docx"}

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
    error: Optional[str] = None


class UploadResponse(BaseModel):
    """Response after uploading product files."""

    product_id: str
    product_dir: str
    saved_files: list[str]


def get_jobs_dir() -> Path:
    """Get or create jobs directory."""
    jobs_dir = Path("/app/data/jobs") if Path("/app").exists() else Path("./data/jobs")
    jobs_dir.mkdir(parents=True, exist_ok=True)
    return jobs_dir


def get_products_dir() -> Path:
    """Get or create products directory."""
    products_dir = Path("/app/data/products") if Path("/app").exists() else Path("./data/products")
    products_dir.mkdir(parents=True, exist_ok=True)
    return products_dir


def get_job_path(job_id: str) -> Path:
    """Get path to job metadata file."""
    return get_jobs_dir() / f"{job_id}.json"


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", "", value).strip().strip(".")
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    return cleaned[:100]


def _save_job_metadata(metadata: dict) -> None:
    get_job_path(metadata["job_id"]).write_text(json.dumps(metadata, indent=2))


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
        "error": None,
    }


def _run_job(job_id: str) -> None:
    job_path = get_job_path(job_id)
    metadata = json.loads(job_path.read_text())
    metadata["status"] = "running"
    _save_job_metadata(metadata)

    try:
        settings = load_settings()
        run_pipeline(
            Path(metadata["data_dir"]),
            settings,
            mode=metadata["mode"],
            selected_marketplaces=metadata["marketplaces"],
        )
    except Exception as exc:
        metadata["status"] = "failed"
        metadata["completed_at"] = datetime.utcnow().isoformat()
        metadata["error"] = str(exc)
    else:
        metadata["status"] = "completed"
        metadata["completed_at"] = datetime.utcnow().isoformat()
        metadata["result_path"] = metadata["data_dir"]

    _save_job_metadata(metadata)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.post("/jobs", response_model=JobResponse)
async def submit_job(request: JobRequest):
    """Submit a new pipeline job."""
    job_id = str(uuid.uuid4())
    metadata = create_job_metadata(job_id, request.data_dir, request.mode, request.marketplaces)

    _save_job_metadata(metadata)
    executor.submit(_run_job, job_id)

    return JobResponse(
        job_id=job_id,
        status="pending",
        created_at=metadata["created_at"],
        data_dir=request.data_dir,
        mode=request.mode,
    )


@app.post("/uploads/products", response_model=UploadResponse)
async def upload_product(
    product_name: str = Form(...),
    notes: str = Form(""),
    files: list[UploadFile] = File(...),
):
    """Upload product files into the backend's persistent products directory."""
    if not files:
        raise HTTPException(status_code=400, detail="Upload at least one file")

    product_id = _safe_name(product_name)
    product_dir = get_products_dir() / product_id
    product_dir.mkdir(parents=True, exist_ok=True)

    saved_files: list[str] = []
    for uploaded in files:
        filename = _safe_name(Path(uploaded.filename or "upload").name)
        suffix = Path(filename).suffix.lower()
        if suffix not in ALLOWED_UPLOAD_EXTS:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {filename}")

        destination = product_dir / filename
        content = await uploaded.read()
        destination.write_bytes(content)
        saved_files.append(filename)

    if notes.strip():
        (product_dir / "notes.txt").write_text(notes.strip(), encoding="utf-8")
        saved_files.append("notes.txt")

    return UploadResponse(
        product_id=product_id,
        product_dir=str(product_dir),
        saved_files=saved_files,
    )


@app.get("/products")
async def list_products():
    """List uploaded products available to the pipeline."""
    products_dir = get_products_dir()
    products = []

    for product_dir in sorted([p for p in products_dir.iterdir() if p.is_dir()]):
        files = [p.name for p in sorted(product_dir.iterdir()) if p.is_file()]
        products.append(
            {
                "product_id": product_dir.name,
                "product_dir": str(product_dir),
                "files": files,
            }
        )

    return {"products": products, "data_dir": str(products_dir)}


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
