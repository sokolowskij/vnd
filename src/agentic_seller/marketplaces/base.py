from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..models import ListingPlan, PostResult


class MarketplaceAdapter(ABC):
    name: str

    @abstractmethod
    def post(self, context: Any, listing: ListingPlan, mode: str) -> PostResult:
        raise NotImplementedError


