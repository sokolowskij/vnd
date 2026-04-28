from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


@dataclass
class ProductInput:
    product_id: str
    root_dir: Path
    image_paths: list[Path]
    optional_text: str | None = None
    facts: dict[str, Any] | None = None


@dataclass
class ListingPlan:
    product_id: str
    title: str
    description: str
    price: float
    currency: str
    category: str
    condition: str
    attributes: dict[str, Any]
    image_paths: list[str]
    cover_image: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PostResult:
    marketplace: str
    success: bool
    mode: str
    message: str
    external_id: str | None = None
    url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
