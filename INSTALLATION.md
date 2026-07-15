# Installation

## Prerequisites

- Windows 11 64-bit
- NVIDIA GPU with 8+ GB VRAM (recommended, CPU fallback available)
- Blender 5.1+

## Quick Install

1. Clone or download PoseReferenceForge Local
2. Run `scripts\setup_windows.ps1` to create venv and install dependencies
3. Run `scripts\download_models.ps1` to download the YOLO pose model
4. Run `START.bat` to launch the application

## Manual Setup

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
```

## Model Setup

The YOLO pose model is required. Download it:
- `models\yolov8n-pose.pt` (7 MB)

## Blender Configuration

Blender 5.1+ must be installed. The application auto-detects it at:
- `C:\Program Files\Blender Foundation\Blender 5.1\blender.exe`

Configure a different path in Settings if needed.
