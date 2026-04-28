# Bartosz Tutaj

This is the practical handoff for this project: what worked, what did not work, which terminal to use, and the easiest way to give the project to another very novice developer.

## Best Setup For A New Novice Dev

Use two paths:

- Local Windows development: Python venv + PowerShell scripts.
- AWS deployment: Docker Compose.

Do not make WSL required. Docker is still useful, but mostly for AWS and production-like deployment. For a novice Windows developer, the lowest-friction local setup is plain Windows PowerShell, Python, LM Studio, and the existing helper scripts.

Why:

- Docker Desktop on Windows is extra setup, extra concepts, and usually depends on WSL2 anyway.
- The app already needs local Windows things like LM Studio and sometimes a logged-in browser profile.
- AWS already runs the real shared app in Docker, so local Docker is not needed for basic development.
- A new dev can run and debug the Python app directly without learning containers first.

The ideal future state is:

- `scripts/setup-windows-dev.ps1`: creates `.venv`, installs dependencies, installs Playwright browser, creates `.env` from `.env.example`.
- `scripts/start-windows-dev.ps1`: starts the local app in one obvious way.
- `scripts/open-lmstudio-aws-tunnel.ps1`: already exists and opens the tunnel from AWS to local LM Studio.
- `scripts/run-local-pipeline.sh`: main AWS-side runner for processing uploaded AWS data with local LM Studio.

## Mental Model

There are three places involved:

- Local Windows PC: coding, LM Studio, Git commits, optional local pipeline processing.
- AWS server: real uploaded product data, Docker containers, shared web app.
- Browser: the user-facing app for uploads, Boss Review, deletes, downloads, approvals.

Uploaded photos on AWS are not normal files in `/opt/vnd/data`. They live inside the backend Docker volume and are visible inside the backend container at:

```text
/app/data/products/<product id>/
```

Approved products move to:

```text
/app/data/ready_to_publish/<product id>/
```

That container path is backed by the Docker volume:

```text
agentic_data
```

## Which Terminal To Use

Use local Windows PowerShell for:

- Git work on your PC.
- Starting LM Studio.
- Opening the SSH reverse tunnel to AWS.
- Local Python virtualenv setup.
- Syncing data down from AWS if needed.

Use AWS SSH bash for:

- `git pull` on the server.
- `docker compose` commands.
- Running `scripts/run-local-pipeline.sh`.
- Checking AWS logs.

Do not run PowerShell `.ps1` files directly on Ubuntu. Ubuntu bash needs `.sh` scripts.

## First Time Setup On Windows

Run this on the local Windows PC in PowerShell:

```powershell
cd C:\Users\jedre\Desktop\snn
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
Copy-Item .env.example .env
```

For local LM Studio, `.env` should include:

```env
LOCAL_MODEL_API=http://localhost:1234/v1
OPENAI_API_KEY=local-model
OPENAI_MODEL=google/gemma-4-e4b
USER_DATA_DIR=browser_profiles
```

Start LM Studio, load the model, and enable the local server on port `1234`.

## Update AWS App

Run this in an AWS SSH terminal:

```bash
ssh -i ~/.ssh/vnd_aws ubuntu@51.102.104.11
cd /opt/vnd
git pull
chmod +x scripts/*.sh
docker compose build backend frontend
docker compose up -d --force-recreate backend frontend
docker compose ps
```

Use this after frontend/API fixes, for example the image rotation route fix. A plain `git pull` is not enough when containers still run an old image.

To watch logs:

```bash
cd /opt/vnd
docker compose logs -f backend
```

```bash
cd /opt/vnd
docker compose logs -f frontend
```

## Generate Listings On AWS Using Local LM Studio

This was the workflow that worked best.

The data stays on AWS. Your Windows machine only provides the model through LM Studio.

### 1. Windows PowerShell: Open The LM Studio Tunnel

Start LM Studio first and enable its local server on port `1234`.

Then run this on Windows and keep the terminal open:

```powershell
cd C:\Users\jedre\Desktop\snn
.\scripts\open-lmstudio-aws-tunnel.ps1
```

Equivalent manual command:

```powershell
ssh -i $env:USERPROFILE\.ssh\vnd_aws -N -o ExitOnForwardFailure=yes -R 127.0.0.1:1234:127.0.0.1:1234 ubuntu@51.102.104.11
```

This means AWS `http://127.0.0.1:1234/v1` forwards to LM Studio running on your Windows PC.

### 2. AWS SSH Bash: Test The Tunnel

Run this on AWS:

```bash
curl http://127.0.0.1:1234/v1/models
```

If this fails, the pipeline will not work. Check that:

- LM Studio server is running.
- The Windows tunnel terminal is still open.
- The AWS SSH command connected successfully.

### 3. AWS SSH Bash: Run The Pipeline

Run this on AWS:

```bash
cd /opt/vnd
chmod +x scripts/run-local-pipeline.sh
MODE=dry_run MARKETPLACES="facebook" ./scripts/run-local-pipeline.sh
```

To force regeneration instead of using existing `listing_plan.json` files:

```bash
cd /opt/vnd
MODE=dry_run MARKETPLACES="facebook" ./scripts/run-local-pipeline.sh -Recalculate
```

If Python code changed and the backend image needs to be rebuilt:

```bash
cd /opt/vnd
REBUILD=1 MODE=dry_run MARKETPLACES="facebook" ./scripts/run-local-pipeline.sh -Recalculate
```

For real publishing, be careful:

```bash
cd /opt/vnd
MODE=publish MARKETPLACES="facebook" ./scripts/run-local-pipeline.sh
```

The script should detect that `./data/products` does not exist on AWS and fall back to the backend Docker volume:

```text
Host DataDir does not exist: ./data/products
Using backend Docker volume instead.
DataDir: /app/data/products
```

That is expected and correct on AWS.

## Sync Uploaded AWS Products Down To Windows

Only use this if you actually want the files copied to your PC. It is not required for the AWS-with-local-LM-Studio workflow above.

Run this in local Windows PowerShell:

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

The local copy lands here:

```text
C:\Users\jedre\Desktop\snn\data\server-products
```

## New Windows PC: Publish Approved AWS Items Locally

Use this when the item was already generated and approved in Boss Review, and the new PC only needs the photos plus cached listing data for local browser publishing.

Run this in local Windows PowerShell, from the repo folder:

```powershell
cd C:\Users\jedre\Desktop\snn
.\scripts\sync-and-publish-ready.ps1 -Marketplaces facebook -InstallBrowsers
```

After Playwright Chromium has already been installed once:

```powershell
.\scripts\sync-and-publish-ready.ps1 -Marketplaces facebook
```

To log in to Facebook without syncing or posting:

```powershell
.\scripts\sync-and-publish-ready.ps1 -AuthMode -Marketplaces facebook
```

This syncs:

```text
AWS /app/data/ready_to_publish -> local .\data\ready_to_publish
```

It does not run generation. If any approved item has no `listing_plan.json`, the script stops instead of calling the model.
After publishing, the local runner prints an `x/x item(s) published` summary. Type the number before `/` to confirm the count.

## What Worked

- AWS app in Docker for uploads, Boss Review, deletes, downloads, approvals, and shared access.
- Local LM Studio serving the model on Windows.
- SSH reverse tunnel from Windows to AWS:

```text
AWS 127.0.0.1:1234 -> Windows 127.0.0.1:1234
```

- Running generation from AWS with:

```bash
MODE=dry_run MARKETPLACES="facebook" ./scripts/run-local-pipeline.sh
```

- Letting the script use `/app/data/products` from the backend Docker volume.
- Rebuilding containers after Python/frontend changes.

## What Did Not Work

Running a PowerShell script on Ubuntu:

```bash
sudo ./run-local-pipeline.ps1 -Mode publish -Marketplaces facebook
```

This fails because `.ps1` is not a bash script:

```text
Syntax error: newline unexpected
```

Use the bash script on AWS:

```bash
./scripts/run-local-pipeline.sh
```

Running the script without execute permission:

```bash
./run-local-pipeline.sh
```

If it says `Permission denied`, fix it:

```bash
cd /opt/vnd
chmod +x scripts/run-local-pipeline.sh
```

Calling the script by name without `./`:

```bash
run-local-pipeline.sh
```

This fails because the current directory is usually not in `$PATH`. Use:

```bash
./scripts/run-local-pipeline.sh
```

Pointing AWS host bash at `/app/data/products` directly:

```bash
./scripts/run-local-pipeline.sh -DataDir /app/data/products
```

That path exists inside the backend container, not on the AWS host. The script now handles this by falling back to the backend Docker volume when `./data/products` does not exist.

Relying on stale containers after `git pull`:

```bash
git pull
docker compose up -d
```

This can leave old code running. After frontend/backend code changes, rebuild:

```bash
docker compose build backend frontend
docker compose up -d --force-recreate backend frontend
```

Using old backend images with newer CLI flags:

```text
cli.py: error: unrecognized arguments: --use-cached-listings
```

Fix by pulling the latest code and rebuilding the backend image:

```bash
cd /opt/vnd
git pull
docker compose build backend
docker compose up -d --force-recreate backend
```

Or run the pipeline with:

```bash
REBUILD=1 MODE=dry_run MARKETPLACES="facebook" ./scripts/run-local-pipeline.sh
```

## Rotation 404 Fix

If the browser still shows this:

```text
Rotation failed: 404 Client Error: Not Found for url: http://backend:8000/products/.../files/image0.jpeg/rotate
```

The server is probably still running an old frontend container. Rebuild and recreate both frontend and backend:

```bash
cd /opt/vnd
git pull
docker compose build backend frontend
docker compose up -d --force-recreate backend frontend
```

The newer route sends the filename in JSON to the rotate endpoint instead of putting the filename in the URL path.

## Daily Data Backup

The app can email a daily zip backup to the admin. Configure this in `/opt/vnd/.env` on AWS:

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

Restart backend after editing `.env`:

```bash
cd /opt/vnd
docker compose up -d --force-recreate backend
```

## WinSCP To AWS

Use:

```text
Host: 51.102.104.11
User: ubuntu
Auth: private key C:\Users\jedre\.ssh\vnd_aws
Password: none, use the SSH key passphrase if prompted
Remote path: /opt/vnd
```

Remember that uploaded photos are in a Docker volume, not directly visible as normal files under `/opt/vnd/data`.

## Quick Recovery Checklist

If AWS generation is not working:

1. On Windows, confirm LM Studio server is running on port `1234`.
2. On Windows, open the tunnel and keep it open:

```powershell
cd C:\Users\jedre\Desktop\snn
.\scripts\open-lmstudio-aws-tunnel.ps1
```

3. On AWS, test the tunnel:

```bash
curl http://127.0.0.1:1234/v1/models
```

4. On AWS, pull and rebuild if code changed:

```bash
cd /opt/vnd
git pull
REBUILD=1 MODE=dry_run MARKETPLACES="facebook" ./scripts/run-local-pipeline.sh -Recalculate
```

5. Watch logs if needed:

```bash
cd /opt/vnd
docker compose logs -f backend
```

## Recommendation For Sharing The Project

For another very novice developer, package the project like this:

- Keep Docker Compose as the AWS/deployment path.
- Add a one-command Windows setup script.
- Add a one-command Windows start script.
- Keep `README.md` short and task-based.
- Keep this file as the deeper troubleshooting runbook.
- Do not require WSL.
- Do not require the novice dev to understand Docker volumes before they can run the app.

The best plug-and-play shape is:

```powershell
git clone <repo-url>
cd snn
.\scripts\setup-windows-dev.ps1
.\scripts\start-windows-dev.ps1
```

Then for AWS/local LM Studio generation:

```powershell
.\scripts\open-lmstudio-aws-tunnel.ps1
```

And on AWS:

```bash
cd /opt/vnd
MODE=dry_run MARKETPLACES="facebook" ./scripts/run-local-pipeline.sh
```
