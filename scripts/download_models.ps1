$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "=== PoseReferenceForge Model Downloader ===" -ForegroundColor Cyan
Write-Host ""

$modelsDir = "$RepoRoot\models"
New-Item -ItemType Directory -Path $modelsDir -Force | Out-Null

# Model manifest
$models = @(
    @{
        Name = "yolov8n-pose.pt"
        Url = "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n-pose.pt"
        Path = "$modelsDir\yolov8n-pose.pt"
    },
    @{
        Name = "yolov8s-pose.pt"
        Url = "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8s-pose.pt"
        Path = "$modelsDir\yolov8s-pose.pt"
    }
)

foreach ($model in $models) {
    $modelPath = $model.Path
    if (Test-Path $modelPath) {
        Write-Host "  [SKIP] $($model.Name) already exists" -ForegroundColor Yellow
        continue
    }
    Write-Host "  Downloading $($model.Name)..."
    try {
        Invoke-WebRequest -Uri $model.Url -OutFile $modelPath -UseBasicParsing
        Write-Host "  [OK] $($model.Name)" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] $($model.Name): $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== Model Download Complete ===" -ForegroundColor Cyan
