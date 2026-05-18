# AWS Docker Reference

Docker is used on AWS only.

Do not use Docker for the normal local Windows workflow. Local generation and publishing use:

- Python venv
- PowerShell scripts
- LM Studio
- Playwright installed in the local venv

Use `README.md` and `FINAL_README.md` for the current workflow.

## AWS Services

Docker Compose runs:

```text
backend  = FastAPI dashboard/API runtime
frontend = Streamlit dashboard
volume   = agentic_data product/auth/session data
```

The AWS backend image is intentionally lightweight. It should not install Playwright Chromium or browser automation dependencies.

## Start Or Rebuild AWS

```bash
cd /opt/vnd
git pull
chmod +x scripts/*.sh
BUILD=1 ./scripts/aws-start.sh
```

## Frontend-Only Reload

```bash
cd /opt/vnd
./scripts/aws-reload-frontend.sh
```

## Stop App Containers

```bash
cd /opt/vnd
./scripts/aws-stop.sh
```

This stops containers only. It does not stop the EC2 instance or EC2 billing.

## Logs And Status

```bash
docker compose ps
docker compose logs -f backend
docker compose logs -f frontend
```

## Data Volume

Uploaded products live in the backend container:

```text
/app/data/products
```

Approved products live in:

```text
/app/data/ready_to_publish
```

Both are backed by:

```text
agentic_data
```

## Disk Cleanup

Check:

```bash
df -h
docker system df
```

Safe cleanup:

```bash
docker builder prune -af
docker image prune -af
```

Avoid this unless you explicitly accept volume risk:

```bash
docker system prune -af --volumes
```

## Local Windows

Do not run `docker compose up` locally for normal work.

Use:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
```

Then run local workflow scripts:

```powershell
.\scripts\run-local-pipeline.ps1 ...
.\scripts\sync-and-publish-ready.ps1 ...
```
