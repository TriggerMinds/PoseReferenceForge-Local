# Known Limitations

Last updated: 2026-07-15 (Recovery 01 audit)

## Detection

- YOLOv8n-pose uses the COCO 17-keypoint schema; additional joints (hands, feet, spine) are inferred heuristically
- Hand detection is not integrated (hand landmarks use wrist position as proxy)
- MediaPipe fallback is defined but not wired into the detection pipeline
- Occluded joints are inferred, not detected
- Very low-resolution images (< 200px) may fail detection
- No multi-person pose tracking

## 2D Skeleton Editing

- Joint dragging has a critical coordinate-space bug (screen vs image coordinates) when zoom ≠ 1.0
- No undo/redo for 2D joint edits
- No joint locking feedback in the 2D view
- No keyboard shortcuts beyond the top-level menu

## 3D Pose

- Monocular 3D lifting uses heuristic depth as initializer
- **ScipyPoseFitter** uses constrained optimization (L-BFGS-B) to refine depth from reprojection (53-61% improvement over heuristic)
- No learned 3D pose model (MediaPipe world coords unavailable due to API issues in mediapipe 0.10.35)
- No IK solver for anatomically valid pose refinement
- No temporal coherence (single-image only)
- Extreme poses (severe foreshortening, complex sitting) may produce incorrect depth
- Optimization operates on joint offsets, not skeleton chains (no FK/IK hierarchy)

## 3D Viewport

- Mannequin is rendered as skeleton + simple cylinder geometry (not skinned mesh)
- No 3D joint picking (clicking a joint in the viewport does nothing)
- No transform gizmos for rotation/translation
- No IK target handles
- Camera orbit/pan/zoom state is not persisted between sessions

## Properties Panel

- All controls (Lock, Reset, Depth Slider) are decorative — no signal wiring
- Joint information labels always show "None"
- Warning list is never populated
- No connection to viewport selection

## Export

- **Export workflow produces no output** — dialog opens but no file is written
- BlenderRenderer.render() crashes on AttributeError (missing method)
- Only 3 of 6 render profiles have configuration data
- Pack exporter functions exist but are dead code
- Quality reports are generated but never saved
- Preflight validation runs silently with no UI feedback
- No source-matched camera overlay export

## Camera

- **CameraMatchPanel** now provides interactive camera matching with source overlay
- Camera parameters (azimuth, elevation, roll, focal length, offset) adjustable via sliders
- Camera params passed to Blender rendering
- Camera params saved to project data but not yet fully restored on project reopen
- No pre-computed camera auto-fit (uses heuristic shoulder-line estimation)

## Persistence

- 3D pose is never restored on project reopen
- 3D corrections and depth adjustments are lost on save
- Camera state (orbit/pan/zoom) is not saved
- 2D view state (zoom, pan, skeleton visibility) is not saved
- No project schema migration
- Missing source image on reload produces silent blank panel

## Pose Library

- Not implemented — empty package with no database, no CRUD, no UI

## Animation

- No motion data export (BVH) in current version
- No multi-frame or video support

## Packaging

- No Windows installer — application requires Python + venv setup
- Build script only runs tests, does not package
- No PyInstaller configuration
- No Inno Setup script
- Blender must be installed separately (not bundled)

## Testing

- No UI tests
- No Blender render tests
- No round-trip persistence tests
- Test coverage is 32% (UI and renderer are uncovered)
- Export tests only validate naming functions, not actual output
