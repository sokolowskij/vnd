from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..models import ListingPlan, PostResult


class MarketplaceAdapter(ABC):
    name: str

    def authenticate(self, context: Any) -> None:
        page = context.new_page()
        try:
            page.goto("about:blank")
            print(f"  [AUTH] {self.name}: browser opened. Log in, then close the page to continue.", flush=True)
            page.wait_for_event("close", timeout=0)
        finally:
            if not page.is_closed():
                page.close()

    @abstractmethod
    def post(self, context: Any, listing: ListingPlan, mode: str) -> PostResult:
        raise NotImplementedError

