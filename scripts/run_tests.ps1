$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "=== Running PoseReferenceForge Tests ===" -ForegroundColor Cyan

.\.venv\Scripts\python.exe -m pytest tests/ -v --tb=long --cov=app --cov-report=term

if ($LASTEXITCODE -eq 0) {
    Write-Host "All tests passed!" -ForegroundColor Green
} else {
    Write-Host "Some tests failed." -ForegroundColor Red
    exit 1
}
