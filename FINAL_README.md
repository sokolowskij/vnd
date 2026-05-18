# Final Workflow: AWS Dashboard, Local Generation And Publishing

This is the current operating model for the project.

AWS is only for:

- Streamlit dashboard
- FastAPI backend
- user accounts/sessions
- product uploads
- Boss Review
- photo rotation/deletion
- approvals
- storing product data in the Docker volume

The local Windows PC is for:

- LM Studio
- listing generation
- Playwright/browser automation
- marketplace publishing

This keeps the AWS deployment smaller and cheaper. The AWS backend image no longer installs Playwright Chromium or browser system dependencies.

## Repository Locations

Local Windows PC:

```powershell
cd C:\Users\jedre\Desktop\snn
```

AWS server:

```bash
cd /opt/vnd
```

AWS SSH:

```powershell
ssh -i $env:USERPROFILE\.ssh\vnd_aws ubuntu@51.102.104.11
```

## AWS Deployment

AWS runs Docker Compose.

After pushing code from local Git, update AWS:

```bash
cd /opt/vnd
git pull
chmod +x scripts/*.sh
BUILD=1 ./scripts/aws-start.sh
```

Use `BUILD=1` after changes to:

- `dashboard.py`
- `src/agentic_seller/api.py`
- Dockerfiles
- dependency files

For frontend-only changes you can use:

```bash
cd /opt/vnd
FRONTEND_ONLY=1 ./scripts/aws-reload-frontend.sh
```

For normal pulled app updates where frontend and backend should stay aligned:

```bash
cd /opt/vnd
./scripts/aws-reload-frontend.sh
```

Despite the name, `aws-reload-frontend.sh` rebuilds and recreates both `backend` and `frontend` unless `FRONTEND_ONLY=1` is set.

Older direct Docker commands still work:

```bash
docker compose build backend frontend
docker compose up -d --force-recreate backend frontend
```

Prefer the scripts because they handle health checks and the repo path consistently.

Stop app containers without stopping the EC2 instance:

```bash
cd /opt/vnd
./scripts/aws-stop.sh
```

Check services:

```bash
docker compose ps
docker compose logs -f backend
docker compose logs -f frontend
```

## Lightweight AWS Images

AWS uses these dependency files:

```text
requirements.aws-backend.txt
requirements.aws-frontend.txt
```

Local development still uses:

```text
requirements.txt
pyproject.toml
```

Do not add Playwright, OpenAI, LM Studio, or publishing dependencies to the AWS requirements unless the AWS role changes again.

The backend Docker image should stay dashboard/API-only.

## Local Windows Setup

Run once on a new Windows PC:

```powershell
cd C:\Users\jedre\Desktop\snn
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

For LM Studio, local `.env` should contain:

```env
LOCAL_MODEL_API=http://localhost:1234/v1
OPENAI_API_KEY=local-model
OPENAI_MODEL=google/gemma-4-e4b
USER_DATA_DIR=browser_profiles
```

Start LM Studio, load the model, and enable the local server on port `1234`.

## Download Uploaded Products From AWS

Run in local PowerShell:

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

## Generate Listings Locally

Start LM Studio first.

Regenerate listing plans from downloaded AWS photos:

```powershell
.\scripts\run-local-pipeline.ps1 -DataDir .\data\server-products -Mode dry_run -Marketplaces facebook -Recalculate
```

Use cached `listing_plan.json` files when present:

```powershell
.\scripts\run-local-pipeline.ps1 -DataDir .\data\server-products -Mode dry_run -Marketplaces facebook
```

This writes:

```text
listing_plan.json
post_results.json
```

It does not publish anything in `dry_run` mode.

## Upload Generated Listings Back To AWS

Run in local PowerShell:

```powershell
tar -czf .\server-products-processed.tgz -C .\data\server-products .
scp -i $Key .\server-products-processed.tgz "${Server}:/tmp/server-products-processed.tgz"
ssh -i $Key $Server "cd /opt/vnd && $Compose cp /tmp/server-products-processed.tgz backend:/tmp/server-products-processed.tgz && $Compose exec -T backend tar -xzf /tmp/server-products-processed.tgz -C /app/data/products"
```

Then open the AWS dashboard, refresh Boss Review, edit/rotate/delete photos if needed, and approve items.

Dashboard URL:

```text
http://51.102.104.11:8501
```

## Publish Approved Items Locally

After Boss Review approval, run this on local Windows:

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

Try to click the final publish button automatically:

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

## Data Locations

AWS product uploads live inside the backend container at:

```text
/app/data/products
```

AWS approved items live at:

```text
/app/data/ready_to_publish
```

Those paths are backed by the Docker volume:

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

## Disk Cleanup On AWS

Check disk:

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

Do not run this unless you explicitly understand the volume risk:

```bash
docker system prune -af --volumes
```

The active product-data volume should remain attached to the backend container.

## Cost Model

The expected AWS costs are:

- EC2 compute: the always-running instance
- VPC/public IPv4: hourly public IP charge
- EC2 other: mostly EBS root volume

The new lightweight AWS image reduces disk usage and build time. It does not eliminate EC2 compute cost while the instance is running.

To reduce compute cost, stop the EC2 instance when it is not needed. Stopping Docker containers is not enough to stop EC2 billing.

## Common Problems

After `git pull`, old code still runs:

```bash
cd /opt/vnd
BUILD=1 ./scripts/aws-start.sh
```

AWS dashboard cannot see generated descriptions:

- confirm local generation created `listing_plan.json`
- upload processed data back to AWS
- refresh Boss Review

Publishing tries to use old data:

- re-download approved items with `sync-and-publish-ready.ps1`
- confirm item has `listing_plan.json`

AWS image becomes large again:

- check `Dockerfile.backend`
- confirm it does not run `playwright install chromium`
- confirm it uses `requirements.aws-backend.txt`, not `requirements.txt`
