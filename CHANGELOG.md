# Changelog

## [1.0.0-dev] — 2026-07-15

### Added
- Complete application structure with PySide6 UI framework
- Person detection and 2D pose detection via YOLOv8-pose
- 2D skeleton overlay with interactive joint editing
- 3D pose lifting from 2D landmarks with depth heuristics
- Interactive 3D viewport with orbit/pan/zoom controls
- Blender-based mannequin rendering (procedural geometry)
- Project persistence (save/load JSON format)
- Export profiles (source-matched, transparent, depth-readable)
- Preflight validation system
- Unit test suite (23 tests)
- Integration test suite (3 tests)
- Camera estimation from pose data
- Application settings with persistent storage
- Environment audit and verification scripts
- Model download and setup automation
- Complete documentation (architecture, user guide, troubleshooting, etc.)
- 26 tests all passing
- End-to-end pipeline verified with real images

### Technical
- Repository: `C:\Users\gewoo\New folder (124)`
- Python 3.12.10, PySide6 6.11.1, PyTorch 2.11.0+cu128
- Blender 5.1.2 integration for final rendering
- YOLOv8n-pose model for detection (7 MB)
