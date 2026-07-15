$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "Cleaning..."

@("__pycache__", ".pytest_cache", "*.pyc", "*.pyo", "build", "dist", "*.spec") | ForEach-Object {
    Get-ChildItem -Path $RepoRoot -Recurse -Directory -Filter $_ -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
    Get-ChildItem -Path $RepoRoot -Recurse -File -Filter $_ -ErrorAction SilentlyContinue | Remove-Item -Force
}

Write-Host "Clean complete."
