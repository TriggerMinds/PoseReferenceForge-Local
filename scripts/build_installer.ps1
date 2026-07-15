param(
    [switch]$SkipTests,
    [switch]$InnoSetup
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "=== PoseReferenceForge Local Build ===" -ForegroundColor Cyan

if (-not $SkipTests) {
    Write-Host "Running tests..." -ForegroundColor Yellow
    .\.venv\Scripts\python.exe -m pytest tests/ -v --tb=short
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Tests failed. Fix before building."
        exit 1
    }
    Write-Host "All tests passed." -ForegroundColor Green
}

# Build PyInstaller executable
Write-Host "Building PyInstaller executable..." -ForegroundColor Yellow
.\.venv\Scripts\python.exe scripts/build_pyinstaller.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller build failed."
    exit 1
}

$exePath = "$RepoRoot\dist\PoseReferenceForge.exe"
if (Test-Path $exePath) {
    $sizeMB = [math]::Round((Get-Item $exePath).Length / 1MB, 1)
    Write-Host "Executable: $exePath ($sizeMB MB)" -ForegroundColor Green
}

# Build Inno Setup installer if available
if ($InnoSetup) {
    $iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    if (Test-Path $iscc) {
        Write-Host "Building Inno Setup installer..." -ForegroundColor Yellow
        & $iscc "$RepoRoot\scripts\installer.iss"
        Write-Host "Installer built." -ForegroundColor Green
    } else {
        Write-Warning "Inno Setup not found at $iscc. Skipping installer."
    }
}

# Create portable zip
Write-Host "Creating portable zip..." -ForegroundColor Yellow
$zipPath = "$RepoRoot\dist\PoseReferenceForge_Portable.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath }
Add-Type -AssemblyName System.IO.Compression.FileSystem
$compress = [System.IO.Compression.ZipFile]::CreateFromDirectory("$RepoRoot\dist", $zipPath, [System.IO.Compression.CompressionLevel]::Optimal, $false)
Write-Host "Portable zip: $zipPath" -ForegroundColor Green

Write-Host ""
Write-Host "=== Build Complete ===" -ForegroundColor Cyan
