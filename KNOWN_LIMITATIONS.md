# Known Limitations

## Detection

- YOLOv8n-pose uses the COCO 17-keypoint schema; additional joints (hands, feet, spine) are inferred heuristically
- Hand detection is not yet integrated (hand landmarks use wrist position as proxy)
- Occluded joints are inferred, not detected
- Very low-resolution images (< 200px) may fail detection

## 3D Pose

- Monocular 3D lifting has inherent depth ambiguity
- Depth estimation uses heuristics, not a learned model
- No temporal coherence (single-image only)
- Extreme poses (severe foreshortening, complex sitting) may produce incorrect depth

## Viewport

- Mannequin is rendered as skeleton + simple cylinders (not skinned mesh)
- No transform gizmo implementation yet (rotation is via key/mouse)
- No IK target handles in the viewport (planned for future)

## Rendering

- Blender subprocess is required for final renders
- First render is slower (~30s); subsequent renders use cached data
- Blender must be installed separately (not bundled)

## Animation

- No motion data export (BVH) in current version
- No multi-frame support

## Packaging

- No standalone installer yet (launch via START.bat)
- Python + venv required for current workflow
