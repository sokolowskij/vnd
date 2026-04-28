"""FastAPI backend for the Agentic Seller review portal."""

from __future__ import annotations

import base64
import hashlib
import asyncio
import json
import os
import re
import secrets
import shutil
import smtplib
import tempfile
import zipfile
from contextlib import suppress
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from PIL import Image, ImageOps
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

app = FastAPI(title="Agentic Seller Review API", version="0.2.0")

ALLOWED_UPLOAD_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".txt", ".md", ".docx"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
SHOP_OPTIONS = {"KC", "FW", "KEN", "MAG"}
PACKAGE_SIZE_OPTIONS = {"small", "medium", "large"}
DEFAULT_MARKETPLACES = ["facebook", "olx", "vinted"]
PENDING_RETENTION_DAYS = int(os.getenv("PENDING_RETENTION_DAYS", "90"))
READY_RETENTION_DAYS = int(os.getenv("READY_RETENTION_DAYS", "30"))
RETENTION_CHECK_HOURS = int(os.getenv("RETENTION_CHECK_HOURS", "24"))
DAILY_BACKUP_ENABLED = os.getenv("DAILY_BACKUP_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
DAILY_BACKUP_HOUR_UTC = int(os.getenv("DAILY_BACKUP_HOUR_UTC", "3"))
MAX_BACKUP_EMAIL_MB = int(os.getenv("MAX_BACKUP_EMAIL_MB", "20"))
SESSION_TTL_DAYS = int(os.getenv("SESSION_TTL_DAYS", "30"))
ADMIN_BACKUP_EMAIL = os.getenv("ADMIN_BACKUP_EMAIL", "").strip()
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", SMTP_USERNAME or ADMIN_BACKUP_EMAIL).strip()
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").strip().lower() in {"1", "true", "yes", "on"}
_retention_task: asyncio.Task | None = None
_backup_task: asyncio.Task | None = None

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


class ImageRotateRequest(BaseModel):
    degrees: int
    filename: str | None = None


class ProductMetadataUpdate(BaseModel):
    shop: str | None = None
    package_size: str | None = None
    actual_store_shelf_price: float | None = None
    brand: str | None = None
    maker: str | None = None
    model: str | None = None
    year: str | None = None
    material: str | None = None
    color: str | None = None
    dimensions: str | None = None
    llm_notes: str | None = None


class MarketplaceStatusUpdate(BaseModel):
    listed: bool = True
    url: str | None = None
    notes: str | None = None


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


def sessions_path() -> Path:
    return auth_dir() / "sessions.json"


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


def backup_status_path() -> Path:
    return data_root() / "backup_status.json"


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    with suppress(ValueError):
        return datetime.fromisoformat(value)
    return None


def _load_users() -> dict[str, dict[str, str]]:
    return _read_json(users_path(), {})


def _save_users(users: dict[str, dict[str, str]]) -> None:
    _write_json(users_path(), users)


def _load_sessions() -> dict[str, dict[str, str]]:
    sessions = _read_json(sessions_path(), {})
    return sessions if isinstance(sessions, dict) else {}


def _save_sessions(sessions: dict[str, dict[str, str]]) -> None:
    _write_json(sessions_path(), sessions)


def _session_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _new_session(username: str, role: str) -> dict[str, str]:
    token = secrets.token_urlsafe(32)
    now = datetime.utcnow()
    expires_at = now + timedelta(days=SESSION_TTL_DAYS)
    sessions = _load_sessions()
    sessions[_session_hash(token)] = {
        "username": username,
        "role": role,
        "created_at": now.isoformat(),
        "last_seen_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
    }
    _prune_sessions(sessions, now)
    _save_sessions(sessions)
    return {
        "username": username,
        "role": role,
        "session_token": token,
        "expires_at": expires_at.isoformat(),
    }


def _prune_sessions(sessions: dict[str, dict[str, str]], now: datetime | None = None) -> None:
    now = now or datetime.utcnow()
    expired = [
        token_hash
        for token_hash, session in sessions.items()
        if (_parse_datetime(session.get("expires_at")) or now) <= now
    ]
    for token_hash in expired:
        sessions.pop(token_hash, None)


def _bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing session token")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="Invalid session token")
    return token.strip()


def _current_session(authorization: str | None = Header(default=None)) -> tuple[str, dict[str, str]]:
    token = _bearer_token(authorization)
    token_hash = _session_hash(token)
    sessions = _load_sessions()
    now = datetime.utcnow()
    _prune_sessions(sessions, now)
    session = sessions.get(token_hash)
    if not session:
        _save_sessions(sessions)
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    expires_at = _parse_datetime(session.get("expires_at"))
    if not expires_at or expires_at <= now:
        sessions.pop(token_hash, None)
        _save_sessions(sessions)
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    session["last_seen_at"] = now.isoformat()
    _save_sessions(sessions)
    return token_hash, session


def current_user(session_data: tuple[str, dict[str, str]] = Depends(_current_session)) -> dict[str, str]:
    _, session = session_data
    return {"username": session["username"], "role": session.get("role", "user")}


def boss_user(user: dict[str, str] = Depends(current_user)) -> dict[str, str]:
    if user.get("role") != "boss":
        raise HTTPException(status_code=403, detail="Boss access required")
    return user


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


def _product_file_path(product_id: str, filename: str, require_image: bool = False) -> Path:
    product_dir = _product_path(product_id)
    safe_filename = _safe_name(filename)
    file_path = product_dir / safe_filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    if require_image and file_path.suffix.lower() not in IMAGE_EXTS:
        raise HTTPException(status_code=400, detail="File is not a supported image")
    return file_path


def _rotate_image_file(file_path: Path, degrees: int) -> dict[str, Any]:
    if degrees not in {-270, -180, -90, 90, 180, 270}:
        raise HTTPException(status_code=400, detail="Rotation must be 90, 180, or 270 degrees")

    product_dir = file_path.parent
    rotated_at = datetime.utcnow().isoformat()
    try:
        with Image.open(file_path) as image:
            image_format = image.format
            normalized = ImageOps.exif_transpose(image)
            rotated = normalized.rotate(-degrees, expand=True)
            if file_path.suffix.lower() in {".jpg", ".jpeg"} and rotated.mode in {"RGBA", "LA", "P"}:
                rotated = rotated.convert("RGB")
            rotated.load()
        rotated.save(file_path, format=image_format, quality=95)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not rotate image: {exc}") from exc

    status = _status_for(product_dir)
    rotations = status.get("image_rotations") if isinstance(status.get("image_rotations"), dict) else {}
    current = rotations.get(file_path.name) if isinstance(rotations.get(file_path.name), dict) else {}
    previous_degrees = int(current.get("degrees", 0) or 0)
    effective_degrees = (previous_degrees + degrees) % 360
    rotations[file_path.name] = {
        "degrees": effective_degrees,
        "last_delta_degrees": degrees,
        "updated_at": rotated_at,
        "count": int(current.get("count", 0) or 0) + 1,
    }

    _write_status(
        product_dir,
        {
            "last_image_rotation_at": rotated_at,
            "image_rotations": rotations,
        },
    )
    return _product_summary(product_dir)


def _listing_for(product_dir: Path) -> dict[str, Any] | None:
    listing_path = product_dir / "listing_plan.json"
    if not listing_path.exists():
        return None
    return _read_json(listing_path, None)


def _path_exists(path_value: str) -> bool:
    path = Path(path_value)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.exists()


def _current_image_paths(product_dir: Path) -> list[str]:
    return [str(product_dir / name) for name in _list_images(product_dir)]


def _repair_listing_image_paths(product_dir: Path) -> None:
    listing = _listing_for(product_dir)
    if not listing:
        return

    current_images = _current_image_paths(product_dir)
    if not current_images:
        return

    listing_images = listing.get("image_paths") or []
    if listing_images and all(_path_exists(str(path)) for path in listing_images):
        return

    cover_name = Path(str(listing.get("cover_image") or "")).name
    current_by_name = {Path(path).name: path for path in current_images}
    listing["image_paths"] = current_images
    listing["cover_image"] = current_by_name.get(cover_name, current_images[0])
    _write_json(product_dir / "listing_plan.json", listing)


def _status_for(product_dir: Path) -> dict[str, Any]:
    return _read_json(product_dir / "review_status.json", {})


def _write_status(product_dir: Path, updates: dict[str, Any]) -> None:
    status = _status_for(product_dir)
    status.update(updates)
    status["updated_at"] = datetime.utcnow().isoformat()
    _write_json(product_dir / "review_status.json", status)


def _marketplace_key(value: str) -> str:
    key = re.sub(r"[^a-z0-9._ -]+", "", value.strip().lower())
    key = re.sub(r"\s+", "_", key)
    if not key:
        raise HTTPException(status_code=400, detail="Marketplace name cannot be empty")
    return key[:50]


def _marketplace_label(key: str) -> str:
    known = {"facebook": "Facebook", "olx": "OLX", "vinted": "Vinted"}
    return known.get(key, key.replace("_", " ").title())


def _read_posted_marketplaces(product_dir: Path) -> dict[str, dict[str, Any]]:
    posted: dict[str, dict[str, Any]] = {}
    result_path = product_dir / "post_results.json"
    if not result_path.exists():
        return posted
    results = _read_json(result_path, [])
    if not isinstance(results, list):
        return posted
    for result in results:
        if not isinstance(result, dict) or not result.get("success"):
            continue
        marketplace = result.get("marketplace")
        if not marketplace:
            continue
        key = _marketplace_key(str(marketplace))
        posted[key] = {
            "listed": True,
            "url": result.get("url"),
            "notes": result.get("message"),
            "source": "post_results",
        }
    return posted


def _marketplaces_for(product_dir: Path) -> dict[str, dict[str, Any]]:
    status = _status_for(product_dir)
    stored = status.get("marketplaces") if isinstance(status.get("marketplaces"), dict) else {}
    marketplaces: dict[str, dict[str, Any]] = {}
    for key in DEFAULT_MARKETPLACES:
        marketplaces[key] = {"listed": False, "label": _marketplace_label(key), "url": None, "notes": None}
    for key, value in _read_posted_marketplaces(product_dir).items():
        marketplaces.setdefault(key, {"listed": False, "label": _marketplace_label(key), "url": None, "notes": None})
        marketplaces[key].update(value)
    for raw_key, raw_value in stored.items():
        key = _marketplace_key(str(raw_key))
        value = raw_value if isinstance(raw_value, dict) else {"listed": bool(raw_value)}
        marketplaces.setdefault(key, {"listed": False, "label": _marketplace_label(key), "url": None, "notes": None})
        marketplaces[key].update(
            {
                "listed": bool(value.get("listed")),
                "label": str(value.get("label") or _marketplace_label(key)),
                "url": value.get("url"),
                "notes": value.get("notes"),
                "updated_at": value.get("updated_at"),
                "source": value.get("source", "manual"),
            }
        )
    return marketplaces


def _validate_metadata(shop: str | None, package_size: str | None) -> None:
    if shop and shop not in SHOP_OPTIONS:
        raise HTTPException(status_code=400, detail=f"Shop must be one of: {', '.join(sorted(SHOP_OPTIONS))}")
    if package_size and package_size not in PACKAGE_SIZE_OPTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Package size must be one of: {', '.join(sorted(PACKAGE_SIZE_OPTIONS))}",
        )


def _metadata_updates(
    shop: str | None,
    package_size: str | None,
    actual_store_shelf_price: float | None,
    brand: str | None = None,
    maker: str | None = None,
    model: str | None = None,
    year: str | None = None,
    material: str | None = None,
    color: str | None = None,
    dimensions: str | None = None,
    llm_notes: str | None = None,
) -> dict[str, Any]:
    shop = shop or None
    package_size = package_size or None
    _validate_metadata(shop, package_size)
    return {
        "shop": shop,
        "package_size": package_size,
        "actual_store_shelf_price": actual_store_shelf_price,
        "brand": brand.strip() if brand and brand.strip() else None,
        "maker": maker.strip() if maker and maker.strip() else None,
        "model": model.strip() if model and model.strip() else None,
        "year": year.strip() if year and year.strip() else None,
        "material": material.strip() if material and material.strip() else None,
        "color": color.strip() if color and color.strip() else None,
        "dimensions": dimensions.strip() if dimensions and dimensions.strip() else None,
        "llm_notes": llm_notes.strip() if llm_notes and llm_notes.strip() else None,
    }


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
        "shop": status_meta.get("shop"),
        "package_size": status_meta.get("package_size"),
        "actual_store_shelf_price": status_meta.get("actual_store_shelf_price"),
        "brand": status_meta.get("brand"),
        "maker": status_meta.get("maker"),
        "model": status_meta.get("model"),
        "year": status_meta.get("year"),
        "material": status_meta.get("material"),
        "color": status_meta.get("color"),
        "dimensions": status_meta.get("dimensions"),
        "llm_notes": status_meta.get("llm_notes"),
        "marketplaces": _marketplaces_for(product_dir),
        "image_rotations": status_meta.get("image_rotations", {}),
    }


def _iter_product_dirs() -> list[Path]:
    dirs = [p for p in products_dir().iterdir() if p.is_dir()]
    dirs += [p for p in ready_dir().iterdir() if p.is_dir()]
    return dirs


def _retention_cutoff_for(product_dir: Path, status: str, status_meta: dict[str, Any]) -> datetime | None:
    if status == "ready_to_publish":
        base = _parse_datetime(status_meta.get("approved_at")) or _parse_datetime(status_meta.get("updated_at"))
        return base + timedelta(days=READY_RETENTION_DAYS) if base else None

    base = _parse_datetime(status_meta.get("uploaded_at")) or _parse_datetime(status_meta.get("updated_at"))
    return base + timedelta(days=PENDING_RETENTION_DAYS) if base else None


def _retention_report(delete: bool = False) -> dict[str, Any]:
    now = datetime.utcnow()
    deleted: list[dict[str, Any]] = []
    expiring: list[dict[str, Any]] = []

    for product_dir in _iter_product_dirs():
        status = _product_status(product_dir)
        status_meta = _status_for(product_dir)
        cutoff = _retention_cutoff_for(product_dir, status, status_meta)
        if cutoff is None:
            continue

        entry = {
            "product_id": product_dir.name,
            "status": status,
            "delete_after": cutoff.isoformat(),
            "product_dir": str(product_dir),
        }
        if cutoff <= now:
            if delete:
                shutil.rmtree(product_dir)
                deleted.append(entry)
            else:
                expiring.append(entry)
        else:
            expiring.append(entry)

    return {
        "policy": {
            "pending_days": PENDING_RETENTION_DAYS,
            "ready_days": READY_RETENTION_DAYS,
            "check_hours": RETENTION_CHECK_HOURS,
        },
        "deleted": deleted,
        "items": expiring,
    }


async def _retention_loop() -> None:
    while True:
        _retention_report(delete=True)
        await asyncio.sleep(RETENTION_CHECK_HOURS * 60 * 60)


def _create_zip_archive(paths: list[Path], archive_name: str) -> Path:
    fd, archive_path = tempfile.mkstemp(prefix="agentic-seller-", suffix=".zip")
    os.close(fd)
    archive = Path(archive_path)

    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for path in paths:
            if path.is_file():
                zip_file.write(path, f"{archive_name}/{path.name}")
                continue
            for file_path in path.rglob("*"):
                if file_path.is_file():
                    zip_file.write(file_path, f"{path.name}/{file_path.relative_to(path)}")

    return archive


def _zip_paths(paths: list[Path], archive_name: str) -> FileResponse:
    archive = _create_zip_archive(paths, archive_name)
    return FileResponse(
        archive,
        media_type="application/zip",
        filename=f"{archive_name}.zip",
        background=BackgroundTask(archive.unlink, missing_ok=True),
    )


def _backup_configured() -> bool:
    return bool(DAILY_BACKUP_ENABLED and ADMIN_BACKUP_EMAIL and SMTP_HOST and SMTP_FROM_EMAIL)


def _backup_status() -> dict[str, Any]:
    status = _read_json(backup_status_path(), {})
    return {
        "enabled": DAILY_BACKUP_ENABLED,
        "configured": _backup_configured(),
        "admin_email": ADMIN_BACKUP_EMAIL or None,
        "smtp_host": SMTP_HOST or None,
        "hour_utc": DAILY_BACKUP_HOUR_UTC,
        "max_attachment_mb": MAX_BACKUP_EMAIL_MB,
        "last_result": status.get("last_result"),
        "last_sent_at": status.get("last_sent_at"),
        "last_error_at": status.get("last_error_at"),
        "last_error": status.get("last_error"),
    }


def _send_smtp_message(message: EmailMessage) -> None:
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=60) as smtp:
        if SMTP_USE_TLS:
            smtp.starttls()
        if SMTP_USERNAME:
            smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
        smtp.send_message(message)


def _send_daily_backup_email() -> dict[str, Any]:
    if not _backup_configured():
        raise RuntimeError("Daily backup email is not configured")

    sent_at = datetime.utcnow()
    archive_name = f"agentic-seller-data-{sent_at.strftime('%Y%m%d')}"
    archive = _create_zip_archive([products_dir(), ready_dir()], archive_name)

    try:
        max_bytes = MAX_BACKUP_EMAIL_MB * 1024 * 1024
        archive_size = archive.stat().st_size
        if archive_size > max_bytes:
            size_mb = archive_size / 1024 / 1024
            raise RuntimeError(
                f"Backup zip is {size_mb:.1f} MB, above the {MAX_BACKUP_EMAIL_MB} MB email limit. "
                "Use Download all product data instead, or raise MAX_BACKUP_EMAIL_MB if your SMTP provider allows it."
            )

        message = EmailMessage()
        message["Subject"] = f"Agentic Seller daily backup {sent_at.strftime('%Y-%m-%d')}"
        message["From"] = SMTP_FROM_EMAIL
        message["To"] = ADMIN_BACKUP_EMAIL
        message.set_content(
            "Attached is the daily Agentic Seller product-data backup.\n\n"
            "Included: uploaded products, ready-to-publish products, listing plans, review status, and photos.\n"
            "Excluded: auth files and browser profiles.\n"
        )
        message.add_attachment(
            archive.read_bytes(),
            maintype="application",
            subtype="zip",
            filename=f"{archive_name}.zip",
        )

        _send_smtp_message(message)
    finally:
        archive.unlink(missing_ok=True)

    result = {
        "last_result": "sent",
        "last_sent_at": sent_at.isoformat(),
        "last_error_at": None,
        "last_error": None,
    }
    _write_json(backup_status_path(), result)
    return _backup_status()


def _record_backup_error(exc: Exception) -> None:
    current = _read_json(backup_status_path(), {})
    current.update(
        {
            "last_result": "error",
            "last_error_at": datetime.utcnow().isoformat(),
            "last_error": str(exc),
        }
    )
    _write_json(backup_status_path(), current)


def _seconds_until_next_backup() -> float:
    now = datetime.utcnow()
    target = now.replace(hour=DAILY_BACKUP_HOUR_UTC, minute=0, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return max((target - now).total_seconds(), 60.0)


async def _daily_backup_loop() -> None:
    while True:
        await asyncio.sleep(_seconds_until_next_backup())
        try:
            await asyncio.to_thread(_send_daily_backup_email)
        except Exception as exc:
            _record_backup_error(exc)


@app.on_event("startup")
async def start_retention_task():
    global _retention_task, _backup_task
    _retention_report(delete=True)
    _retention_task = asyncio.create_task(_retention_loop())
    if DAILY_BACKUP_ENABLED:
        _backup_task = asyncio.create_task(_daily_backup_loop())


@app.on_event("shutdown")
async def stop_retention_task():
    if _retention_task:
        _retention_task.cancel()
        with suppress(asyncio.CancelledError):
            await _retention_task
    if _backup_task:
        _backup_task.cancel()
        with suppress(asyncio.CancelledError):
            await _backup_task


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
    return _new_session(username, "boss")


@app.post("/auth/login")
async def login(request: AuthRequest):
    users = _load_users()
    user = users.get(request.username)
    if not user or not _verify_password(request.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return _new_session(request.username, user.get("role", "user"))


@app.get("/auth/session")
async def restore_session(user: dict[str, str] = Depends(current_user)):
    return user


@app.post("/auth/logout")
async def logout(session_data: tuple[str, dict[str, str]] = Depends(_current_session)):
    token_hash, _ = session_data
    sessions = _load_sessions()
    sessions.pop(token_hash, None)
    _save_sessions(sessions)
    return {"logged_out": True}


@app.post("/auth/users")
async def create_user(request: UserCreateRequest, _: dict[str, str] = Depends(boss_user)):
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
    shop: str = Form(""),
    package_size: str = Form("medium"),
    actual_store_shelf_price: float | None = Form(None),
    brand: str = Form(""),
    maker: str = Form(""),
    model: str = Form(""),
    year: str = Form(""),
    material: str = Form(""),
    color: str = Form(""),
    dimensions: str = Form(""),
    llm_notes: str = Form(""),
    files: list[UploadFile] = File(...),
    user: dict[str, str] = Depends(current_user),
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
            "added_by": user["username"] or (_safe_name(added_by) if added_by.strip() else "unknown"),
            "uploaded_at": datetime.utcnow().isoformat(),
            **_metadata_updates(
                shop,
                package_size,
                actual_store_shelf_price,
                brand,
                maker,
                model,
                year,
                material,
                color,
                dimensions,
                llm_notes,
            ),
        },
    )
    return UploadResponse(product_id=product_id, product_dir=str(product_dir), saved_files=saved_files)


@app.get("/products")
async def list_products(status: str | None = None, _: dict[str, str] = Depends(current_user)):
    products = [_product_summary(path) for path in sorted(_iter_product_dirs(), key=lambda p: p.name.lower())]
    if status:
        products = [product for product in products if product["status"] == status]
    return {
        "products": products,
        "products_dir": str(products_dir()),
        "ready_dir": str(ready_dir()),
    }


@app.get("/products/{product_id}")
async def get_product(product_id: str, _: dict[str, str] = Depends(current_user)):
    return _product_summary(_product_path(product_id))


@app.get("/admin/data/export")
async def export_all_data(_: dict[str, str] = Depends(boss_user)):
    return _zip_paths([products_dir(), ready_dir()], "agentic-seller-data")


@app.get("/admin/retention")
async def retention_status(_: dict[str, str] = Depends(boss_user)):
    return _retention_report(delete=False)


@app.post("/admin/retention/run")
async def run_retention_cleanup(_: dict[str, str] = Depends(boss_user)):
    return _retention_report(delete=True)


@app.get("/admin/backup")
async def backup_status(_: dict[str, str] = Depends(boss_user)):
    return _backup_status()


@app.post("/admin/backup/run")
async def run_backup_email(_: dict[str, str] = Depends(boss_user)):
    try:
        return await asyncio.to_thread(_send_daily_backup_email)
    except Exception as exc:
        _record_backup_error(exc)
        raise HTTPException(status_code=400, detail=f"Backup email failed: {exc}") from exc


@app.post("/products/{product_id}/files/rotate")
async def rotate_product_image_by_request(
    product_id: str,
    request: ImageRotateRequest,
    _: dict[str, str] = Depends(boss_user),
):
    if not request.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    file_path = _product_file_path(product_id, request.filename, require_image=True)
    return _rotate_image_file(file_path, request.degrees)


@app.get("/products/{product_id}/files/{filename}")
async def get_product_file(product_id: str, filename: str, _: dict[str, str] = Depends(current_user)):
    file_path = _product_file_path(product_id, filename)
    return FileResponse(file_path)


@app.post("/products/{product_id}/files/{filename}/rotate")
async def rotate_product_image(
    product_id: str,
    filename: str,
    request: ImageRotateRequest,
    _: dict[str, str] = Depends(boss_user),
):
    file_path = _product_file_path(product_id, filename, require_image=True)
    return _rotate_image_file(file_path, request.degrees)


@app.put("/products/{product_id}/metadata")
async def update_product_metadata(
    product_id: str,
    update: ProductMetadataUpdate,
    _: dict[str, str] = Depends(boss_user),
):
    product_dir = _product_path(product_id)
    _write_status(
        product_dir,
        _metadata_updates(
            update.shop,
            update.package_size,
            update.actual_store_shelf_price,
            update.brand,
            update.maker,
            update.model,
            update.year,
            update.material,
            update.color,
            update.dimensions,
            update.llm_notes,
        ),
    )
    return _product_summary(product_dir)


@app.put("/products/{product_id}/marketplaces/{marketplace}")
async def update_product_marketplace(
    product_id: str,
    marketplace: str,
    update: MarketplaceStatusUpdate,
    user: dict[str, str] = Depends(boss_user),
):
    product_dir = _product_path(product_id)
    key = _marketplace_key(marketplace)
    status = _status_for(product_dir)
    marketplaces = status.get("marketplaces") if isinstance(status.get("marketplaces"), dict) else {}
    marketplaces[key] = {
        "listed": update.listed,
        "label": _marketplace_label(key),
        "url": update.url.strip() if update.url and update.url.strip() else None,
        "notes": update.notes.strip() if update.notes and update.notes.strip() else None,
        "source": "manual",
        "updated_by": user["username"],
        "updated_at": datetime.utcnow().isoformat(),
    }
    _write_status(product_dir, {"marketplaces": marketplaces})
    return _product_summary(product_dir)


@app.get("/products/{product_id}/download")
async def download_product(product_id: str, _: dict[str, str] = Depends(boss_user)):
    product_dir = _product_path(product_id)
    return _zip_paths([product_dir], product_dir.name)


@app.delete("/products/{product_id}")
async def delete_product(product_id: str, _: dict[str, str] = Depends(boss_user)):
    product_dir = _product_path(product_id)
    summary = _product_summary(product_dir)
    shutil.rmtree(product_dir)
    return {"deleted": True, "product": summary}


@app.put("/products/{product_id}/listing")
async def update_listing(product_id: str, update: ListingUpdate, _: dict[str, str] = Depends(boss_user)):
    product_dir = _product_path(product_id)
    current = _listing_for(product_dir) or {}
    current_images = current.get("image_paths") or []
    images = current_images if current_images and all(_path_exists(str(path)) for path in current_images) else _current_image_paths(product_dir)
    cover_image = update.cover_image or current.get("cover_image") or (images[0] if images else None)
    if cover_image and not _path_exists(str(cover_image)) and images:
        by_name = {Path(path).name: path for path in images}
        cover_image = by_name.get(Path(str(cover_image)).name, images[0])

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
async def approve_product(
    product_id: str,
    username: str = Form("boss"),
    user: dict[str, str] = Depends(boss_user),
):
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
            "approved_by": user["username"] or username,
            "approved_at": datetime.utcnow().isoformat(),
        },
    )
    shutil.move(str(product_dir), str(destination))
    _repair_listing_image_paths(destination)
    return _product_summary(destination)


@app.post("/products/{product_id}/reopen")
async def reopen_product(
    product_id: str,
    user: dict[str, str] = Depends(boss_user),
):
    product_dir = _product_path(product_id, include_ready=True)
    if product_dir.parent != ready_dir():
        _write_status(product_dir, {"status": "awaiting_review"})
        return _product_summary(product_dir)

    destination = products_dir() / product_dir.name
    if destination.exists():
        destination = products_dir() / f"{product_dir.name}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    _write_status(
        product_dir,
        {
            "status": "awaiting_review",
            "approved_by": None,
            "approved_at": None,
            "reopened_by": user["username"],
            "reopened_at": datetime.utcnow().isoformat(),
        },
    )
    shutil.move(str(product_dir), str(destination))
    _repair_listing_image_paths(destination)
    return _product_summary(destination)
