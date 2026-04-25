from __future__ import annotations

from typing import Any

from ..models import ListingPlan, PostResult
from .base import MarketplaceAdapter


class OLXAdapter(MarketplaceAdapter):
    name = "olx"

    def post(self, context: Any, listing: ListingPlan, mode: str) -> PostResult:
        if mode == "dry_run":
            return PostResult(
                marketplace=self.name,
                success=True,
                mode=mode,
                message="Dry-run: payload prepared for OLX.",
            )

        if context is None:
            return PostResult(
                marketplace=self.name,
                success=False,
                mode=mode,
                message="Browser context is required for publish mode.",
            )

        page = context.new_page()
        try:
            page.goto("https://www.olx.pl/d/nowe-ogloszenie/", wait_until="networkidle")
            # Best-effort selectors; OLX UI changes are expected.
            page.get_by_label("Tytuł ogłoszenia").fill(listing.title)
            page.get_by_label("Opis").fill(listing.description)
            page.get_by_label("Cena").fill(str(int(listing.price)))
            for img in listing.image_paths[:8]:
                page.locator("input[type='file']").set_input_files(img)

            # Human confirmation: Wait indefinitely for page to close or user to finish
            print(f"  [WAITING] OLX form filled. Please review and click 'Dodaj' in the browser.")
            print(f"  [WAITING] The agent will proceed once you close the page or the browser context.")
            page.wait_for_event("close", timeout=0)

            return PostResult(
                marketplace=self.name,
                success=True,
                mode=mode,
                message="Listing flow completed by human.",
                url=page.url,
            )
        except Exception as exc:
            return PostResult(
                marketplace=self.name,
                success=False,
                mode=mode,
                message=f"OLX automation failed: {exc}",
            )
        finally:
            if not page.is_closed():
                page.close()
