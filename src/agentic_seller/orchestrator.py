from __future__ import annotations

import json
from contextlib import nullcontext
from pathlib import Path

from .analyzer import ListingAnalyzer
from .config import Settings
from .ingest import discover_products
from .marketplaces import FacebookMarketplaceAdapter, OLXAdapter
from .models import PostResult


def _write_json(path: Path, payload: dict | list) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_pipeline(data_dir: Path, settings: Settings, mode: str, selected_marketplaces: list[str]) -> None:
    products = discover_products(data_dir)
    if not products:
        print(f"No product folders found in: {data_dir}")
        return

    analyzer = ListingAnalyzer(settings)
    user_data_base = Path(settings.user_data_dir).resolve()
    user_data_base.mkdir(parents=True, exist_ok=True)

    adapters = {
        "olx": OLXAdapter(),
        "facebook": FacebookMarketplaceAdapter(),
    }

    active = [name for name in selected_marketplaces if name in adapters]
    if not active:
        print("No valid marketplaces selected.")
        return

    if mode == "publish":
        from playwright.sync_api import sync_playwright

        play_ctx = sync_playwright()
    else:
        play_ctx = nullcontext()

    with play_ctx as p:
        for product in products:
            print(f"Processing: {product.product_id}")
            listing = analyzer.analyze(product)
            listing_path = product.root_dir / "listing_plan.json"
            _write_json(listing_path, listing.to_dict())

            results: list[PostResult] = []
            for name in active:
                if name == "olx" and not settings.enable_olx:
                    continue
                if name == "facebook" and not settings.enable_facebook:
                    continue

                browser_context = None
                if mode == "publish":
                    profile_dir = user_data_base / name
                    browser_context = p.chromium.launch_persistent_context(
                        user_data_dir=str(profile_dir),
                        headless=settings.headless,
                    )

                try:
                    result = adapters[name].post(browser_context, listing, mode)
                    results.append(result)
                    print(f"  - {name}: {'OK' if result.success else 'FAIL'} | {result.message}")
                finally:
                    if browser_context:
                        browser_context.close()

            result_path = product.root_dir / "post_results.json"
            _write_json(result_path, [r.to_dict() for r in results])

