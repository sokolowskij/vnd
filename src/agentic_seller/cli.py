from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_settings
from .orchestrator import run_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Agentic seller pipeline")
    parser.add_argument("--data-dir", type=Path, required=True, help="Directory with product folders")
    parser.add_argument(
        "--mode",
        choices=["dry_run", "publish"],
        default=None,
        help="dry_run = no real submit, publish = attempt live form automation",
    )
    parser.add_argument(
        "--marketplaces",
        nargs="+",
        default=["olx", "facebook", "ceneo"],
        help="Marketplaces to run: olx facebook ceneo",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = load_settings()
    mode = args.mode or settings.post_mode
    run_pipeline(args.data_dir, settings, mode=mode, selected_marketplaces=args.marketplaces)


if __name__ == "__main__":
    main()
