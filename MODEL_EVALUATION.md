# Model Evaluation

## Person Detection

### Evaluated: YOLOv8n-pose (Ultralytics)
- **Model:** yolov8n-pose.pt
- **Source:** Ultralytics (via ultralytics Python package)
- **License:** AGPL-3.0
- **File Size:** 6.8 MB
- **Device:** GPU (CUDA) / CPU
- **Inference (GPU):** ~1.6s on RTX 2060 SUPER
- **VRAM:** ~300 MB
- **Detection Schema:** COCO 17-keypoint

**Verdict: PRIMARY DETECTOR.** Lightweight, fast, proven accuracy.

### Evaluated: MediaPipe Pose (New tasks API)
- **Version:** 0.10.35
- **Model:** pose_landmarker_lite.task (optional download)
- **Device:** CPU
- **Landmarks:** 33 per person

**Verdict: FALLBACK DETECTOR.** Good for CPU fallback, more landmarks.

## 2D Pose Detection

Same models as person detection; YOLOv8-pose provides both person detection and 17 keypoints in one pass.

## 3D Lifting

### Approach 1: Heuristic (Emergency Fallback)
- Inverse perspective projection from 2D landmarks
- Anatomical depth heuristics (fixed per-joint class)
- Pelvis-centered normalization
- **Status:** Preserved as labelled fallback in `app/pose3d/lifting_pipeline.py`

### Approach 2: Scipy Constrained Optimization (PRIMARY)
- `app/optimization/pose_fitter.py` — ScipyPoseFitter
- Auto-scales heuristic 3D pose to match image dimensions
- Optimizes joint positions using L-BFGS-B to minimize reprojection error
- Weighted by detection confidence (high-conf joints weighted 3x)
- Depth regularization to prevent extreme Z values
- Runtime: ~0.13s per image on i9-9900K
- **Improvement:** 53-61% reprojection error reduction over heuristic
- **Verdict:** PRIMARY 3D refinement method. Fast, no GPU needed, image-dependent depth.

### Approach 3: MediaPipe World Coordinates (NOT AVAILABLE)
- MediaPipe 0.10.35 has packaging bugs preventing import of `pose_landmarker` module
- Would provide 33 landmarks with world-space 3D coordinates
- **Status:** Blocked by mediapipe API incompatibility. Skip until next version.

## Hand Detection

Not yet evaluated. MediaPipe Hands will be the primary option when needed.

## Future Model Candidates
- RTMPose (MMPose): Higher accuracy at same model size
- HybrIK: Dedicated 3D lifting
- SMPL-X regressor: Full body mesh
- Learned MLP regressor from 2D→3D: Could be added as a Pose3DInitializer
