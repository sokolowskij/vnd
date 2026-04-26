"""FastAPI backend for the Agentic Seller review portal."""

from __future__ import annotations

import base64
import hashlib
import json
import re
import secrets
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

app = FastAPI(title="Agentic Seller Review API", version="0.2.0")

ALLOWED_UPLOAD_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".txt", ".md", ".docx"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AuthRequest(BaseModel):
    username: str
    password: str


class UserCreateRequest(AuthRequest):
    role: str = "user"


class ListingUpdate(BaseModel):
    title: str
    description: str
    price: float
    currency: str = "PLN"
    category: str
    condition: str
    attributes: dict[str, Any] = Field(default_factory=dict)
    cover_image: str | None = None


class UploadResponse(BaseModel):
    product_id: str
    product_dir: str
    saved_files: list[str]


def data_root() -> Path:
    root = Path("/app/data") if Path("/app").exists() else Path("./data")
    root.mkdir(parents=True, exist_ok=True)
    return root


def products_dir() -> Path:
    path = data_root() / "products"
    path.mkdir(parents=True, exist_ok=True)
    return path


def ready_dir() -> Path:
    path = data_root() / "ready_to_publish"
    path.mkdir(parents=True, exist_ok=True)
    return path


def auth_dir() -> Path:
    path = data_root() / "auth"
    path.mkdir(parents=True, exist_ok=True)
    return path


def users_path() -> Path:
    return auth_dir() / "users.json"


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", "", value).strip().strip(".")
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    return cleaned[:100]


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_users() -> dict[str, dict[str, str]]:
    return _read_json(users_path(), {})


def _save_users(users: dict[str, dict[str, str]]) -> None:
    _write_json(users_path(), users)


def _password_hash(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 150_000)
    return f"{salt}${base64.b64encode(digest).decode('ascii')}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt, expected = stored.split("$", 1)
    except ValueError:
        return False
    return secrets.compare_digest(_password_hash(password, salt).split("$", 1)[1], expected)


def _product_path(product_id: str, include_ready: bool = True) -> Path:
    safe_id = _safe_name(product_id)
    candidates = [products_dir() / safe_id]
    if include_ready:
        candidates.append(ready_dir() / safe_id)
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    raise HTTPException(status_code=404, detail=f"Product {product_id} not found")


def _product_status(product_dir: Path) -> str:
    if product_dir.parent == ready_dir():
        return "ready_to_publish"
    status = _read_json(product_dir / "review_status.json", {})
    current = status.get("status")
    if current == "awaiting_generation" and (product_dir / "listing_plan.json").exists():
        return "awaiting_review"
    return current or "awaiting_review"


def _list_product_files(product_dir: Path) -> list[str]:
    return [p.name for p in sorted(product_dir.iterdir()) if p.is_file()]


def _list_images(product_dir: Path) -> list[str]:
    return [p.name for p in sorted(product_dir.iterdir()) if p.is_file() and p.suffix.lower() in IMAGE_EXTS]


def _listing_for(product_dir: Path) -> dict[str, Any] | None:
    listing_path = product_dir / "listing_plan.json"
    if not listing_path.exists():
        return None
    return _read_json(listing_path, None)


def _status_for(product_dir: Path) -> dict[str, Any]:
    return _read_json(product_dir / "review_status.json", {})


def _write_status(product_dir: Path, updates: dict[str, Any]) -> None:
    status = _status_for(product_dir)
    status.update(updates)
    status["updated_at"] = datetime.utcnow().isoformat()
    _write_json(product_dir / "review_status.json", status)


def _product_summary(product_dir: Path) -> dict[str, Any]:
    listing = _listing_for(product_dir)
    status = _product_status(product_dir)
    status_meta = _status_for(product_dir)
    fallback_title = product_dir.name
    return {
        "product_id": product_dir.name,
        "status": status,
        "product_dir": str(product_dir),
        "files": _list_product_files(product_dir),
        "images": _list_images(product_dir),
        "listing": listing,
        "title": (listing or {}).get("title", fallback_title),
        "price": (listing or {}).get("price"),
        "category": (listing or {}).get("category"),
        "condition": (listing or {}).get("condition"),
        "added_by": status_meta.get("added_by"),
        "uploaded_at": status_meta.get("uploaded_at"),
        "approved_by": status_meta.get("approved_by"),
        "approved_at": status_meta.get("approved_at"),
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/auth/status")
async def auth_status():
    users = _load_users()
    return {"configured": bool(users)}


@app.post("/auth/setup")
async def setup_first_user(request: AuthRequest):
    users = _load_users()
    if users:
        raise HTTPException(status_code=409, detail="Authentication is already configured")
    username = _safe_name(request.username)
    if len(request.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters")
    users[username] = {
        "password_hash": _password_hash(request.password),
        "role": "boss",
        "created_at": datetime.utcnow().isoformat(),
    }
    _save_users(users)
    return {"username": username, "role": "boss"}


@app.post("/auth/login")
async def login(request: AuthRequest):
    users = _load_users()
    user = users.get(request.username)
    if not user or not _verify_password(request.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"username": request.username, "role": user.get("role", "user")}


@app.post("/auth/users")
async def create_user(request: UserCreateRequest):
    users = _load_users()
    username = _safe_name(request.username)
    if username in users:
        raise HTTPException(status_code=409, detail="User already exists")
    role = request.role if request.role in {"user", "boss"} else "user"
    if len(request.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters")
    users[username] = {
        "password_hash": _password_hash(request.password),
        "role": role,
        "created_at": datetime.utcnow().isoformat(),
    }
    _save_users(users)
    return {"username": username, "role": role}


@app.post("/uploads/products", response_model=UploadResponse)
async def upload_product(
    product_name: str = Form(...),
    notes: str = Form(""),
    added_by: str = Form("unknown"),
    files: list[UploadFile] = File(...),
):
    if not files:
        raise HTTPException(status_code=400, detail="Upload at least one file")

    product_id = _safe_name(product_name)
    product_dir = products_dir() / product_id
    product_dir.mkdir(parents=True, exist_ok=True)

    saved_files: list[str] = []
    for uploaded in files:
        filename = _safe_name(Path(uploaded.filename or "upload").name)
        suffix = Path(filename).suffix.lower()
        if suffix not in ALLOWED_UPLOAD_EXTS:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {filename}")

        destination = product_dir / filename
        destination.write_bytes(await uploaded.read())
        saved_files.append(filename)

    if notes.strip():
        (product_dir / "notes.txt").write_text(notes.strip(), encoding="utf-8")
        saved_files.append("notes.txt")

    _write_status(
        product_dir,
        {
            "status": "awaiting_generation",
            "added_by": _safe_name(added_by) if added_by.strip() else "unknown",
            "uploaded_at": datetime.utcnow().isoformat(),
        },
    )
    return UploadResponse(product_id=product_id, product_dir=str(product_dir), saved_files=saved_files)


@app.get("/products")
async def list_products(status: str | None = None):
    product_dirs = [p for p in products_dir().iterdir() if p.is_dir()]
    product_dirs += [p for p in ready_dir().iterdir() if p.is_dir()]
    products = [_product_summary(path) for path in sorted(product_dirs, key=lambda p: p.name.lower())]
    if status:
        products = [product for product in products if product["status"] == status]
    return {
        "products": products,
        "products_dir": str(products_dir()),
        "ready_dir": str(ready_dir()),
    }


@app.get("/products/{product_id}")
async def get_product(product_id: str):
    return _product_summary(_product_path(product_id))


@app.get("/products/{product_id}/files/{filename}")
async def get_product_file(product_id: str, filename: str):
    product_dir = _product_path(product_id)
    safe_filename = _safe_name(filename)
    file_path = product_dir / safe_filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)


@app.put("/products/{product_id}/listing")
async def update_listing(product_id: str, update: ListingUpdate):
    product_dir = _product_path(product_id)
    current = _listing_for(product_dir) or {}
    images = current.get("image_paths") or [str(product_dir / name) for name in _list_images(product_dir)]
    cover_image = update.cover_image or current.get("cover_image") or (images[0] if images else None)

    listing = {
        "product_id": product_dir.name,
        "title": update.title,
        "description": update.description,
        "price": update.price,
        "currency": update.currency,
        "category": update.category,
        "condition": update.condition,
        "attributes": update.attributes,
        "image_paths": images,
        "cover_image": cover_image,
    }
    _write_json(product_dir / "listing_plan.json", listing)
    _write_status(product_dir, {"status": "awaiting_review"})
    return _product_summary(product_dir)


@app.post("/products/{product_id}/approve")
async def approve_product(product_id: str, username: str = Form("boss")):
    product_dir = _product_path(product_id, include_ready=False)
    if not (product_dir / "listing_plan.json").exists():
        raise HTTPException(status_code=400, detail="Product has no listing plan to approve")

    destination = ready_dir() / product_dir.name
    if destination.exists():
        destination = ready_dir() / f"{product_dir.name}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    _write_status(
        product_dir,
        {
            "status": "ready_to_publish",
            "approved_by": username,
            "approved_at": datetime.utcnow().isoformat(),
        },
    )
    shutil.move(str(product_dir), str(destination))
    return _product_summary(destination)
    
