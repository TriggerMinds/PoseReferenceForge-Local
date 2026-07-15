# Feature Evidence Matrix

Audit date: 2026-07-15  
Repository: TriggerMinds/PoseReferenceForge-Local  
Branch: production-recovery  
Commit: abc3679  
Test suite: 26/26 passing  

## Legend

| Status | Meaning |
|---|---|
| WORKING | Real implementation, connected, executable, produces correct output |
| PARTIAL | Has real code but missing connections, incomplete behavior, or has defects |
| STUB | Interface/schema defined, no real implementation |
| DISCONNECTED | Implementation exists but is not wired to any caller |
| NOT_IMPLEMENTED | No code exists for this feature |
| BROKEN | Implementation exists but crashes or produces incorrect output |

---

## 1. Person Detection

| Field | Value |
|---|---|
| Claimed Status | ✅ Phase 2 COMPLETED |
| Actual Status | **WORKING** |
| Implementation Files | `app/detectors/yolo_detector.py:23-43` (YOLOPersonDetector), `app/pose2d/detection_pipeline.py:14-52` |
| UI Connected | Yes — `main_window.py:219` `_on_detect_pose` |
| Automated Test | `tests/integration/test_detection_pipeline.py:30-34` |
| Real Execution Evidence | 4 persons detected on bus.jpg, 2 on zidane.jpg |
| Blocking Defect | None |
| Required Repair | None |

---

## 2. 2D Pose Detection (YOLO)

| Field | Value |
|---|---|
| Claimed Status | ✅ Phase 2 COMPLETED |
| Actual Status | **WORKING** |
| Implementation Files | `app/detectors/yolo_detector.py:47-100` (YOLOPoseDetector), `app/domain/models.py:68-72` (COCO_KEYPOINTS) |
| UI Connected | Yes — same path as person detection |
| Automated Test | `tests/integration/test_detection_pipeline.py:30-34` (joint count > 0) |
| Real Execution Evidence | 17 COCO keypoints + 11 inferred joints on bus.jpg |
| Blocking Defect | None |
| Required Repair | None |

---

## 3. 2D Skeleton Overlay

| Field | Value |
|---|---|
| Claimed Status | ✅ Phase 2 COMPLETED |
| Actual Status | **WORKING** (with critical bug) |
| Implementation Files | `app/ui/source_panel.py:104-128` (_draw_skeleton) |
| UI Connected | Yes — overlay drawn on source image via QPainter |
| Automated Test | None |
| Real Execution Evidence | Visual skeleton lines and joint dots rendered in UI |
| Blocking Defect | **CRITICAL** — `source_panel.py:148-161` Joint dragging writes screen coordinates into image-space fields, corrupting pose data. No zoom/pan coordinate conversion. |
| Required Repair | Fix coordinate transform in mouse handlers |

---

## 4. Manual 2D Joint Correction (Drag)

| Field | Value |
|---|---|
| Claimed Status | ✅ Phase 2 COMPLETED |
| Actual Status | **BROKEN** |
| Implementation Files | `app/ui/source_panel.py:137-161` (mouse press/move/release) |
| UI Connected | Yes — monkey-patched mouse handlers on QLabel |
| Automated Test | None |
| Real Execution Evidence | Dragging appears to move joints but writes wrong coordinates |
| Blocking Defect | **CRITICAL** — `source_panel.py:148-161` No screen-to-image coordinate conversion. Data is silently corrupted on drag. |
| Required Repair | Rewrite mouse handlers with proper coordinate transform |

---

## 5. 3D Pose Initialization (lift_to_3d)

| Field | Value |
|---|---|
| Claimed Status | ✅ Phase 3 COMPLETED |
| Actual Status | **WORKING** (heuristic, documented limitation) |
| Implementation Files | `app/pose3d/lifting_pipeline.py` (121 lines) |
| UI Connected | Yes — `main_window.py:243` `_on_generate_3d` |
| Automated Test | `tests/integration/test_detection_pipeline.py:36-44` (returned >0 joints, critical joints present) |
| Real Execution Evidence | 28 joints with XYZ produced from bus.jpg detection |
| Blocking Defect | None (heuristic depth is a known limitation, not a bug) |
| Required Repair | Replace heuristic depth with learned model or IK solver |

---

## 6. Interactive 3D Viewport

| Field | Value |
|---|---|
| Claimed Status | ✅ Phase 4 COMPLETED |
| Actual Status | **PARTIAL** |
| Implementation Files | `app/ui/viewport_3d.py` (190 lines) |
| UI Connected | Yes — QOpenGLWidget embedded in main window |
| Automated Test | None (requires GL context) |
| Real Execution Evidence | Renders 3D skeleton + ground grid + torso volume |
| Blocking Defect | **viewport_3d.py:153-177** — No joint picking. Only camera orbit/pan/zoom works. No user interaction with mannequin joints. |
| Required Repair | Add raycasting/picking for 3D joints |

---

## 7. Properties Panel

| Field | Value |
|---|---|
| Claimed Status | ✅ Phase 5 COMPLETED |
| Actual Status | **STUB** |
| Implementation Files | `app/ui/properties_panel.py` (67 lines) |
| UI Connected | No — widgets exist in layout but no signal/slot wiring |
| Automated Test | None |
| Real Execution Evidence | None — all widgets show defaults permanently |
| Blocking Defect | **properties_panel.py:23** btn_lock.clicked unconnected. **:24** btn_reset.clicked unconnected. **:33-35** depth_slider unconnected. **:49** set_joint_info() never called. All controls are decorative. |
| Required Repair | Wire all signals, connect data flow from Viewport3D |

---

## 8. Camera Estimator

| Field | Value |
|---|---|
| Claimed Status | ✅ Phase 3 COMPLETED |
| Actual Status | **DISCONNECTED** |
| Implementation Files | `app/cameras/camera_estimator.py` (45 lines) |
| UI Connected | No — zero call sites in entire codebase |
| Automated Test | None |
| Real Execution Evidence | None (never executed in any workflow) |
| Blocking Defect | **camera_estimator.py:21** — `estimate_camera()` defined but never called. Only 2/10 CameraMatch fields populated. |
| Required Repair | Wire into viewport and export pipeline |

---

## 9. Camera Match Workspace

| Field | Value |
|---|---|
| Claimed Status | ❌ Not claimed complete |
| Actual Status | **NOT_IMPLEMENTED** |
| Implementation Files | None — no UI component exists |
| UI Connected | N/A |
| Automated Test | N/A |
| Real Execution Evidence | N/A |
| Blocking Defect | No UI, no integration with viewport or export |
| Required Repair | Build camera match workspace with source image overlay |

---

## 10. Project Save/Load

| Field | Value |
|---|---|
| Claimed Status | ✅ Phase 5 COMPLETED |
| Actual Status | **PARTIAL** |
| Implementation Files | `app/ui/main_window.py:132-158` (open), `:163-190` (save) |
| UI Connected | Yes — File menu, Ctrl+S, Ctrl+O |
| Automated Test | None (persistence round-trip) |
| Real Execution Evidence | Save produces valid JSON, can reload from disk |
| Blocking Defect | **main_window.py:140-158** — 3D pose never restored on open (pose3d loaded but not deserialized or sent to viewport). **main_window.py:182-184** — Only 2D pose re-read on save; 3D corrections discarded. **viewport_3d.py:12-14** — Camera state never persisted. |
| Required Repair | Deserialize pose3d on open, re-read viewport state on save |

---

## 11. Export Workflow (_on_export + ExportDialog)

| Field | Value |
|---|---|
| Claimed Status | ✅ Phase 5/6 COMPLETED |
| Actual Status | **BROKEN** |
| Implementation Files | `app/ui/main_window.py:254-259`, `app/ui/dialogs.py:90-153` |
| UI Connected | Yes — menu, Ctrl+E, toolbar button all trigger the dialog |
| Automated Test | None |
| Real Execution Evidence | Dialog opens and renders, but no output is produced |
| Blocking Defect | **main_window.py:258-259** — `dialog.exec()` return value never checked, no form values read, no exporter invoked. **dialogs.py:90-153** — Zero code reads form fields. **blender_renderer.py:51** — `render()` calls non-existent `_generate_blender_script()`. |
| Required Repair | Wire dialog to form reading, connect to BlenderRenderer, produce file output |

---

## 12. Render Profiles

| Field | Value |
|---|---|
| Claimed Status | ✅ Phase 6 COMPLETED |
| Actual Status | **PARTIAL** |
| Implementation Files | `app/exporters/render_profiles.py` (44 lines) |
| UI Connected | No — ExportDialog combo box strings don't match profile keys |
| Automated Test | `tests/unit/test_export.py:40-44` (profiles_exist — checks dict keys only) |
| Real Execution Evidence | Only 3/6 profiles have config; no code calls them |
| Blocking Defect | **render_profiles.py:54-85** — PROFILES dict has 3 entries but UI combo has 6 items. No mapping function exists. |
| Required Repair | Complete all 6 profiles, add lookup function, wire to dialog |

---

## 13. Export Pack Exporter

| Field | Value |
|---|---|
| Claimed Status | ✅ Phase 6 COMPLETED |
| Actual Status | **STUB** |
| Implementation Files | `app/exporters/pack_exporter.py` (21 lines of non-empty code) |
| UI Connected | No — zero imports from UI layer |
| Automated Test | `tests/unit/test_export.py:18-38` (generation functions only) |
| Real Execution Evidence | None — dead code |
| Blocking Defect | No orchestrator class, no entry point. 4 pack checkboxes in ExportDialog are decorative. |
| Required Repair | Build pack orchestrator, wire to dialog and renderer |

---

## 14. Preflight Validation

| Field | Value |
|---|---|
| Claimed Status | ✅ Phase 7 COMPLETED |
| Actual Status | **PARTIAL** |
| Implementation Files | `app/preflight/validator.py` (43 lines) |
| UI Connected | No — never called from any export or workflow |
| Automated Test | `tests/unit/test_preflight.py:15-37` (4 tests) |
| Real Execution Evidence | Tests pass with synthetic data, but never runs in application |
| Blocking Defect | Not wired into export workflow; results are never displayed to user |
| Required Repair | Integrate into export preflight step, show results in dialog |

---

## 15. Pose Library

| Field | Value |
|---|---|
| Claimed Status | ❌ Not claimed complete |
| Actual Status | **NOT_IMPLEMENTED** |
| Implementation Files | `app/library/__init__.py` (0 bytes — empty) |
| UI Connected | No — no UI exists |
| Automated Test | None |
| Real Execution Evidence | None |
| Blocking Defect | Empty package. No database, no CRUD, no models, no UI. |
| Required Repair | Full implementation (database schema, save/load, browser UI) |

---

## 16. Blender Integration

| Field | Value |
|---|---|
| Claimed Status | ✅ Phase 3 COMPLETED |
| Actual Status | **PARTIAL** |
| Implementation Files | `app/rendering/blender_renderer.py` (60 lines), `blender/scripts/render_mannequin.py` (293 lines) |
| UI Connected | No — renderer is never instantiated or called from any workflow |
| Automated Test | None |
| Real Execution Evidence | Blender script works standalone (tested manually: mannequin_test.png). `render_with_script()` would work if called. `render()` would crash. |
| Blocking Defect | **blender_renderer.py:51** — `render()` calls non-existent `_generate_blender_script()`. **blender_renderer.py** — not wired into export workflow. |
| Required Repair | Fix `render()` or remove it, wire `render_with_script()` into export |

---

## 17. MediaPipe Fallback Detector

| Field | Value |
|---|---|
| Claimed Status | ✅ Phase 1 COMPLETED |
| Actual Status | **STUB** |
| Implementation Files | `app/detectors/mediapipe_detector.py` (74 lines) |
| UI Connected | No — not imported by detection pipeline |
| Automated Test | None |
| Real Execution Evidence | None (never executed) |
| Blocking Defect | **mediapipe_detector.py:104** — `_get_pose_detector()` returns None if model file not found (no download provided). Detection pipeline never imports this module. |
| Required Repair | Integrate as fallback in detection_pipeline.py when YOLO fails |

---

## 18. Hand Detection

| Field | Value |
|---|---|
| Claimed Status | ❌ Not claimed complete |
| Actual Status | **NOT_IMPLEMENTED** |
| Implementation Files | `app/detectors/base.py:19-22` (HandDetector interface only) |
| UI Connected | No |
| Automated Test | None |
| Real Execution Evidence | None |
| Blocking Defect | Interface defined but no implementation exists |
| Required Repair | Implement MediaPipe Hands integration |

---

## 19. IK Solver

| Field | Value |
|---|---|
| Claimed Status | ❌ Not claimed complete |
| Actual Status | **NOT_IMPLEMENTED** |
| Implementation Files | None |
| UI Connected | N/A |
| Automated Test | N/A |
| Real Execution Evidence | N/A |
| Blocking Defect | No implementation at any level |
| Required Repair | Build constrained IK solver for 3D pose refinement |

---

## 20. Windows Installer

| Field | Value |
|---|---|
| Claimed Status | 🟡 Phase 9 COMPLETED (claimed) |
| Actual Status | **NOT_IMPLEMENTED** |
| Implementation Files | `scripts/build_installer.ps1` (25 lines — runs tests only, no packaging) |
| UI Connected | N/A |
| Automated Test | N/A |
| Real Execution Evidence | No .exe, .msi, or .iss file exists. No PyInstaller build configured. |
| Blocking Defect | Script runs `pytest` then creates an empty output directory. No packaging tool configured. |
| Required Repair | Full PyInstaller + Inno Setup pipeline |

---

## 21. Settings Persistence

| Field | Value |
|---|---|
| Claimed Status | ✅ Phase 8 COMPLETED |
| Actual Status | **WORKING** |
| Implementation Files | `app/config/settings.py` (89 lines) |
| UI Connected | Yes — Settings dialog reads and writes via `get_val`/`set` |
| Automated Test | None |
| Real Execution Evidence | Creates `%USERPROFILE%\.posereferenceforge\settings.json`, saves/loads correctly |
| Blocking Defect | None |
| Required Repair | None |

---

## 22. Image Import

| Field | Value |
|---|---|
| Claimed Status | ✅ Phase 2 COMPLETED |
| Actual Status | **WORKING** |
| Implementation Files | `app/services/image_service.py` (38 lines) |
| UI Connected | Yes — File → Import Image, Ctrl+I |
| Automated Test | `tests/unit/test_image_service.py` (4 tests) |
| Real Execution Evidence | JPG, PNG loaded and displayed correctly |
| Blocking Defect | None |
| Required Repair | None |

---

## Summary

| Area | Count |
|---|---|
| WORKING | 5 (Person Detection, 2D Pose Detection, 3D lifting, Settings, Image Import) |
| PARTIAL | 5 (2D Skeleton, Viewport3D, Project Save/Load, Render Profiles, Preflight, Blender) |
| STUB | 3 (Properties Panel, MediaPipe, Pack Exporter) |
| DISCONNECTED | 1 (Camera Estimator) |
| BROKEN | 2 (Joint Drag, Export Workflow) |
| NOT_IMPLEMENTED | 5 (Camera Match UI, Pose Library, Hand Detection, IK Solver, Windows Installer) |
