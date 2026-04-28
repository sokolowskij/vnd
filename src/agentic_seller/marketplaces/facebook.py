from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..models import ListingPlan, PostResult
from .base import MarketplaceAdapter


class FacebookMarketplaceAdapter(MarketplaceAdapter):
    name = "facebook"

    def authenticate(self, context: Any) -> None:
        page = context.new_page()
        try:
            page.goto("https://www.facebook.com/marketplace/", wait_until="domcontentloaded")
            print("  [AUTH] Facebook opened. Log in if needed, then close the page to continue.", flush=True)
            page.wait_for_event("close", timeout=0)
        finally:
            if not page.is_closed():
                page.close()

    def _first_fillable(self, page: Any, labels: list[str], timeout: int = 2500) -> Any | None:
        candidates = []
        for label in labels:
            label_pattern = re.compile(re.escape(label), re.IGNORECASE)
            candidates.extend(
                [
                    page.get_by_label(label, exact=False),
                    page.get_by_placeholder(label, exact=False),
                    page.get_by_role("textbox", name=label_pattern),
                    page.locator(f"input[aria-label*='{label}'], textarea[aria-label*='{label}']"),
                    page.locator(f"[contenteditable='true'][aria-label*='{label}']"),
                    page.locator(f"label:has-text('{label}')").locator("..").locator(
                        "input, textarea, [contenteditable='true']"
                    ),
                ]
            )

        for candidate in candidates:
            field = candidate.first
            try:
                field.wait_for(state="visible", timeout=timeout)
                return field
            except Exception:
                continue
        return None

    def _fill_field(self, page: Any, labels: list[str], value: str, field_name: str) -> bool:
        field = self._first_fillable(page, labels)
        if field is None:
            print(f"  [WARN] Facebook {field_name} field was not found.")
            return False

        field.fill(value)
        return True

    def _absolute_existing_images(self, listing: ListingPlan) -> list[str]:
        image_paths: list[str] = []
        for image_path in listing.image_paths[:10]:
            path = Path(image_path)
            if not path.is_absolute():
                path = Path.cwd() / path
            if path.exists():
                image_paths.append(str(path))
            else:
                print(f"  [WARN] Image not found, skipping: {path}")
        return image_paths

    def _set_files_from_photo_button(self, page: Any, image_paths: list[str]) -> bool:
        labels = [
            "Dodaj zdjęcia",
            "Dodaj zdjęcie",
            "Zdjęcia",
            "Add photos",
            "Add photo",
            "Photos",
        ]
        for label in labels:
            try:
                button = page.get_by_role("button", name=re.compile(re.escape(label), re.IGNORECASE)).first
                with page.expect_file_chooser(timeout=3000) as chooser_info:
                    button.click(timeout=1500)
                chooser_info.value.set_files(image_paths)
                page.wait_for_timeout(3000)
                print(f"  [OK] Uploaded {len(image_paths)} photo(s) to Facebook.")
                return True
            except Exception:
                continue
        return False

    def _upload_images(self, page: Any, listing: ListingPlan) -> bool:
        image_paths = self._absolute_existing_images(listing)
        if not image_paths:
            print("  [WARN] No existing images found for Facebook upload.")
            return False

        file_selectors = [
            "input[type='file'][accept*='image']",
            "input[type='file'][multiple]",
            "input[type='file']",
        ]
        last_error: Exception | None = None
        for selector in file_selectors:
            file_input = page.locator(selector).first
            try:
                file_input.wait_for(state="attached", timeout=3000)
                file_input.set_input_files(image_paths)
                page.wait_for_timeout(3000)
                print(f"  [OK] Uploaded {len(image_paths)} photo(s) to Facebook.")
                return True
            except Exception as exc:
                last_error = exc

        if self._set_files_from_photo_button(page, image_paths):
            return True

        try:
            page.set_input_files("input[type='file']", image_paths, timeout=10000)
            page.wait_for_timeout(3000)
            print(f"  [OK] Uploaded {len(image_paths)} photo(s) to Facebook.")
            return True
        except Exception as exc:
            print(f"  [WARN] Facebook photo upload failed: {exc or last_error}")
            return False

    def post(self, context: Any, listing: ListingPlan, mode: str) -> PostResult:
        if mode == "dry_run":
            return PostResult(
                marketplace=self.name,
                success=True,
                mode=mode,
                message="Dry-run: payload prepared for Facebook Marketplace.",
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
            filled_steps: list[str] = []
            missing_steps: list[str] = []

            # Using domcontentloaded instead of networkidle as FB is very "heavy"
            page.goto("https://www.facebook.com/marketplace/create/item", wait_until="domcontentloaded")
            
            # Help the user if redirected to login
            if "login" in page.url:
                print("  [ACTION REQUIRED] Please log in to Facebook. The agent will wait.")
                page.wait_for_url("**/marketplace/create/item**", timeout=0)

            page.wait_for_load_state("domcontentloaded")

            if self._fill_field(page, ["Tytuł", "Title"], listing.title, "title"):
                filled_steps.append("title")
            else:
                missing_steps.append("title")

            if self._fill_field(page, ["Cena", "Price"], str(int(listing.price)), "price"):
                filled_steps.append("price")
            else:
                missing_steps.append("price")

            if self._fill_field(page, ["Opis", "Description"], listing.description, "description"):
                filled_steps.append("description")
            else:
                missing_steps.append("description")

            if self._upload_images(page, listing):
                filled_steps.append("photos")
            else:
                missing_steps.append("photos")

            print("  [INFO] Facebook category is left for manual selection.")
            missing_steps.append("category")

            # --- CONDITION HANDLING ---
            try:
                condition_selector = page.locator("label:has-text('Stan')").or_(
                    page.get_by_label("Stan", exact=False)
                ).or_(page.get_by_label("Condition", exact=False))
                if condition_selector.first.is_visible(timeout=5000):
                    condition_selector.first.click()
                    page.wait_for_timeout(1000)

                    target_map = {
                        "Nowy": "Nowy",
                        "Jak nowy": "Używany - jak nowy",
                        "Bardzo dobry": "Używany - bardzo dobry",
                        "Dobry": "Używany - dobry",
                        "Do renowacji": "Używany - dobry",
                    }
                    target_text = target_map.get(listing.condition, "Używany - bardzo dobry")

                    try:
                        option = page.locator(f"role=option >> text='{target_text}'").or_(
                            page.locator(f"span:has-text('{target_text}')")
                        ).first
                        option.click(timeout=3000)
                    except Exception:
                        if "jak nowy" in target_text.lower():
                            page.keyboard.press("ArrowDown")
                            page.keyboard.press("ArrowDown")
                        elif "bardzo dobry" in target_text.lower():
                            page.keyboard.press("ArrowDown")
                            page.keyboard.press("ArrowDown")
                            page.keyboard.press("ArrowDown")
                        else:
                            page.keyboard.press("ArrowDown")
                        page.keyboard.press("Enter")
                    filled_steps.append("condition")
            except Exception as e:
                print(f"  [DEBUG] Condition automation skipped: {e}")

            print(f"  [WAITING] Facebook form prepared. Please review and click 'Publish' in the browser.")
            if missing_steps:
                print(f"  [WARN] Review these fields manually: {', '.join(missing_steps)}")
            print(f"  [WAITING] The agent will proceed once you close the page.")
            page.wait_for_event("close", timeout=0)

            message = "Listing flow completed by human."
            if missing_steps:
                message += f" Manual review needed for: {', '.join(missing_steps)}."
            if filled_steps:
                message += f" Automated: {', '.join(filled_steps)}."

            return PostResult(
                marketplace=self.name,
                success=True,
                mode=mode,
                message=message,
                url=page.url,
            )
        except Exception as exc:
            return PostResult(
                marketplace=self.name,
                success=False,
                mode=mode,
                message=f"Facebook automation failed: {exc}",
            )
        finally:
            if not page.is_closed():
                page.close()
