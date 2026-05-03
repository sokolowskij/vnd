from __future__ import annotations

from typing import Any

from ..models import ListingPlan, PostResult, PublishOptions
from .base import MarketplaceAdapter


class OLXAdapter(MarketplaceAdapter):
    name = "olx"

    def authenticate(self, context: Any) -> None:
        page = context.new_page()
        try:
            page.goto("https://www.olx.pl/", wait_until="domcontentloaded")
            print("  [AUTH] OLX opened. Log in if needed, then close the page to continue.", flush=True)
            page.wait_for_event("close", timeout=0)
        finally:
            if not page.is_closed():
                page.close()

    def _fill_first_available(self, page: Any, labels: list[str], value: str, field_name: str) -> bool:
        for label in labels:
            try:
                page.get_by_label(label, exact=False).fill(value, timeout=2500)
                return True
            except Exception:
                pass
            try:
                page.get_by_placeholder(label, exact=False).fill(value, timeout=2500)
                return True
            except Exception:
                continue
        print(f"  [WARN] OLX {field_name} field was not found.")
        return False

    def _click_final_submit(self, page: Any) -> bool:
        for label in ["Dodaj", "Opublikuj", "Publish", "Submit"]:
            try:
                page.get_by_role("button", name=label).last.click(timeout=5000)
                page.wait_for_timeout(3000)
                return True
            except Exception:
                continue
        print("  [WARN] OLX final publish button was not found.")
        return False

    def post(self, context: Any, listing: ListingPlan, mode: str, options: PublishOptions | None = None) -> PostResult:
        options = options or PublishOptions()
        if mode == "dry_run":
            if options.auto_publish:
                return PostResult(
                    marketplace=self.name,
                    success=True,
                    mode=mode,
                    message=(
                        "Dry-run auto-publish: payload prepared for OLX. "
                        f"Would fill location '{options.location}', "
                        f"email '{options.contact_email or '-'}', and click final publish."
                    ),
                )
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

            filled_steps = []
            missing_steps = []
            if self._fill_first_available(
                page,
                ["Lokalizacja", "Miejscowość", "Miasto", "Kod pocztowy", "Location", "City", "Postal code"],
                options.location,
                "location",
            ):
                filled_steps.append("location")
            else:
                missing_steps.append("location")

            if options.contact_email:
                if self._fill_first_available(
                    page,
                    ["E-mail", "Email", "Adres e-mail", "Adres email"],
                    options.contact_email,
                    "email",
                ):
                    filled_steps.append("email")
                else:
                    missing_steps.append("email")

            auto_clicked = False
            if options.auto_publish:
                print("  [AUTO] OLX form prepared. Attempting final publish click.")
                auto_clicked = self._click_final_submit(page)
                if not auto_clicked:
                    missing_steps.append("final_publish")
            else:
                print(f"  [WAITING] OLX form filled. Please review and click 'Dodaj' in the browser.")
                print(f"  [WAITING] The agent will proceed once you close the page or the browser context.")
                page.wait_for_event("close", timeout=0)

            message = "Listing flow completed by automation." if options.auto_publish else "Listing flow completed by human."
            if filled_steps:
                message += f" Automated: {', '.join(filled_steps)}."
            if missing_steps:
                message += f" Manual review needed for: {', '.join(missing_steps)}."
            if options.auto_publish and auto_clicked:
                message += " Final publish button clicked."

            return PostResult(
                marketplace=self.name,
                success=not (options.auto_publish and not auto_clicked),
                mode=mode,
                message=message,
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
