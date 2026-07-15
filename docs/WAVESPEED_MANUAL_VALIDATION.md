# WaveSpeed Manual Validation Guide

There is no WaveSpeed API integration in PoseReferenceForge Local.

This document describes a manual test procedure to validate that pose-reference images produced by the application are effective when used with WaveSpeed.ai or comparable multimodal AI image-generation platforms.

## Prerequisites

- A WaveSpeed.ai account or comparable AI image-generation platform
- Separate identity-reference images (photographs defining the person's appearance)
- A PoseReferenceForge Local export pack

## Test Procedure

### Test 1: Straightforward Standing Pose

1. Open PoseReferenceForge Local.
2. Import a standing pose photograph.
3. Run pose detection and 3D generation.
4. Export a **one-image pack** (source-matched clean PNG).
5. Upload to WaveSpeed.ai:
   - **Identity reference:** A photograph of the person whose appearance you want to preserve.
   - **Pose reference:** The exported `Pose_0001_pose_primary.png` from the pack.
   - **Prompt:** *"A photo of a person standing naturally, full body, the mannequin controls pose only."*
6. Evaluate whether the generated image matches the pose of the mannequin.

### Test 2: Pose with Limb Depth

1. Find or create a pose photograph with one arm extended forward or one leg crossed.
2. Import into PoseReferenceForge Local.
3. Run detection and 3D generation.
4. Use the **Camera Match** workspace to verify depth ordering.
5. Correct any depth issues using:
   - Scroll-wheel on joints in the 3D viewport
   - The **Fit 3D Pose** (Ctrl+F) optimization
6. Export a **two-image pack** (primary + depth support).
7. Upload to WaveSpeed.ai:
   - **Identity reference**
   - **Pose references:** Both images from the pack
   - **Prompt:** Describe the pose, mention limb positions.
8. Evaluate whether the generated limb positions match the mannequin.

### Test 3: Crouching, Seated or Crossed-Limb Pose

1. Import a crouching, seated or crossed-leg pose photograph.
2. Run detection → 3D generation → fit (Ctrl+F).
3. Manually correct:
   - Depth of overlapping limbs
   - Knee/elbow positions
   - Foot contacts
4. Export a **three-image pack**.
5. Upload to WaveSpeed.ai with all three reference images.
6. Evaluate pose accuracy.

## Validation Criteria

A test passes when an external evaluator confirms:

- The generated person's pose clearly matches the mannequin's pose.
- The identity (face, body shape, clothing) comes from the identity reference, NOT the mannequin.
- No mannequin artifacts (joint spheres, limb cylinders) bleed into the final image.
- The pose is usable as a production reference without manual rework.

## Production Candidate Pack

A reference pack for external testing is available at:

```
evidence/reference_packs/recovery_05_full/
```

This pack contains:
- `reference/Pose_0001_pose_primary.png` — Primary pose reference
- `reference/Pose_0001_transparent.png` — Transparent variant
- `multiview/` — 8 camera angles for reference
- `data/` — Pose preset and keypoint data

## Status

| Test | Status | Date | Evaluator |
|---|---|---|---|
| Straightforward pose | PENDING | — | — |
| Pose with depth | PENDING | — | — |
| Crouching/seated | PENDING | — | — |

Before these tests are confirmed by a human evaluator, the reference image workflow is:

**REFERENCE_IMAGE_WORKFLOW_STATUS: CONDITIONALLY_READY**
**DAILY_WORKFLOW_STATUS: CONDITIONALLY_READY**
