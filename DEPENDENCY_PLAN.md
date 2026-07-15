# Dependency Plan

## Runtime Dependencies

| Dependency | Version | Purpose | License |
|---|---|---|---|
| PySide6 | >=6.8 | Desktop UI framework | LGPL-3.0 |
| numpy | >=2.0 | Numerical computation | BSD-3 |
| opencv-python-headless | >=4.10 | Image processing | MIT |
| Pillow | >=11.0 | Image I/O | Historical |
| scipy | >=1.14 | Optimization | BSD-3 |
| onnxruntime-gpu | >=1.19 | Model inference | MIT |
| torch | >=2.5 | ML framework | BSD-3 |
| torchvision | >=0.20 | Vision models | BSD-3 |
| mediapipe | >=0.10 | Alternative pose detection | Apache-2.0 |
| trimesh | >=4.5 | 3D mesh processing | MIT |
| pyyaml | >=6.0 | YAML config | MIT |
| jsonschema | >=4.23 | Schema validation | MIT |
| requests | >=2.32 | HTTP client | Apache-2.0 |
| filetype | >=1.2 | File type detection | MIT |
| packaging | >=24.0 | Version management | BSD-2 |
| psutil | >=6.0 | System monitoring | BSD-3 |
| PyOpenGL | >=3.1 | 3D viewport rendering | BSD-3 |
| ultralytics | >=8.4 | YOLO pose models | AGPL-3.0 |

## System Dependencies

| Dependency | Purpose |
|---|---|
| Blender 5.1+ | High-quality rendering |
| NVIDIA GPU + CUDA | GPU-accelerated inference |
| Windows 11 64-bit | Target platform |

## Model Dependencies

| Model | File | Size |
|---|---|---|
| YOLOv8n-pose | `models/yolov8n-pose.pt` | 7 MB |
