# New PC Local Workflow

This guide is for a fresh Windows PC that should do the whole workflow locally:

1. download uploaded photos from AWS,
2. generate listing descriptions locally with LM Studio,
3. upload the generated `listing_plan.json` data back to AWS,
4. let the boss approve items in the AWS app,
5. download approved items back to the PC,
6. publish from the local browser.

You do not need the LM Studio AWS tunnel for this workflow. The tunnel is only for the opposite setup: photos stay on AWS, but AWS calls LM Studio on your PC.

Use PowerShell when possible. If your prompt looks like `C:\Users\barte>`, use the CMD section instead.

## Before You Start

On the new PC you need:

- repo folder: `C:\Users\barte\Desktop\snn`
- SSH key: `C:\Users\barte\.ssh\vnd_aws`
- AWS public key access already working
- LM Studio installed, model loaded, local server enabled on port `1234`
- internet access

Test AWS SSH first:

```cmd
ssh -i "%USERPROFILE%\.ssh\vnd_aws" -o IdentitiesOnly=yes ubuntu@51.102.104.11
```

If this says `Connection timed out`, AWS/security group/network is blocking port `22`.
If this says `Permission denied (publickey)`, the key is not trusted by AWS yet.
If it logs in, type `exit` and continue.

## PowerShell

PowerShell prompt usually starts with `PS`.

### 1. Go To The Project

```powershell
cd C:\Users\barte\Desktop\snn
```

This puts the terminal inside the project folder.

### 2. Set Up Python

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

What this does:

- creates the local Python environment,
- installs the project packages,
- installs the browser engine used by publishing automation,
- creates `.env` if it does not exist,
- opens `.env` so you can check settings.

For LM Studio, `.env` should contain:

```env
LOCAL_MODEL_API=http://localhost:1234/v1
OPENAI_API_KEY=local-model
OPENAI_MODEL=google/gemma-4-e4b
USER_DATA_DIR=browser_profiles
```

### 3. Download Uploaded Photos From AWS

```powershell
$Key = "$env:USERPROFILE\.ssh\vnd_aws"
$Server = "ubuntu@51.102.104.11"
$Compose = "docker compose"

ssh -i $Key $Server "cd /opt/vnd && $Compose exec -T backend tar -C /app/data/products -czf /tmp/products.tgz . && $Compose cp backend:/tmp/products.tgz /tmp/products.tgz && ls -lh /tmp/products.tgz"
scp -i $Key "${Server}:/tmp/products.tgz" .\server-products.tgz

Remove-Item -Recurse -Force .\data\server-products -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force .\data\server-products
tar -xzf .\server-products.tgz -C .\data\server-products
```

What this does:

- asks AWS to pack all uploaded products/photos into `products.tgz`,
- downloads that archive to your PC,
- extracts it into `.\data\server-products`.

If AWS uses the production compose file, change only this line:

```powershell
$Compose = "docker compose -f docker-compose.yml -f docker-compose.prod.yml"
```

### 4. Generate Descriptions Locally

Start LM Studio first. Enable the local server on port `1234`.

Then run:

```powershell
.\scripts\run-local-pipeline.ps1 -DataDir .\data\server-products -Mode dry_run -Marketplaces facebook -Recalculate
```

What this does:

- reads photos and item facts from `.\data\server-products`,
- calls LM Studio on this PC,
- creates or replaces `listing_plan.json`,
- writes `post_results.json`,
- does not publish anything.

Useful options:

```powershell
.\scripts\run-local-pipeline.ps1 -DataDir .\data\server-products -Mode dry_run -Marketplaces facebook
```

Uses existing `listing_plan.json` files when they already exist.

```powershell
.\scripts\run-local-pipeline.ps1 -DataDir .\data\server-products -Mode dry_run -Marketplaces olx,facebook -Recalculate
```

Generates for OLX and Facebook.

### 5. Upload Generated Descriptions Back To AWS

```powershell
tar -czf .\server-products-processed.tgz -C .\data\server-products .
scp -i $Key .\server-products-processed.tgz "${Server}:/tmp/server-products-processed.tgz"
ssh -i $Key $Server "cd /opt/vnd && $Compose cp /tmp/server-products-processed.tgz backend:/tmp/server-products-processed.tgz && $Compose exec -T backend tar -xzf /tmp/server-products-processed.tgz -C /app/data/products"
```

What this does:

- packs your locally generated files,
- sends them to AWS,
- extracts them back into `/app/data/products`,
- makes Boss Review able to see the generated descriptions.

Now open the AWS app, refresh Boss Review, review the generated items, and approve the good ones.

### 6. Download Approved Items And Publish Locally

Use this after items were approved in the AWS app:

```powershell
.\scripts\sync-and-publish-ready.ps1 -Marketplaces facebook -InstallBrowsers
```

What this does:

- downloads `/app/data/ready_to_publish` from AWS,
- extracts photos and `listing_plan.json` files into `.\data\ready_to_publish`,
- starts local browser publishing using cached generated data.

After Playwright was installed once, this shorter command is enough:

```powershell
.\scripts\sync-and-publish-ready.ps1 -Marketplaces facebook
```

Log in to Facebook only, without syncing or publishing:

```powershell
.\scripts\sync-and-publish-ready.ps1 -AuthMode -Marketplaces facebook
```

Publish and let the script try to click the final Publish button:

```powershell
.\scripts\sync-and-publish-ready.ps1 -Marketplaces facebook -AutoPublish -PublishingEmail you@example.com
```

Other useful options:

```powershell
.\scripts\sync-and-publish-ready.ps1 -Marketplaces olx,facebook
.\scripts\sync-and-publish-ready.ps1 -Marketplaces facebook -Yes
.\scripts\sync-and-publish-ready.ps1 -Marketplaces facebook -SkipDependencyInstall
.\scripts\sync-and-publish-ready.ps1 -Marketplaces facebook -KeepArchive
.\scripts\sync-and-publish-ready.ps1 -Marketplaces facebook -UseProdCompose
.\scripts\sync-and-publish-ready.ps1 -Marketplaces facebook -PublishLocation "Warsaw, Poland"
```

Meaning:

- `-Marketplaces facebook`: publish to Facebook only.
- `-Marketplaces olx,facebook`: publish to OLX and Facebook.
- `-Yes`: skip the first publish warning prompt.
- `-AutoPublish`: try to click final marketplace publish buttons automatically.
- `-PublishingEmail`: email filled into marketplace forms.
- `-PublishLocation`: city/location filled into marketplace forms, default is `Warsaw, Poland`.
- `-SkipDependencyInstall`: do not run `pip install`.
- `-KeepArchive`: keep the downloaded archive file.
- `-UseProdCompose`: use `docker-compose.prod.yml` on AWS.
- `-AuthMode`: open browser login profiles only.

## CMD

CMD prompt usually looks like `C:\Users\barte>`.

CMD does not understand `$env:USERPROFILE`. CMD uses `%USERPROFILE%`.

### 1. Go To The Project

```cmd
cd /d C:\Users\barte\Desktop\snn
```

This puts the terminal inside the project folder.

### 2. Set Up Python

```cmd
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
if not exist .env copy .env.example .env
notepad .env
```

For LM Studio, `.env` should contain:

```env
LOCAL_MODEL_API=http://localhost:1234/v1
OPENAI_API_KEY=local-model
OPENAI_MODEL=google/gemma-4-e4b
USER_DATA_DIR=browser_profiles
```

### 3. Download Uploaded Photos From AWS

```cmd
set "KEY=%USERPROFILE%\.ssh\vnd_aws"
set "SERVER=ubuntu@51.102.104.11"
set "COMPOSE=docker compose"

ssh -i "%KEY%" %SERVER% "cd /opt/vnd && %COMPOSE% exec -T backend tar -C /app/data/products -czf /tmp/products.tgz . && %COMPOSE% cp backend:/tmp/products.tgz /tmp/products.tgz && ls -lh /tmp/products.tgz"
scp -i "%KEY%" %SERVER%:/tmp/products.tgz server-products.tgz

if exist data\server-products rmdir /s /q data\server-products
mkdir data\server-products
tar -xzf server-products.tgz -C data\server-products
```

If AWS uses the production compose file, change only this line:

```cmd
set "COMPOSE=docker compose -f docker-compose.yml -f docker-compose.prod.yml"
```

### 4. Generate Descriptions Locally

Start LM Studio first. Enable the local server on port `1234`.

```cmd
powershell -ExecutionPolicy Bypass -File ".\scripts\run-local-pipeline.ps1" -DataDir ".\data\server-products" -Mode dry_run -Marketplaces facebook -Recalculate
```

This reads local photos, calls local LM Studio, and writes generated `listing_plan.json` files. It does not publish anything.

Useful options:

```cmd
powershell -ExecutionPolicy Bypass -File ".\scripts\run-local-pipeline.ps1" -DataDir ".\data\server-products" -Mode dry_run -Marketplaces facebook
powershell -ExecutionPolicy Bypass -File ".\scripts\run-local-pipeline.ps1" -DataDir ".\data\server-products" -Mode dry_run -Marketplaces olx,facebook -Recalculate
```

### 5. Upload Generated Descriptions Back To AWS

```cmd
tar -czf server-products-processed.tgz -C data\server-products .
scp -i "%KEY%" server-products-processed.tgz %SERVER%:/tmp/server-products-processed.tgz
ssh -i "%KEY%" %SERVER% "cd /opt/vnd && %COMPOSE% cp /tmp/server-products-processed.tgz backend:/tmp/server-products-processed.tgz && %COMPOSE% exec -T backend tar -xzf /tmp/server-products-processed.tgz -C /app/data/products"
```

This sends the generated local data back to AWS. Then refresh Boss Review in the AWS app and approve the items.

### 6. Download Approved Items And Publish Locally

```cmd
powershell -ExecutionPolicy Bypass -File ".\scripts\sync-and-publish-ready.ps1" -Marketplaces facebook -InstallBrowsers
```

After Playwright was installed once:

```cmd
powershell -ExecutionPolicy Bypass -File ".\scripts\sync-and-publish-ready.ps1" -Marketplaces facebook
```

Log in to Facebook only:

```cmd
powershell -ExecutionPolicy Bypass -File ".\scripts\sync-and-publish-ready.ps1" -AuthMode -Marketplaces facebook
```

Auto-publish:

```cmd
powershell -ExecutionPolicy Bypass -File ".\scripts\sync-and-publish-ready.ps1" -Marketplaces facebook -AutoPublish -PublishingEmail you@example.com
```

Other useful options:

```cmd
powershell -ExecutionPolicy Bypass -File ".\scripts\sync-and-publish-ready.ps1" -Marketplaces olx,facebook
powershell -ExecutionPolicy Bypass -File ".\scripts\sync-and-publish-ready.ps1" -Marketplaces facebook -Yes
powershell -ExecutionPolicy Bypass -File ".\scripts\sync-and-publish-ready.ps1" -Marketplaces facebook -SkipDependencyInstall
powershell -ExecutionPolicy Bypass -File ".\scripts\sync-and-publish-ready.ps1" -Marketplaces facebook -KeepArchive
powershell -ExecutionPolicy Bypass -File ".\scripts\sync-and-publish-ready.ps1" -Marketplaces facebook -UseProdCompose
powershell -ExecutionPolicy Bypass -File ".\scripts\sync-and-publish-ready.ps1" -Marketplaces facebook -PublishLocation "Warsaw, Poland"
```

## Quick Decision Table

Use this when you are unsure what to run:

| Goal | Command |
| --- | --- |
| Download raw uploaded photos | section `Download Uploaded Photos From AWS` |
| Generate descriptions locally | section `Generate Descriptions Locally` |
| Upload generated descriptions to AWS | section `Upload Generated Descriptions Back To AWS` |
| Boss approves items | use the AWS app in the browser |
| Download approved items and publish | section `Download Approved Items And Publish Locally` |
| Only log in to Facebook browser profile | use `-AuthMode` |
| Publish without final manual click | use `-AutoPublish` |

## Common Errors

`$env:USERPROFILE` does not work:

- You are in CMD. Use `%USERPROFILE%`.

`%USERPROFILE%` does not work:

- You are in PowerShell. Use `$env:USERPROFILE`.

`Connection timed out`:

- AWS port `22` is not reachable from this network. Check EC2 security group.

`Permission denied (publickey)`:

- The SSH key file exists, but AWS does not trust it. Add the `.pub` key to `/home/ubuntu/.ssh/authorized_keys`.

LM Studio connection fails:

- Start LM Studio.
- Load the model.
- Enable the local server.
- Confirm it listens on `http://localhost:1234/v1`.

Boss Review does not show generated descriptions:

- Make sure you ran the upload-back-to-AWS step.
- Refresh the AWS app.
- Check that each product folder has `listing_plan.json`.
