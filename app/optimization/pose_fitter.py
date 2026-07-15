"""Constrained optimization fitting pipeline for 3D pose refinement."""
import numpy as np
from typing import Optional
from scipy.optimize import minimize

from app.domain.models import Pose2D, Pose3D, Joint3D, JointState
from app.optimization.reprojection import (
    build_camera_matrix, project_points, compute_reprojection_error,
)
from app.optimization.interfaces import PoseFitter

# skeleton connections for optimization
SKELETON_3D = [
    ("pelvis", "lower_spine"), ("lower_spine", "upper_spine"),
    ("upper_spine", "neck"), ("neck", "head"),
    ("neck", "left_shoulder"), ("neck", "right_shoulder"),
    ("left_shoulder", "left_elbow"), ("right_shoulder", "right_elbow"),
    ("left_elbow", "left_wrist"), ("right_elbow", "right_wrist"),
    ("left_wrist", "left_hand"), ("right_wrist", "right_hand"),
    ("pelvis", "left_hip"), ("pelvis", "right_hip"),
    ("left_hip", "left_knee"), ("right_hip", "right_knee"),
    ("left_knee", "left_ankle"), ("right_knee", "right_ankle"),
]

JOINT_NAMES = [
    "pelvis", "lower_spine", "upper_spine", "neck", "head",
    "left_shoulder", "right_shoulder",
    "left_elbow", "right_elbow",
    "left_wrist", "right_wrist",
    "left_hip", "right_hip",
    "left_knee", "right_knee",
    "left_ankle", "right_ankle",
]


def auto_scale_pose(pose3d: Pose3D, pose2d: Pose2D) -> tuple[Pose3D, float]:
    """Auto-scale a 3D pose to roughly match 2D image dimensions."""
    img_w = pose2d.image_width or 1000
    img_h = pose2d.image_height or 1000

    # Get 2D bounding box of detected joints
    detected_2d = [j for j in pose2d.joints.values() if j.detected]
    if len(detected_2d) < 3:
        return pose3d, 1.0

    xs = [j.x for j in detected_2d]
    ys = [j.y for j in detected_2d]
    bbox_w = max(xs) - min(xs)
    bbox_h = max(ys) - min(ys)
    if bbox_w < 1 or bbox_h < 1:
        return pose3d, 1.0

    # Get 3D bounding box
    vals_3d = [(j.x, j.y, j.z) for j in pose3d.joints.values()]
    if not vals_3d:
        return pose3d, 1.0
    xs3, ys3, zs3 = zip(*vals_3d)
    bbox_w3 = max(xs3) - min(xs3)
    bbox_h3 = max(ys3) - min(ys3)
    if bbox_w3 < 0.01 or bbox_h3 < 0.01:
        return pose3d, 1.0

    # Target: 3D bounding box projected through a standard camera should fill ~80% of 2D bbox
    # The scale factor makes 3D units match roughly with pixel units at focal=img_w
    focal = max(img_w, img_h)
    scale = (bbox_w / bbox_w3) * 0.4
    scale = max(0.01, min(100.0, scale))

    new_pose = Pose3D()
    for jid, j in pose3d.joints.items():
        new_pose.joints[jid] = Joint3D(
            joint_id=jid,
            x=j.x * scale, y=j.y * scale, z=j.z * scale,
            confidence=j.confidence, state=j.state,
            locked=j.locked,
        )
    return new_pose, scale


class ScipyPoseFitter(PoseFitter):
    """Optimizes 3D pose using reprojection error + constraints."""

    def fit(
        self,
        pose2d: Pose2D,
        pose3d: Pose3D,
        camera_params: Optional[dict] = None,
    ) -> tuple[Pose3D, dict]:
        img_w = pose2d.image_width or 1000
        img_h = pose2d.image_height or 1000

        # Auto-scale the 3D pose to match image dimensions
        scaled_pose, scale_factor = auto_scale_pose(pose3d, pose2d)

        # Default camera
        if camera_params is None:
            camera_params = {
                "focal_length": max(img_w, img_h) * 1.2,
                "cx": img_w / 2,
                "cy": img_h / 2,
                "azimuth": 0.0,
                "elevation": 0.0,
                "roll": 0.0,
                "tx": 0.0,
                "ty": 0.0,
                "tz": max(img_w, img_h) * 2.0,  # Subject distance
            }

        # Build parameter vector: [joint_offsets (N*3), ...]
        joint_order = [j for j in JOINT_NAMES if j in scaled_pose.joints]
        n_joints = len(joint_order)

        # Initial params: zeros (no offset from initial pose)
        x0 = np.zeros(n_joints * 3, dtype=np.float64)

        # Per-joint weights from detection confidence
        joint_weights = {}
        for jid, j in pose2d.joints.items():
            w = 1.0
            if j.detected:
                w = 3.0 if j.confidence > 0.7 else (1.0 if j.confidence > 0.3 else 0.5)
            else:
                w = 0.1
            joint_weights[jid] = w

        def build_pose(offsets):
            pose = Pose3D()
            for i, jid in enumerate(joint_order):
                ref = scaled_pose.joints[jid]
                if ref:
                    oi = i * 3
                    pose.joints[jid] = Joint3D(
                        joint_id=jid,
                        x=float(ref.x + offsets[oi]),
                        y=float(ref.y + offsets[oi + 1]),
                        z=float(ref.z + offsets[oi + 2]),
                        confidence=ref.confidence,
                        state=JointState.MANUALLY_CORRECTED,
                        locked=ref.locked,
                    )
            for jid, j in scaled_pose.joints.items():
                if jid not in pose.joints:
                    pose.joints[jid] = Joint3D(
                        joint_id=jid, x=j.x, y=j.y, z=j.z,
                        confidence=j.confidence, state=j.state,
                    )
            return pose

        def objective(x):
            pose = build_pose(x)

            # Reprojection error
            error, _ = compute_reprojection_error(
                pose, pose2d, camera_params, joint_weights
            )

            # Depth regularization (prevent large depth offsets)
            depth_penalty = 0.0
            for i, jid in enumerate(joint_order):
                oi = i * 3
                depth_penalty += x[oi + 2] ** 2 * 0.001

            return float(error) + depth_penalty

        # Run optimization
        result = minimize(
            objective,
            x0,
            method="L-BFGS-B",
            options={"maxiter": 300, "ftol": 1e-6},
        )

        optimized_pose = build_pose(result.x)
        final_error, _ = compute_reprojection_error(
            optimized_pose, pose2d, camera_params, joint_weights
        )

        fit_info = {
            "initial_error": float(objective(x0)),
            "final_error": float(result.fun),
            "reprojection_error": float(final_error),
            "iterations": result.nit if hasattr(result, "nit") else 0,
            "success": bool(result.success),
            "message": str(result.message),
            "scale_factor": float(scale_factor),
        }
        return optimized_pose, fit_info
