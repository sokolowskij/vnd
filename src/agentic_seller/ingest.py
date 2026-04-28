from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import ProductInput

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
_TEXT_EXTS = {".txt", ".md", ".docx"}
_FACT_FIELDS = {
    "brand": "Brand",
    "maker": "Maker",
    "model": "Model",
    "material": "Material",
    "color": "Color",
    "dimensions": "Dimensions",
    "llm_notes": "Additional notes",
}


def _read_optional_text(path: Path) -> str | None:
    if path.suffix.lower() == ".txt" or path.suffix.lower() == ".md":
        return path.read_text(encoding="utf-8", errors="ignore").strip() or None

    if path.suffix.lower() == ".docx":
        try:
            from docx import Document
        except ImportError:
            return None

        doc = Document(path)
        text = "\n".join(p.text for p in doc.paragraphs).strip()
        return text or None

    return None


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _product_facts(product_dir: Path) -> dict[str, str]:
    status = _read_json(product_dir / "review_status.json")
    facts: dict[str, str] = {}
    for key, label in _FACT_FIELDS.items():
        value = status.get(key)
        if value is not None and str(value).strip():
            facts[label] = str(value).strip()
    return facts


def discover_products(data_dir: Path) -> list[ProductInput]:
    products: list[ProductInput] = []

    for entry in sorted(data_dir.iterdir()):
        if not entry.is_dir():
            continue

        # Allow one nested folder level from the provided sample structure.
        candidate_dirs = [entry]
        inner_dirs = [d for d in entry.iterdir() if d.is_dir()]
        if len(inner_dirs) == 1:
            candidate_dirs.insert(0, inner_dirs[0])

        selected_dir = None
        selected_images: list[Path] = []
        optional_text = None

        for d in candidate_dirs:
            images = sorted([p for p in d.iterdir() if p.is_file() and p.suffix.lower() in _IMAGE_EXTS])
            texts = sorted([p for p in d.iterdir() if p.is_file() and p.suffix.lower() in _TEXT_EXTS])
            if images:
                selected_dir = d
                selected_images = images
                if texts:
                    optional_text = _read_optional_text(texts[0])
                break

        if selected_dir is None:
            continue

        products.append(
            ProductInput(
                product_id=entry.name,
                root_dir=selected_dir,
                image_paths=selected_images,
                optional_text=optional_text,
                facts=_product_facts(selected_dir),
            )
        )

    return products
