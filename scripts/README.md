# Operations Commands

Short command reference for updating AWS, managing the deployed app, and running local listing generation.

## Local PowerShell

Run from your Windows machine:

```powershell
cd C:\Users\jedre\Desktop\snn
git status
git push
```

Connect to AWS:

```powershell
ssh -i $env:USERPROFILE\.ssh\vnd_aws ubuntu@51.102.104.11
```

Copy scripts manually if Git is not available on the server:

```powershell
scp -i $env:USERPROFILE\.ssh\vnd_aws .\scripts\aws-reload-frontend.sh .\scripts\aws-start.sh .\scripts\aws-stop.sh ubuntu@51.102.104.11:/tmp/
```

## AWS Server

Run after SSH connects:

```bash
cd /opt/vnd
git pull
chmod +x scripts/aws-*.sh
```

Reload only the frontend after UI changes:

```bash
./scripts/aws-reload-frontend.sh
```

Start the full app:

```bash
./scripts/aws-start.sh
```

Stop the app without deleting product/review data:

```bash
./scripts/aws-stop.sh
```

Run with production compose override:

```bash
USE_PROD_COMPOSE=1 ./scripts/aws-start.sh
USE_PROD_COMPOSE=1 ./scripts/aws-reload-frontend.sh
USE_PROD_COMPOSE=1 ./scripts/aws-stop.sh
```

Check containers and logs:

```bash
docker compose ps
docker compose logs -f
docker compose logs -f frontend
docker compose logs -f backend
```

## Local Generation And Publishing

Use cached listing plans when available, then write dry-run posting results:

```powershell
.\scripts\run-local-pipeline.ps1 -Mode dry_run
```

Force recalculation of descriptions and listing plans:

```powershell
.\scripts\run-local-pipeline.ps1 -Mode dry_run -Recalculate
```

Publish for real using cached listing plans when available:

```powershell
.\scripts\run-local-pipeline.ps1 -Mode publish -Marketplaces facebook
```

Publish for real after recalculating listing plans:

```powershell
.\scripts\run-local-pipeline.ps1 -Mode publish -Marketplaces facebook -Recalculate
```

Skip the publish confirmation prompt:

```powershell
.\scripts\run-local-pipeline.ps1 -Mode publish -Marketplaces olx,facebook -Yes
```

Install Playwright Chromium before running browser automation:

```powershell
.\scripts\run-local-pipeline.ps1 -Mode dry_run -InstallBrowsers
```
