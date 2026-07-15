param(
    [string]$PythonPath = "C:\Users\gewoo\AppData\Local\Programs\Python\Python312\python.exe"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "=== PoseReferenceForge Local Setup ===" -ForegroundColor Cyan
Write-Host ""

# Check Python
if (-not (Test-Path $PythonPath)) {
    Write-Error "Python not found at $PythonPath. Please install Python 3.12.10"
    exit 1
}
Write-Host "Python: $PythonPath" -ForegroundColor Green

# Create venv
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    & $PythonPath -m venv .venv
}
$pip = "$RepoRoot\.venv\Scripts\pip.exe"
$python = "$RepoRoot\.venv\Scripts\python.exe"

# Install dependencies
Write-Host "Installing dependencies..."
& $pip install --upgrade pip
& $pip install -r requirements.txt

Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Cyan
Write-Host "Run START.bat or '.venv\Scripts\python.exe -m app.main' to launch"
