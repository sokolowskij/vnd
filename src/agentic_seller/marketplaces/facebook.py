from __future__ import annotations

from typing import Any

from ..models import ListingPlan, PostResult
from .base import MarketplaceAdapter


class FacebookMarketplaceAdapter(MarketplaceAdapter):
    name = "facebook"

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
            # Using domcontentloaded instead of networkidle as FB is very "heavy"
            page.goto("https://www.facebook.com/marketplace/create/item", wait_until="domcontentloaded")
            
            # Help the user if redirected to login
            if "login" in page.url:
                print("  [ACTION REQUIRED] Please log in to Facebook. The agent will wait.")
                page.wait_for_url("**/marketplace/create/item**", timeout=0)

            # Look for "Tytuł" or "Title" labels (FB uses aria-labels heavily)
            # Try Polish first, then English fallbacks
            title_input = (
                page.get_by_label("Tytuł", exact=False) 
                or page.get_by_label("Title", exact=False)
                or page.locator("label:has-text('Tytuł')").locator("..").locator("input")
            )

            if title_input.first.is_visible(timeout=10000):
                title_input.first.fill(listing.title)
                
                # Fill others if possible
                price_input = page.get_by_label("Cena", exact=False).or_(page.get_by_label("Price", exact=False))
                if price_input.first.is_visible():
                    price_input.first.fill(str(int(listing.price)))

                desc_input = page.get_by_label("Opis", exact=False).or_(page.get_by_label("Description", exact=False))
                if desc_input.first.is_visible():
                    desc_input.first.fill(listing.description)

                # --- CATEGORY HANDLING ---
                # Facebook Category selector is notoriously difficult to automate due to focus trapping.
                # We will perform a best-effort fill, but wrap it in a try/except to ensure the REST of the form fills.
                try:
                    category_selector = page.locator("label:has-text('Kategoria')").or_(page.get_by_label("Kategoria", exact=False))
                    if category_selector.first.is_visible(timeout=5000):
                        category_selector.first.click()
                        page.wait_for_timeout(1000)
                        
                        # Type only (avoiding Ctrl+A which as the user noted, selects the whole page sometimes)
                        page.keyboard.type(listing.category, delay=100)
                        page.wait_for_timeout(2000)
                        
                        # Try to click the specific option, but don't hang if it fails
                        try:
                            page.locator(f"div[role='listbox'] div[role='option']").first.click(timeout=3000)
                        except:
                            page.keyboard.press("Enter")
                except Exception as e:
                    print(f"  [DEBUG] Category automation skipped: {e}")

                # --- CONDITION HANDLING ---
                # Move condition AFTER category so that even if category fails, state is attempted.
                try:
                    condition_selector = page.locator("label:has-text('Stan')").or_(page.get_by_label("Stan", exact=False))
                    if condition_selector.first.is_visible(timeout=5000):
                        condition_selector.first.click()
                        page.wait_for_timeout(1000)
                        
                        target_map = {
                            "Nowy": "Nowy",
                            "Jak nowy": "Używany - jak nowy",
                            "Bardzo dobry": "Używany - bardzo dobry",
                            "Dobry": "Używany - dobry",
                            "Do renowacji": "Używany - dobry"
                        }
                        target_text = target_map.get(listing.condition, "Używany - bardzo dobry")
                        
                        try:
                            # Try multiple ways to find the option
                            option = page.locator(f"role=option >> text='{target_text}'").or_(page.locator(f"span:has-text('{target_text}')")).first
                            option.click(timeout=3000)
                        except:
                            # Direct keyboard sequence as ultimate fallback
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
                except Exception as e:
                    print(f"  [DEBUG] Condition automation skipped: {e}")

                # Facebook often has multiple hidden file inputs. Using .first to avoid strict mode violation.
                for img in listing.image_paths[:10]:
                    page.locator("input[type='file']").first.set_input_files(img)

            print(f"  [WAITING] Facebook form prepared. Please review and click 'Publish' in the browser.")
            print(f"  [WAITING] The agent will proceed once you close the page.")
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
                message=f"Facebook automation failed: {exc}",
            )
        finally:
            if not page.is_closed():
                page.close()
