# Performance Report

## Hardware

| Component | Specification |
|---|---|
| CPU | Intel Core i9-9900K @ 3.60 GHz (8C/16T) |
| RAM | 32 GB DDR4 |
| GPU | NVIDIA GeForce RTX 2060 SUPER (8 GB VRAM) |
| Storage | Samsung SSD (NVMe) |
| OS | Windows 11 Pro x64 |

## Measured Performance

| Operation | Time | GPU | VRAM |
|---|---|---|---|
| Cold start | ~3s | — | — |
| Image load (1920x1080) | ~0.1s | — | — |
| YOLOv8n-pose detection (GPU) | ~1.6s | RTX 2060 SUPER | ~300 MB |
| 3D pose lifting | ~0.01s | — | — |
| Blender render (1024x1536) | ~8s | RTX 2060 SUPER | ~500 MB |
| Blender render (1536x2048) | ~15s | RTX 2060 SUPER | ~800 MB |
| Blender render (2048x3072) | ~30s | RTX 2060 SUPER | ~1.2 GB |
| Project save/load | ~0.1s | — | — |
| Full pipeline (detect → 3D → render 1024) | ~10s | RTX 2060 SUPER | ~800 MB |
| Full pipeline (detect → 3D → render 1536) | ~18s | RTX 2060 SUPER | ~1.1 GB |

## Observations

- VRAM usage stays well within 8 GB limit
- CPU usage during GPU inference is minimal
- Blender rendering is the bottleneck
- No memory leaks observed during extended use
- Performance is adequate for daily production workflow
