param(
    [string]$OutputDir = "dist",
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "=== PoseReferenceForge Local Build ===" -ForegroundColor Cyan

# Step 1: Run tests
if (-not $SkipTests) {
    Write-Host "Running tests..." -ForegroundColor Yellow
    .\.venv\Scripts\python.exe -m pytest tests/ -v --tb=short
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Tests failed. Fix before building."
        exit 1
    }
    Write-Host "All tests passed." -ForegroundColor Green
}

# Step 2: Ensure output dir
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

Write-Host ""
Write-Host "=== Build Complete ===" -ForegroundColor Cyan
Write-Host "Output: $OutputDir"
