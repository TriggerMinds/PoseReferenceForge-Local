"""Reprojection evaluation and camera model for 3D pose fitting."""
import numpy as np
from typing import Optional
from app.domain.models import Pose2D, Pose3D, Joint2D


def build_camera_matrix(params: dict) -> dict:
    """Build a pinhole camera model from optimization parameters."""
    f = params.get("focal_length", 1500.0)
    cx = params.get("cx", 0.0)
    cy = params.get("cy", 0.0)
    az = np.radians(params.get("azimuth", 0.0))
    el = np.radians(params.get("elevation", 0.0))
    roll = np.radians(params.get("roll", 0.0))
    tx = params.get("tx", 0.0)
    ty = params.get("ty", 0.0)
    tz = params.get("tz", 0.0)

    # Rotation matrices
    Rz = np.array([
        [np.cos(az), -np.sin(az), 0],
        [np.sin(az), np.cos(az), 0],
        [0, 0, 1],
    ])
    Ry = np.array([
        [np.cos(el), 0, np.sin(el)],
        [0, 1, 0],
        [-np.sin(el), 0, np.cos(el)],
    ])
    Rx = np.array([
        [1, 0, 0],
        [0, np.cos(roll), -np.sin(roll)],
        [0, np.sin(roll), np.cos(roll)],
    ])
    R = Rz @ Ry @ Rx
    t = np.array([tx, ty, tz])

    K = np.array([
        [f, 0, cx],
        [0, f, cy],
        [0, 0, 1],
    ])

    return {"R": R, "t": t, "K": K, "f": f}


def project_points(points_3d: np.ndarray, camera: dict) -> np.ndarray:
    """Project 3D points to 2D using the pinhole camera model.
    
    Args:
        points_3d: (N, 3) array of 3D points in world coordinates
        camera: dict with R, t, K
    
    Returns:
        (N, 2) array of 2D projections
    """
    R = camera["R"]
    t = camera["t"]
    K = camera["K"]

    # Transform to camera coordinates
    cam_pts = (R @ points_3d.T).T + t

    # Perspective projection
    valid = cam_pts[:, 2] > 1e-6
    proj = np.zeros((points_3d.shape[0], 2))
    if valid.any():
        pts_2d = K @ cam_pts[valid].T
        pts_2d = pts_2d.T
        proj[valid] = pts_2d[:, :2] / pts_2d[:, 2:3]
    return proj


def compute_reprojection_error(
    pose3d: Pose3D,
    pose2d: Pose2D,
    camera_params: dict,
    joint_weights: Optional[dict[str, float]] = None,
) -> tuple[float, dict[str, float]]:
    """Compute weighted reprojection error.
    
    Returns:
        total_error: weighted sum of squared errors
        per_joint: dict of joint_id -> error
    """
    camera = build_camera_matrix(camera_params)

    # Build 3D point array
    joint_order = list(pose3d.joints.keys())
    n = len(joint_order)
    pts_3d = np.zeros((n, 3))
    for i, jid in enumerate(joint_order):
        j = pose3d.joints[jid]
        pts_3d[i] = [j.x, j.y, j.z]

    proj_2d = project_points(pts_3d, camera)

    total_error = 0.0
    per_joint = {}
    for i, jid in enumerate(joint_order):
        j2d = pose2d.get_joint(jid)
        if j2d is None or not j2d.detected:
            continue
        dx = proj_2d[i, 0] - j2d.x
        dy = proj_2d[i, 1] - j2d.y
        err = dx * dx + dy * dy

        weight = joint_weights.get(jid, 1.0) if joint_weights else 1.0
        if j2d.confidence > 0.7:
            weight *= 2.0
        elif j2d.confidence < 0.3:
            weight *= 0.5

        per_joint[jid] = err
        total_error += err * weight

    return total_error / max(len(per_joint), 1), per_joint


def evaluate_reprojection(
    pose2d: Pose2D,
    pose3d: Pose3D,
    camera_params: dict,
) -> dict:
    """Full reprojection evaluation with per-joint metrics."""
    total_err, per_joint = compute_reprojection_error(
        pose3d, pose2d, camera_params
    )

    # Count joints by confidence
    high_conf = sum(
        1 for j in pose2d.joints.values()
        if j.detected and j.confidence > 0.5
    )
    low_conf = sum(
        1 for j in pose2d.joints.values()
        if j.detected and 0.3 <= j.confidence <= 0.5
    )
    inferred = sum(1 for j in pose2d.joints.values() if j.inferred)

    per_joint_list = [
        {
            "joint_id": jid,
            "error_2d": float(err),
            "detected": pose2d.get_joint(jid).detected if pose2d.get_joint(jid) else False,
            "confidence": pose2d.get_joint(jid).confidence if pose2d.get_joint(jid) else 0.0,
        }
        for jid, err in sorted(per_joint.items(), key=lambda x: -x[1])
    ]

    return {
        "total_reprojection_error": float(total_err),
        "rme": float(np.sqrt(total_err)),
        "high_confidence_joints": high_conf,
        "low_confidence_joints": low_conf,
        "inferred_joints": inferred,
        "per_joint_errors": per_joint_list,
    }
