# Agentic Seller Framework

Autonomous, multi-marketplace listing framework for products represented by image folders.

## What it does

- Discovers product folders from `data/`
- Reads optional product text from `.txt`, `.md`, `.docx`
- Uses multimodal analysis to infer:
  - title
  - category
  - condition
  - key attributes/material
  - estimated price range
  - final listing description
  - best cover image
- Maps listing fields into marketplace-specific payloads
- Executes posting adapters for:
  - OLX
  - Ceneo
  - Facebook Marketplace
- Supports `dry_run` and `publish` modes

## Important note

Live posting requires valid user sessions and may require anti-bot checks (2FA/captcha). This framework keeps a human-in-the-loop for auth while automating structured listing work.

## Quick start

1. Create venv and install deps:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

2. Configure env:

```powershell
Copy-Item .env.example .env
```

Fill `OPENAI_API_KEY`.

### Using with LM Studio (Free/Local)

1. **Download & Install LM Studio.**
2. **Download a Vision-capable model** (e.g., `moondream2` or `llama-3-vision`) in LM Studio.
3. **Start the Local Server** inside LM Studio (usually on port 1234).
4. **Update your `.env`**:
   ```env
   LOCAL_MODEL_API=http://localhost:1234/v1
   OPENAI_API_KEY=lm-studio
   OPENAI_MODEL=local-model  # Or the specific name shown in LM Studio
   ```

3. Run in dry-run (safe):

```powershell
python -m agentic_seller.cli --data-dir data --mode dry_run
```

4. Publish mode (real automation attempts):

```powershell
python -m agentic_seller.cli --data-dir data --mode publish --marketplaces olx facebook ceneo
```

## Output

Each product folder gets:

- `listing_plan.json` (normalized listing data)
- `post_results.json` (adapter execution results)

## Architecture

- `agentic_seller/ingest.py`: dataset/product discovery
- `agentic_seller/analyzer.py`: multimodal extraction + enrichment
- `agentic_seller/marketplaces/*`: adapters
- `agentic_seller/orchestrator.py`: agent loop and dispatch
- `agentic_seller/cli.py`: command line entrypoint
