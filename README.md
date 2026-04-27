# Agentic Seller

Product intake, review, listing generation, and assisted marketplace publishing.

The real workflow is split between:

- **AWS app**: upload products, review generated listings, approve/delete/download product data.
- **Local Windows machine**: run LM Studio and generate listing plans from uploaded photos.
- **Marketplace browser automation**: run locally when publishing needs a logged-in browser session.

## What The App Does

- Users upload product photos and optional notes/documents.
- Boss users review listings, rotate images, pick the cover image, edit listing copy, and approve products.
- Each product can store internal metadata:
  - shop: `KC`, `FW`, `KEN`, `MAG`
  - package size: `small`, `medium`, `large`
  - actual store shelf price, visible only in Boss Review and not used for publishing
- Boss users can download or delete product data.
- The backend periodically removes old product data:
  - uploaded/in-review products: 90 days
  - ready-to-publish products: 30 days
  - configurable with `PENDING_RETENTION_DAYS`, `READY_RETENTION_DAYS`, `RETENTION_CHECK_HOURS`
- The backend can send a daily zip backup of product data to an admin email.

## Where Data Lives

On AWS Docker, uploads are stored inside the backend container at:

```text
/app/data/products/<product id>/
```

Approved products move to:

```text
/app/data/ready_to_publish/<product id>/
```

That `/app/data` directory is backed by the Docker volume `agentic_data`.

On your local machine, synced server data is usually kept at:

```text
C:\Users\jedre\Desktop\snn\data\server-products
```

Each processed product folder gets:

- `listing_plan.json`
- `post_results.json`
- `review_status.json`

## When To Use AWS

Use AWS for the web app and shared review workflow:

- uploading products
- Boss Review
- approval
- deleting products
- downloading product data
- retention cleanup

Start or update the AWS app:

```bash
cd /opt/vnd
git pull
chmod +x scripts/aws-*.sh
./scripts/aws-start.sh
```

For production compose override:

```bash
USE_PROD_COMPOSE=1 ./scripts/aws-start.sh
```

Check status and logs:

```bash
docker compose ps
docker compose logs -f backend
docker compose logs -f frontend
```

### Daily Email Backups

Configure SMTP in `/opt/vnd/.env` to send a daily product-data zip to the admin.

```env
DAILY_BACKUP_ENABLED=true
DAILY_BACKUP_HOUR_UTC=3
ADMIN_BACKUP_EMAIL=admin@example.com
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=smtp-user
SMTP_PASSWORD=smtp-password
SMTP_FROM_EMAIL=agentic-seller@example.com
SMTP_USE_TLS=true
```

The backup includes:

- `/app/data/products`
- `/app/data/ready_to_publish`
- photos
- `listing_plan.json`
- `post_results.json`
- `review_status.json`

The backup excludes auth files and browser profiles.

Restart the backend after changing `.env`:

```bash
cd /opt/vnd
docker compose up -d --force-recreate backend
```

Boss users can also open `Users -> Daily email backup` and send a backup email immediately.

## When To Use Local

Use your local Windows machine when the model or browser session lives locally:

- LM Studio generation
- local browser publishing
- debugging pipeline changes

Create and configure the local environment:

```powershell
cd C:\Users\jedre\Desktop\snn
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
Copy-Item .env.example .env
```

For LM Studio on Windows, `.env` should point at local LM Studio:

```env
LOCAL_MODEL_API=http://localhost:1234/v1
OPENAI_API_KEY=local-model
OPENAI_MODEL=google/gemma-4-e4b
USER_DATA_DIR=browser_profiles
```

Start LM Studio’s local server before running generation.

## Sync Server Uploads To Local

Uploaded products live in the AWS Docker volume, so pull them out through the backend container.

Run from local PowerShell:

```powershell
cd C:\Users\jedre\Desktop\snn

$Key = "$env:USERPROFILE\.ssh\vnd_aws"
$Server = "ubuntu@51.102.104.11"

ssh -i $Key $Server "cd /opt/vnd && docker compose exec -T backend tar -C /app/data/products -czf /tmp/products.tgz . && docker compose cp backend:/tmp/products.tgz /tmp/products.tgz && ls -lh /tmp/products.tgz"
scp -i $Key "${Server}:/tmp/products.tgz" .\server-products.tgz

Remove-Item -Recurse -Force .\data\server-products -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force .\data\server-products
tar -xzf .\server-products.tgz -C .\data\server-products
```

If the server is running with production compose override, replace `docker compose` in the SSH command with:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml
```

## Process Synced Products Locally

Generate or refresh listing plans:

```powershell
.\scripts\run-local-pipeline.ps1 -DataDir .\data\server-products -Mode dry_run -Recalculate
```

Reuse existing listing plans where present:

```powershell
.\scripts\run-local-pipeline.ps1 -DataDir .\data\server-products -Mode dry_run
```

The local runner writes `listing_plan.json` and `post_results.json` into each product folder.

## Push Processed Results Back To AWS

After local processing, push the processed product folders back into `/app/data/products`.

```powershell
cd C:\Users\jedre\Desktop\snn

$Key = "$env:USERPROFILE\.ssh\vnd_aws"
$Server = "ubuntu@51.102.104.11"

tar -czf .\server-products-processed.tgz -C .\data\server-products .
scp -i $Key .\server-products-processed.tgz "${Server}:/tmp/server-products-processed.tgz"

ssh -i $Key $Server "cd /opt/vnd && docker compose cp /tmp/server-products-processed.tgz backend:/tmp/server-products-processed.tgz && docker compose exec -T backend tar -xzf /tmp/server-products-processed.tgz -C /app/data/products"
```

Then refresh Boss Review in the AWS app.

## Publishing

Publishing can create real marketplace listings. Use `dry_run` until the reviewed payload looks correct.

For local browser-assisted publishing:

```powershell
.\scripts\run-local-pipeline.ps1 -DataDir .\data\server-products -Mode publish -Marketplaces facebook
```

Skip the confirmation prompt only when you are sure:

```powershell
.\scripts\run-local-pipeline.ps1 -DataDir .\data\server-products -Mode publish -Marketplaces facebook -Yes
```

## Architecture

- `dashboard.py`: Streamlit review portal
- `agentic_seller/api.py`: FastAPI backend, uploads, review data, deletion, downloads, retention
- `agentic_seller/ingest.py`: product folder discovery
- `agentic_seller/analyzer.py`: multimodal listing generation
- `agentic_seller/orchestrator.py`: pipeline runner
- `agentic_seller/marketplaces/*`: marketplace adapters
- `scripts/run-local-pipeline.ps1`: local generation and publishing helper
