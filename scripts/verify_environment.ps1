param(
    [string]$PythonPath = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$passed = 0
$failed = 0

function Check {
    param($Name, $Condition, $Help)
    if (& $Condition) {
        Write-Host "  [PASS] $Name" -ForegroundColor Green
        $script:passed++
    } else {
        Write-Host "  [FAIL] $Name" -ForegroundColor Red
        if ($Help) { Write-Host "         $Help" -ForegroundColor Yellow }
        $script:failed++
    }
}

Write-Host "=== PoseReferenceForge Environment Verification ===" -ForegroundColor Cyan
Write-Host ""

# Python
if (-not $PythonPath) {
    $PythonPath = "$RepoRoot\.venv\Scripts\python.exe"
}
Check "Python executable exists" { Test-Path $PythonPath } "Run setup_windows.ps1 or install Python 3.12"

if (Test-Path $PythonPath) {
    Check "Python version 3.12" { & $PythonPath -c "import sys; sys.exit(0 if sys.version_info[:2]==(3,12) else 1)" }
    Check "PyTorch available" { & $PythonPath -c "import torch" 2>$null }
    Check "CUDA available" { & $PythonPath -c "import torch; exit(0 if torch.cuda.is_available() else 1)" 2>$null }
    Check "PySide6 available" { & $PythonPath -c "from PySide6 import QtWidgets" 2>$null }
    Check "OpenCV available" { & $PythonPath -c "import cv2" 2>$null }
    Check "MediaPipe available" { & $PythonPath -c "import mediapipe" 2>$null }
}

# Models
Check "YOLO pose model exists" { Test-Path "$RepoRoot\models\yolov8n-pose.pt" } "Run download_models.ps1"

# Blender
$blenderPaths = @(
    "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe",
    "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"
)
$foundBlender = $false
foreach ($bp in $blenderPaths) {
    if (Test-Path $bp) { $foundBlender = $true; break }
}
Check "Blender installed" { $foundBlender } "Install Blender 5.1 or configure path in Settings"

# Disk
$drive = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"
$freeGB = [math]::Round($drive.FreeSpace/1GB, 1)
Check "Sufficient disk space (>5 GB free)" { $freeGB -gt 5 } "Free space: ${freeGB}GB"

Write-Host ""
Write-Host "Results: $passed passed, $failed failed" -ForegroundColor Cyan
if ($failed -eq 0) {
    Write-Host "Environment is ready." -ForegroundColor Green
} else {
    Write-Host "Please resolve the failures above." -ForegroundColor Yellow
}
exit $failed
