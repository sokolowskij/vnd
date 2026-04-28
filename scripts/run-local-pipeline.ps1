<#
Runs local listing generation and optional publishing.

Examples:
  .\scripts\run-local-pipeline.ps1
  .\scripts\run-local-pipeline.ps1 -Mode dry_run -DataDir .\data\products
  .\scripts\run-local-pipeline.ps1 -Mode publish -DataDir .\data\ready_to_publish
  .\scripts\run-local-pipeline.ps1 -Mode publish -Marketplaces facebook
  .\scripts\run-local-pipeline.ps1 -Mode publish -Marketplaces facebook -Recalculate
  .\scripts\run-local-pipeline.ps1 -Mode publish -Marketplaces olx,facebook -Yes
  .\scripts\run-local-pipeline.ps1 -AuthMode -Marketplaces facebook

Notes:
  - By default, existing listing_plan.json files are reused as cached data.
  - Use -Recalculate to regenerate listing_plan.json before posting.
  - dry_run writes post_results.json without submitting listings.
  - publish opens/uses marketplace browser automation and may post real listings.
  - AuthMode opens marketplace browser profiles for login only and does not post.
  - publish asks for a final published-count confirmation after browser flows complete.
  - Configure .env first. For LM Studio, keep the local server running.
#>

[CmdletBinding()]
param(
    [string]$DataDir = "",
    [ValidateSet("dry_run", "publish")]
    [string]$Mode = "dry_run",
    [string[]]$Marketplaces = @("olx", "facebook"),
    [switch]$Recalculate,
    [switch]$Yes,
    [switch]$InstallBrowsers,
    [switch]$AuthMode
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if (-not (Test-Path ".env")) {
    throw "Missing .env in $RepoRoot. Create it from .env.example and configure it first."
}

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

if ($InstallBrowsers) {
    & $Python -m playwright install chromium
}

if ($Mode -eq "publish" -and -not $Yes -and -not $AuthMode) {
    Write-Host "Publish mode may create real marketplace listings."
    $answer = Read-Host "Type PUBLISH to continue"
    if ($answer -ne "PUBLISH") {
        Write-Host "Cancelled."
        exit 1
    }
}

if (-not $DataDir) {
    if ($AuthMode) {
        $DataDir = "."
    } elseif ($Mode -eq "publish") {
        $DataDir = ".\data\ready_to_publish"
    } else {
        $DataDir = ".\data\products"
    }
}

$ResolvedDataDir = (Resolve-Path -Path $DataDir).Path
$env:PYTHONPATH = Join-Path $RepoRoot "src"
if (-not $env:USER_DATA_DIR -or $env:USER_DATA_DIR -eq "/app/data/browser_profiles") {
    $env:USER_DATA_DIR = Join-Path $RepoRoot "browser_profiles"
}

Write-Host "Running Agentic Seller pipeline"
Write-Host "DataDir:      $ResolvedDataDir"
Write-Host "Mode:         $Mode"
Write-Host "Marketplaces: $($Marketplaces -join ', ')"
Write-Host "UserDataDir:  $env:USER_DATA_DIR"
Write-Host "Listings:     $(if ($Recalculate) { 'recalculate' } else { 'use cached when available' })"

$CliArgs = @(
    "-m",
    "agentic_seller.cli",
    "--data-dir",
    $ResolvedDataDir,
    "--mode",
    $Mode,
    "--marketplaces"
) + $Marketplaces

if (-not $Recalculate) {
    $CliArgs += "--use-cached-listings"
}

if ($AuthMode) {
    $CliArgs += "--auth-mode"
}

& $Python @CliArgs

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
