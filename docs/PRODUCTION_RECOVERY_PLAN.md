# Production Recovery Plan

Audit date: 2026-07-15
Branch: production-recovery

## Priority Definition

| Priority | Meaning |
|---|---|
| P0 | Blocks usable reference-image generation |
| P1 | Blocks reliable daily use |
| P2 | Improvement but not an immediate blocker |

---

## P0 Defects — Blocks Reference Image Generation

These defects prevent the application from producing its primary deliverable: a clean pose-reference image.

| # | File | Line | Description |
|---|---|---|---|
| P0-1 | `main_window.py` | 258-259 | `_on_export` never checks `dialog.exec()` return value, never reads dialog state, never calls any exporter. The entire export workflow produces **no output**. |
| P0-2 | `dialogs.py` | 90-153 | `ExportDialog` has zero code that reads its own form values. All user selections (profile, format, resolution, pack type) are silently discarded. |
| P0-3 | `blender_renderer.py` | 51 | `render()` calls `self._generate_blender_script()` which does not exist. Will raise `AttributeError`. |
| P0-4 | `blender_renderer.py` | 1-132 | `BlenderRenderer` is never instantiated or called from any workflow. Even if the export dialog were wired, no rendering would occur. |
| P0-5 | `render_profiles.py` | 54-85 | Only 3 of 6 profiles in the UI combo box have corresponding config. Selection of Silhouette, Structural, or Multi-View will cause `KeyError`. |
| P0-6 | `pack_exporter.py` | 1-83 | All functions are orphans. The 4 AI Reference Pack checkboxes in ExportDialog are decorative. No pack export possible. |
| P0-7 | `main_window.py` | 140-158 | 3D pose is **never restored on project open**. pose3d loaded into `_current_data` but never deserialized or sent to viewport. |
| P0-8 | `main_window.py` | 182-184 | On save, only 2D pose is re-read from source panel. 3D corrections, depth adjustments, and camera state are never persisted. |

**P0 Count: 8**

---

## P1 Defects — Blocks Reliable Daily Use

| # | File | Line | Description |
|---|---|---|---|
| P1-1 | `source_panel.py` | 148-161 | Joint dragging corrupts data: no screen-to-image coordinate conversion. Dragging a joint at zoom≠1 sets wrong coordinates. |
| P1-2 | `properties_panel.py` | 23 | `btn_lock.clicked` never connected. Lock button does nothing. |
| P1-3 | `properties_panel.py` | 24 | `btn_reset.clicked` never connected. Reset button does nothing. |
| P1-4 | `properties_panel.py` | 33-35 | `depth_slider.valueChanged` never connected. Slider does nothing. |
| P1-5 | `properties_panel.py` | 49 | `set_joint_info()` never called by any component. All labels permanently show "None". |
| P1-6 | `properties_panel.py` | 63-67 | `add_warning()` / `clear_warnings()` never called. Warnings list always empty. |
| P1-7 | `viewport_3d.py` | 153-177 | No 3D joint picking. User cannot select, rotate, or translate individual joints in the 3D viewport. |
| P1-8 | `camera_estimator.py` | 21 | `estimate_camera()` defined but never called by any code. Camera estimation is dead code. |
| P1-9 | `main_window.py` | 154 | Missing source image on reload produces silent blank panel with no error message. |
| P1-10 | `main_window.py` | 248 | 3D pose corrections made via properties panel are never captured on save — no `viewport_3d.get_pose3d()` exists. |
| P1-11 | `viewport_3d.py` | 12-14 | Camera orbit/pan/zoom state never saved. Viewport resets on every reopen. |
| P1-12 | `source_panel.py` | 14-17 | 2D view state (zoom, pan, skeleton toggle) never saved. Image view resets on every reopen. |

**P1 Count: 12**

---

## P2 Defects — Improvement, Not Immediate Blocker

| # | File | Line | Description |
|---|---|---|---|
| P2-1 | `preflight/validator.py` | 1-62 | Preflight not wired into export workflow. Results never shown to user. |
| P2-2 | `mediapipe_detector.py` | 1-74 | MediaPipe fallback not integrated into detection pipeline. |
| P2-3 | `scripts/build_installer.ps1` | 1-25 | Installer script only runs tests. No actual packaging. No PyInstaller config. |
| P2-4 | `source_panel.py` | 43-47 | Monkey-patched event handlers on QLabel (fragile pattern). |
| P2-5 | `source_panel.py` | 33, 79 | "Fit" button does not fit image to viewport, only resets zoom=1. |
| P2-6 | `project_repository.py` | 37-51 | `joint_id` stored redundantly (key + value field). |
| P2-7 | `project_repository.py` | 130-149 | `create_project_data` is dead code — never called anywhere. |
| P2-8 | `main_window.py` | 267 | `import os` at bottom of file (PEP 8 violation). |
| P2-9 | `main_window.py` | 178 | `updated_at` format mismatch (Qt vs Python ISO format). |
| P2-10 | `library/__init__.py` | 1 | Pose library is an empty package. No database, no CRUD, no UI. |
| P2-11 | `hand_detection` | — | HandDetector interface exists (`base.py:19-22`) but no implementation. |
| P2-12 | `ik_solver` | — | No IK solver at any level. Depth heuristic is documented limitation. |

**P2 Count: 12**

---

## Recovery Phase Plan

### Recovery 02: Export Pipeline
- Wire ExportDialog values to actual exporter
- Fix/remove `BlenderRenderer.render()` broken method
- Wire `render_with_script()` into export workflow
- Complete all 6 render profiles
- Wire preflight into export

### Recovery 03: 3D Editing
- Add 3D joint picking to Viewport3D
- Wire PropertiesPanel signals to actual pose editing
- Add `get_pose3d()` and `get_camera_state()` to Viewport3D
- Persist 3D state on save/restore

### Recovery 04: Source Panel Bug Fix
- Fix coordinate transform in joint drag handlers
- Add proper zoom-to-fit behavior
- Add error feedback for missing source images

### Recovery 05: Camera & MediaPipe
- Wire CameraEstimator into 3D pipeline
- Integrate MediaPipe fallback detector
- Build Camera Match workspace

### Recovery 06: Library & Installer
- Implement pose library (DB schema, CRUD, UI)
- Build PyInstaller packaging
- Create Inno Setup installer script

---

## Recovery Priority Matrix

| Component | P0 | P1 | P2 | Recovery Phase |
|---|---|---|---|---|
| Export workflow | 7 | 0 | 1 | Recovery 02 |
| 3D pose pipeline | 2 | 3 | 0 | Recovery 03 |
| 2D joint editing | 0 | 1 | 2 | Recovery 04 |
| Properties panel | 0 | 5 | 0 | Recovery 03 |
| Viewport | 0 | 1 | 0 | Recovery 03 |
| Camera estimation | 0 | 1 | 0 | Recovery 05 |
| Persistence | 0 | 4 | 0 | Recovery 03 |
| MediaPipe | 0 | 0 | 1 | Recovery 05 |
| Installer | 0 | 0 | 1 | Recovery 06 |
| Pose library | 0 | 0 | 1 | Recovery 06 |
| Preflight | 0 | 0 | 1 | Recovery 02 |
| Hand detection | 0 | 0 | 1 | Recovery 05 |
| IK solver | 0 | 0 | 1 | Recovery 05 |

**Total: 8 P0 + 12 P1 + 12 P2 = 32 defects**
