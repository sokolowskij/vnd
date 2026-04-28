from __future__ import annotations

import json
from contextlib import nullcontext
from datetime import datetime
from pathlib import Path

from .analyzer import ListingAnalyzer
from .config import Settings
from .ingest import discover_products
from .models import ListingPlan, ProductInput
from .marketplaces import FacebookMarketplaceAdapter, OLXAdapter
from .models import PostResult


def _write_json(path: Path, payload: dict | list) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_listing(path: Path) -> ListingPlan:
    return ListingPlan(**json.loads(path.read_text(encoding="utf-8")))


def _read_json(path: Path, default: dict | list) -> dict | list:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _marketplace_key(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def _write_marketplace_status(product_dir: Path, result: PostResult) -> None:
    if not result.success or result.mode != "publish":
        return

    status_path = product_dir / "review_status.json"
    status = _read_json(status_path, {})
    if not isinstance(status, dict):
        status = {}
    marketplaces = status.get("marketplaces") if isinstance(status.get("marketplaces"), dict) else {}
    key = _marketplace_key(result.marketplace)
    marketplaces[key] = {
        "listed": True,
        "label": {"facebook": "Facebook", "olx": "OLX", "vinted": "Vinted"}.get(key, key.replace("_", " ").title()),
        "url": result.url,
        "notes": result.message,
        "source": "local_publish",
        "updated_at": datetime.utcnow().isoformat(),
    }
    status["marketplaces"] = marketplaces
    status["updated_at"] = datetime.utcnow().isoformat()
    _write_json(status_path, status)


def _path_exists(path_value: str) -> bool:
    path = Path(path_value)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.exists()


def _repair_listing_image_paths(product: ProductInput, listing: ListingPlan) -> bool:
    current_images = [str(path) for path in product.image_paths]
    if not current_images:
        return False

    if listing.image_paths and all(_path_exists(path) for path in listing.image_paths):
        return False

    current_by_name = {Path(path).name: path for path in current_images}
    cover_name = Path(listing.cover_image).name if listing.cover_image else ""

    listing.image_paths = current_images
    listing.cover_image = current_by_name.get(cover_name, current_images[0])
    return True


def run_pipeline(
    data_dir: Path,
    settings: Settings,
    mode: str,
    selected_marketplaces: list[str],
    use_cached_listings: bool = False,
    auth_mode: bool = False,
) -> None:
    user_data_base = Path(settings.user_data_dir).resolve()
    user_data_base.mkdir(parents=True, exist_ok=True)

    adapters = {
        "olx": OLXAdapter(),
        "facebook": FacebookMarketplaceAdapter(),
    }

    active = [name for name in selected_marketplaces if name in adapters]
    if not active:
        print("No valid marketplaces selected.", flush=True)
        return

    if auth_mode:
        from playwright.sync_api import sync_playwright

        print("Auth mode: opening persistent browser profiles for login. No listings will be posted.", flush=True)
        with sync_playwright() as p:
            for name in active:
                profile_dir = user_data_base / name
                browser_context = p.chromium.launch_persistent_context(
                    user_data_dir=str(profile_dir),
                    headless=False,
                )
                try:
                    adapters[name].authenticate(browser_context)
                finally:
                    browser_context.close()
        return

    products = discover_products(data_dir)
    if not products:
        print(f"No product folders found in: {data_dir}", flush=True)
        return

    analyzer = ListingAnalyzer(settings)
    print(f"Discovered {len(products)} product(s) in {data_dir}", flush=True)

    if mode == "publish":
        from playwright.sync_api import sync_playwright

        play_ctx = sync_playwright()
    else:
        play_ctx = nullcontext()

    successful_products: set[str] = set()
    with play_ctx as p:
        for product in products:
            print(f"Processing: {product.product_id}", flush=True)
            listing_path = product.root_dir / "listing_plan.json"
            if use_cached_listings and listing_path.exists():
                listing = _load_listing(listing_path)
                print(f"  - using cached listing: {listing_path}", flush=True)
                if _repair_listing_image_paths(product, listing):
                    _write_json(listing_path, listing.to_dict())
                    print("  - repaired cached listing image paths for current product folder", flush=True)
            else:
                listing = analyzer.analyze(product)
                _write_json(listing_path, listing.to_dict())
                print(f"  - wrote listing: {listing_path}", flush=True)

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
                    _write_marketplace_status(product.root_dir, result)
                    print(f"  - {name}: {'OK' if result.success else 'FAIL'} | {result.message}", flush=True)
                finally:
                    if browser_context:
                        browser_context.close()

            if mode == "publish" and results and all(result.success for result in results):
                successful_products.add(product.product_id)

            result_path = product.root_dir / "post_results.json"
            _write_json(result_path, [r.to_dict() for r in results])
            print(f"  - wrote results: {result_path}", flush=True)

    if mode == "publish":
        published_count = len(successful_products)
        total_count = len(products)
        print(f"Publish summary: {published_count}/{total_count} item(s) published.", flush=True)
        answer = input("Confirm the published item count by typing the number shown before '/': ").strip()
        if answer != str(published_count):
            raise SystemExit(f"Publish count confirmation failed. Expected {published_count}, got {answer or '<empty>'}.")

    analyzer.print_usage_summary()
