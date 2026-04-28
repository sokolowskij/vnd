<#
Sync approved products from AWS to this Windows PC, then launch local browser publishing.

This script is for a fresh/local publishing machine. It does not generate listing plans.
Every synced product must already contain listing_plan.json, otherwise the script stops.

Examples:
  .\scripts\sync-and-publish-ready.ps1
  .\scripts\sync-and-publish-ready.ps1 -Marketplaces facebook -InstallBrowsers
  .\scripts\sync-and-publish-ready.ps1 -UseProdCompose -Yes
#>

[CmdletBinding()]
param(
    [string]$Key = "$env:USERPROFILE\.ssh\vnd_aws",
    [string]$Server = "ubuntu@51.102.104.11",
    [string]$DeployDir = "/opt/vnd",
    [string]$DataDir = ".\data\ready_to_publish",
    [string[]]$Marketplaces = @("facebook"),
    [switch]$UseProdCompose,
    [switch]$InstallBrowsers,
    [switch]$SkipDependencyInstall,
    [switch]$Yes,
    [switch]$KeepArchive
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if (-not (Test-Path $Key)) {
    throw "SSH key not found: $Key"
}

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Host "Creating local virtual environment..."
    python -m venv .venv
}

if (-not (Test-Path $Python)) {
    throw "Could not find Python in .venv after creating it: $Python"
}

if (-not $SkipDependencyInstall) {
    Write-Host "Installing/updating Python dependencies..."
    & $Python -m pip install -r requirements.txt
}

if ($InstallBrowsers) {
    Write-Host "Installing Playwright Chromium..."
    & $Python -m playwright install chromium
}

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "Created .env from .env.example."
    } else {
        New-Item -ItemType File -Path ".env" | Out-Null
        Write-Host "Created empty .env."
    }
}

$Compose = "docker compose"
if ($UseProdCompose) {
    $Compose = "docker compose -f docker-compose.yml -f docker-compose.prod.yml"
}

$RemoteArchive = "/tmp/ready-to-publish.tgz"
$LocalArchive = Join-Path $RepoRoot "ready-to-publish.tgz"
if ([System.IO.Path]::IsPathRooted($DataDir)) {
    $ResolvedDataDir = [System.IO.Path]::GetFullPath($DataDir)
} else {
    $ResolvedDataDir = [System.IO.Path]::GetFullPath((Join-Path $RepoRoot $DataDir))
}
$RepoRootFull = [System.IO.Path]::GetFullPath($RepoRoot)
if (-not $ResolvedDataDir.StartsWith($RepoRootFull, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to sync outside the repository: $ResolvedDataDir"
}

Write-Host "Syncing approved products from AWS..."
Write-Host "Server:       $Server"
Write-Host "Remote data:  /app/data/ready_to_publish"
Write-Host "Local data:   $ResolvedDataDir"

$RemoteCommand = "cd $DeployDir && $Compose exec -T backend tar -C /app/data/ready_to_publish -czf $RemoteArchive . && $Compose cp backend:$RemoteArchive $RemoteArchive && ls -lh $RemoteArchive"
ssh -i $Key $Server $RemoteCommand

scp -i $Key "${Server}:$RemoteArchive" $LocalArchive

if (Test-Path $ResolvedDataDir) {
    Remove-Item -LiteralPath $ResolvedDataDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $ResolvedDataDir | Out-Null
tar -xzf $LocalArchive -C $ResolvedDataDir

if (-not $KeepArchive) {
    Remove-Item -LiteralPath $LocalArchive -Force
}

$ProductDirs = Get-ChildItem -LiteralPath $ResolvedDataDir -Directory -ErrorAction SilentlyContinue
if (-not $ProductDirs) {
    throw "No approved products were synced from AWS."
}

$MissingListings = @(
    $ProductDirs | Where-Object { -not (Test-Path (Join-Path $_.FullName "listing_plan.json")) }
)
if ($MissingListings.Count -gt 0) {
    $Names = ($MissingListings | ForEach-Object { $_.Name }) -join ", "
    throw "Refusing to publish because these products have no listing_plan.json: $Names. Approve/generate them on the main app first."
}

Write-Host "Synced $($ProductDirs.Count) approved product(s)."
Write-Host "Launching local publish flow with cached listings only."

$PublishArgs = @(
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    ".\scripts\run-local-pipeline.ps1",
    "-Mode",
    "publish",
    "-DataDir",
    $ResolvedDataDir,
    "-Marketplaces"
) + $Marketplaces

if ($Yes) {
    $PublishArgs += "-Yes"
}

& powershell @PublishArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
