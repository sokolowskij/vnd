# Agentic Seller

Product intake, review, listing generation, and assisted marketplace publishing.

## Current Model

Docker is used on AWS only.

Local Windows does not need Docker.

Use AWS for:

- Streamlit dashboard
- FastAPI backend
- uploads
- Boss Review
- photo rotation/deletion
- approvals
- product data storage

Use the local Windows PC for:

- LM Studio
- listing generation
- Playwright browser automation
- marketplace publishing

This split keeps AWS lightweight and avoids installing browser automation dependencies on the server.

## Main Docs

Use this file for the normal workflow.

Use [FINAL_README.md](FINAL_README.md) for the full operational runbook.

Use [NEW_PC_LOCAL_WORKFLOW.md](NEW_PC_LOCAL_WORKFLOW.md) for setting up a fresh Windows PC.

## AWS Deployment

AWS runs Docker Compose. The AWS containers are dashboard/API only.

The backend AWS image uses:

```text
requirements.aws-backend.txt
```

The frontend AWS image uses:

```text
requirements.aws-frontend.txt
```

The local PC still uses:

```text
requirements.txt
pyproject.toml
```

Connect to AWS from local PowerShell:

```powershell
ssh -i $env:USERPROFILE\.ssh\vnd_aws ubuntu@51.102.104.11
```

Update AWS after pushing code:

```bash
cd /opt/vnd
git pull
chmod +x scripts/*.sh
BUILD=1 ./scripts/aws-start.sh
```

Use `BUILD=1` after backend, frontend, Dockerfile, or dependency changes.

For normal app updates where backend/API and frontend should stay in sync:

```bash
cd /opt/vnd
./scripts/aws-reload-frontend.sh
```

Despite the script name, this rebuilds and recreates both `backend` and `frontend` by default.

For true frontend-only changes:

```bash
cd /opt/vnd
FRONTEND_ONLY=1 ./scripts/aws-reload-frontend.sh
```

Older commands like `docker compose build backend frontend` and
`docker compose up -d --force-recreate backend frontend` still work, but the scripts above are the preferred interface.

Check AWS services:

```bash
docker compose ps
docker compose logs -f backend
docker compose logs -f frontend
```

Stop app containers:

```bash
cd /opt/vnd
./scripts/aws-stop.sh
```

Stopping containers does not stop EC2 billing. Stop the EC2 instance if you want to stop compute cost.

## Local Windows Setup

Run this in PowerShell:

```powershell
cd C:\Users\jedre\Desktop\snn
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

For LM Studio:

```env
LOCAL_MODEL_API=http://localhost:1234/v1
OPENAI_API_KEY=local-model
OPENAI_MODEL=google/gemma-4-e4b
USER_DATA_DIR=browser_profiles
```

Start LM Studio, load the model, and enable the local server on port `1234`.

Do not install Docker Desktop for the local workflow. It is not needed.

## Data Locations

AWS uploads are inside the backend container:

```text
/app/data/products
```

AWS approved items are inside:

```text
/app/data/ready_to_publish
```

Both are backed by the Docker volume:

```text
agentic_data
```

They are not normal files under `/opt/vnd/data`.

Local downloaded raw products:

```text
.\data\server-products
```

Local downloaded approved products:

```text
.\data\ready_to_publish
```

## Download Uploaded Products From AWS

Run from local PowerShell:

```powershell
cd C:\Users\jedre\Desktop\snn

$Key = "$env:USERPROFILE\.ssh\vnd_aws"
$Server = "ubuntu@51.102.104.11"
$Compose = "docker compose"

ssh -i $Key $Server "cd /opt/vnd && $Compose exec -T backend tar -C /app/data/products -czf /tmp/products.tgz . && $Compose cp backend:/tmp/products.tgz /tmp/products.tgz && ls -lh /tmp/products.tgz"
scp -i $Key "${Server}:/tmp/products.tgz" .\server-products.tgz

Remove-Item -Recurse -Force .\data\server-products -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force .\data\server-products
tar -xzf .\server-products.tgz -C .\data\server-products
```

If AWS uses the production compose override:

```powershell
$Compose = "docker compose -f docker-compose.yml -f docker-compose.prod.yml"
```

This uses Docker on AWS through SSH. It does not require Docker locally.

## Generate Listings Locally

Start LM Studio first.

Generate fresh listing plans:

```powershell
.\scripts\run-local-pipeline.ps1 -DataDir .\data\server-products -Mode dry_run -Marketplaces facebook -Recalculate
```

Use cached `listing_plan.json` when available:

```powershell
.\scripts\run-local-pipeline.ps1 -DataDir .\data\server-products -Mode dry_run -Marketplaces facebook
```

This writes:

```text
listing_plan.json
post_results.json
```

No marketplace listing is published in `dry_run` mode.

## Upload Generated Listings Back To AWS

Run from local PowerShell:

```powershell
tar -czf .\server-products-processed.tgz -C .\data\server-products .
scp -i $Key .\server-products-processed.tgz "${Server}:/tmp/server-products-processed.tgz"
ssh -i $Key $Server "cd /opt/vnd && $Compose cp /tmp/server-products-processed.tgz backend:/tmp/server-products-processed.tgz && $Compose exec -T backend tar -xzf /tmp/server-products-processed.tgz -C /app/data/products"
```

Then open the AWS dashboard and refresh Boss Review.

Dashboard:

```text
http://51.102.104.11:8501
```

## Boss Review

Use the AWS dashboard to:

- review descriptions
- edit title/price/category/condition
- edit product facts
- rotate photos
- delete photos
- choose cover photo
- approve items

Approved items move from:

```text
/app/data/products
```

to:

```text
/app/data/ready_to_publish
```

## Publish Approved Items Locally

Run from local PowerShell:

```powershell
cd C:\Users\jedre\Desktop\snn
.\scripts\sync-and-publish-ready.ps1 -Marketplaces facebook -InstallBrowsers
```

After Playwright Chromium was installed once:

```powershell
.\scripts\sync-and-publish-ready.ps1 -Marketplaces facebook
```

Log in to Facebook only:

```powershell
.\scripts\sync-and-publish-ready.ps1 -AuthMode -Marketplaces facebook
```

Try final publish click automatically:

```powershell
.\scripts\sync-and-publish-ready.ps1 -Marketplaces facebook -AutoPublish -PublishingEmail you@example.com
```

Useful options:

```powershell
.\scripts\sync-and-publish-ready.ps1 -Marketplaces olx,facebook
.\scripts\sync-and-publish-ready.ps1 -Marketplaces facebook -Yes
.\scripts\sync-and-publish-ready.ps1 -Marketplaces facebook -SkipDependencyInstall
.\scripts\sync-and-publish-ready.ps1 -Marketplaces facebook -KeepArchive
.\scripts\sync-and-publish-ready.ps1 -Marketplaces facebook -UseProdCompose
.\scripts\sync-and-publish-ready.ps1 -Marketplaces facebook -PublishLocation "Warsaw, Poland"
```

## AWS Disk Cleanup

Check disk usage:

```bash
df -h
docker system df
```

Safe cleanup:

```bash
docker builder prune -af
docker image prune -af
sudo journalctl --vacuum-time=7d
```

Do not run this unless you explicitly accept Docker volume risk:

```bash
docker system prune -af --volumes
```

## Architecture

- `dashboard.py`: Streamlit dashboard
- `src/agentic_seller/api.py`: FastAPI backend for uploads, review data, auth, retention, backup, deletion, downloads
- `src/agentic_seller/analyzer.py`: local multimodal listing generation
- `src/agentic_seller/orchestrator.py`: local pipeline runner
- `src/agentic_seller/marketplaces/*`: local marketplace browser automation
- `scripts/run-local-pipeline.ps1`: local generation helper
- `scripts/sync-and-publish-ready.ps1`: local approved-item sync and publishing helper

## Important Rule

Do not run Playwright publishing on AWS.

Do not run LM Studio generation on AWS.

AWS is the dashboard and product-data server. The local PC does generation and publishing.
