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

### Current Approach: Heuristic
- Inverse perspective projection from 2D landmarks
- Anatomical depth heuristics
- Pelvis-centered normalization

**Verdict:** Adequate for Phase 2/3. A learned initializer (e.g., simple MLP regressor from 2D→3D) should be added in hardening.

## Hand Detection

Not yet evaluated. MediaPipe Hands will be the primary option when needed.

## Future Model Candidates
- RTMPose (MMPose): Higher accuracy at same model size
- HybrIK: Dedicated 3D lifting
- SMPL-X regressor: Full body mesh
