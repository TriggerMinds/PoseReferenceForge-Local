# Implementation Plan

## Phase 0: Environment Audit (COMPLETE)
- [x] Inspect hardware and OS
- [x] Locate Python, CUDA, Blender
- [x] Initialize repository and structure
- [x] Create documentation
- [x] Install dependencies

## Phase 1: Model & Architecture Validation (CURRENT)
- [ ] Test YOLOv8 pose detection
- [ ] Test MediaPipe pose detection
- [ ] Test ONNX runtime compatibility
- [ ] Evaluate 3D viewport approach (pygfx / QOpenGLWidget)
- [ ] Test Blender automated rendering
- [ ] Document architecture
- [ ] Create MODEL_EVALUATION.md
- [ ] Create VIEWPORT_DECISION.md
- [ ] Create DEPENDENCY_PLAN.md

## Phase 2: Production Vertical Pipeline
- [ ] Image import and validation
- [ ] Person detection with bounding boxes
- [ ] 2D pose detection (YOLO + MediaPipe fallback)
- [ ] 2D skeleton overlay and editing
- [ ] Pose schema and data models
- [ ] Confidence scoring
- [ ] JSON data export
- [ ] Unit tests for detection pipeline

## Phase 3: 3D Pose Core
- [ ] Monocular 3D pose initialization
- [ ] IK fitting with anatomical constraints
- [ ] Mannequin rig creation/loading
- [ ] Rig mapping
- [ ] Source-camera estimation
- [ ] First Blender render
- [ ] Integration tests

## Phase 4: Production Viewport
- [ ] 3D viewport with mannequin display
- [ ] Orbit/pan/zoom controls
- [ ] Joint selection and highlight
- [ ] FK rotation gizmo
- [ ] IK target manipulation
- [ ] Depth correction controls
- [ ] Joint lock/unlock
- [ ] Undo/redo
- [ ] Camera match overlay

## Phase 5: Production Desktop UI
- [ ] Main window layout
- [ ] Project management (new, open, save)
- [ ] Image import dialog
- [ ] Person selection
- [ ] 2D joint editor panel
- [ ] 3D viewport panel
- [ ] Properties panel
- [ ] Progress and cancellation
- [ ] Error dialogs and recovery
- [ ] Settings dialog
- [ ] Diagnostics screen
- [ ] Pose library UI

## Phase 6: Reference Output System
- [ ] Render profiles
- [ ] Source-matched clean render
- [ ] Transparent PNG render
- [ ] Depth-readable render
- [ ] Silhouette render
- [ ] Structural render
- [ ] Multi-view render
- [ ] Export packs (1/2/3 image)
- [ ] Full reference pack
- [ ] Render manifests
- [ ] Quality reports

## Phase 7: Quality & Preflight
- [ ] Pose similarity metrics
- [ ] Readability analysis
- [ ] Export preflight checks
- [ ] Preflight blocking and overrides
- [ ] Report generation

## Phase 8: Hardening
- [ ] Error recovery for all failure modes
- [ ] CPU fallback path
- [ ] Cache management
- [ ] Privacy and security review
- [ ] Structured logging
- [ ] Performance optimization
- [ ] Asset license verification
- [ ] Model checksum verification
- [ ] Schema migration

## Phase 9: Packaging
- [ ] PyInstaller build
- [ ] Windows installer (Inno Setup)
- [ ] Start Menu shortcut
- [ ] Uninstall support
- [ ] Blender detection
- [ ] Clean installation test

## Phase 10: Final Acceptance
- [ ] Complete test suite execution
- [ ] Performance measurement
- [ ] Release checklist
- [ ] Known limitations documentation
- [ ] Final acceptance report
