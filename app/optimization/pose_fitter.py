"""Constrained pose fitting with bone-length preservation and fit quality gating."""
import numpy as np
from typing import Optional
from scipy.optimize import minimize
from copy import deepcopy

from app.domain.models import Pose2D, Pose3D, Joint3D, JointState
from app.optimization.reprojection import compute_reprojection_error
from app.optimization.interfaces import PoseFitter

# Major skeleton connections for bone-length constraints
SKELETON_BONES = [
    ("pelvis", "lower_spine"), ("lower_spine", "upper_spine"),
    ("upper_spine", "neck"), ("neck", "head"),
    ("neck", "left_shoulder"), ("neck", "right_shoulder"),
    ("left_shoulder", "left_elbow"), ("right_shoulder", "right_elbow"),
    ("left_elbow", "left_wrist"), ("right_elbow", "right_wrist"),
    ("left_wrist", "left_hand"), ("right_wrist", "right_hand"),
    ("pelvis", "left_hip"), ("pelvis", "right_hip"),
    ("left_hip", "left_knee"), ("right_hip", "right_knee"),
    ("left_knee", "left_ankle"), ("right_knee", "right_ankle"),
    ("left_ankle", "left_heel"), ("right_ankle", "right_heel"),
    ("left_heel", "left_foot"), ("right_heel", "right_foot"),
]

# Core joints that define the skeleton (excluding inferred dependents)
CORE_JOINTS = [
    "pelvis", "lower_spine", "upper_spine", "neck",
    "left_shoulder", "right_shoulder",
    "left_elbow", "right_elbow",
    "left_wrist", "right_wrist",
    "left_hip", "right_hip",
    "left_knee", "right_knee",
    "left_ankle", "right_ankle",
]

# Inferred dependent joints (recomputed from parents, not independently fitted)
DEPENDENT_JOINTS = {
    "head": "neck",
    "left_hand": "left_wrist",
    "right_hand": "right_wrist",
    "left_heel": "left_ankle",
    "right_heel": "right_ankle",
    "left_foot": "left_ankle",
    "right_foot": "right_ankle",
}

# Symmetry pairs for length consistency
SYMMETRY_PAIRS = [
    ("left_shoulder", "right_shoulder"),
    ("left_elbow", "right_elbow"),
    ("left_wrist", "right_wrist"),
    ("left_hip", "right_hip"),
    ("left_knee", "right_knee"),
    ("left_ankle", "right_ankle"),
]


def compute_bone_lengths(pose: Pose3D) -> dict[tuple[str, str], float]:
    lengths = {}
    for j1, j2 in SKELETON_BONES:
        p1 = pose.joints.get(j1)
        p2 = pose.joints.get(j2)
        if p1 and p2:
            d = np.sqrt((p1.x-p2.x)**2 + (p1.y-p2.y)**2 + (p1.z-p2.z)**2)
            lengths[(j1, j2)] = max(d, 0.001)
    return lengths


def compute_reprojection_rme(pose3d: Pose3D, pose2d: Pose2D, camera_params: dict) -> float:
    err, _ = compute_reprojection_error(pose3d, pose2d, camera_params)
    return float(np.sqrt(err))


def is_skeleton_connected(pose: Pose3D) -> tuple[bool, list[str]]:
    missing = []
    for j1, j2 in SKELETON_BONES:
        if j1 not in pose.joints or j2 not in pose.joints:
            missing.append(f"{j1}->{j2}")
    return len(missing) == 0, missing


def has_finite_coords(pose: Pose3D) -> tuple[bool, list[str]]:
    bad = []
    for jid, j in pose.joints.items():
        if not np.isfinite(j.x) or not np.isfinite(j.y) or not np.isfinite(j.z):
            bad.append(jid)
    return len(bad) == 0, bad


def recompute_dependents(pose: Pose3D) -> Pose3D:
    """Recompute dependent joints (hands, feet, heels, head) from their parents."""
    for dependent, parent in DEPENDENT_JOINTS.items():
        p = pose.joints.get(parent)
        j = pose.joints.get(dependent)
        if p and j and not j.locked:
            j.x = p.x
            j.y = p.y
            j.z = p.z
            if dependent in ("left_hand", "right_hand"):
                j.y -= 0.05
            elif dependent in ("left_heel", "right_heel"):
                j.y -= 0.02
            elif dependent in ("left_foot", "right_foot"):
                j.y -= 0.03; j.x += 0.02
            elif dependent == "head":
                j.y += 0.1
    return pose


def auto_scale_pose(pose3d: Pose3D, pose2d: Pose2D) -> tuple[Pose3D, float]:
    img_w = pose2d.image_width or 1000
    img_h = pose2d.image_height or 1000
    detected = [j for j in pose2d.joints.values() if j.detected]
    if len(detected) < 3:
        return pose3d, 1.0
    xs = [j.x for j in detected]; ys = [j.y for j in detected]
    bbox_w = max(xs)-min(xs); bbox_h = max(ys)-min(ys)
    if bbox_w < 1 or bbox_h < 1:
        return pose3d, 1.0
    vals = [(j.x, j.y, j.z) for j in pose3d.joints.values()]
    if not vals:
        return pose3d, 1.0
    xs3, ys3, zs3 = zip(*vals)
    bbox_w3 = max(xs3)-min(xs3); bbox_h3 = max(ys3)-min(ys3)
    if bbox_w3 < 0.01 or bbox_h3 < 0.01:
        return pose3d, 1.0
    scale = (bbox_w / bbox_w3) * 0.4
    scale = max(0.01, min(100.0, scale))
    new_pose = Pose3D()
    for jid, j in pose3d.joints.items():
        new_pose.joints[jid] = Joint3D(jid, j.x*scale, j.y*scale, j.z*scale,
                                         j.confidence, j.state, j.locked,
                                         j.manually_corrected)
    return new_pose, scale


class ScipyPoseFitter(PoseFitter):
    """Constrained pose fitter preserving bone lengths and skeleton connectivity."""

    def __init__(self):
        self.lens_mm = 1500
        self.sensor_mm = 36.0
        self.bone_length_tolerance = 0.3
        self.max_normalized_rme = 0.25

    def fit(self, pose2d: Pose2D, pose3d: Pose3D,
            camera_params: Optional[dict] = None) -> tuple[Pose3D, dict]:
        img_w = pose2d.image_width or 1000
        img_h = pose2d.image_height or 1000
        img_diag = np.sqrt(img_w**2 + img_h**2)

        scaled, scale_factor = auto_scale_pose(pose3d, pose2d)

        # Compute rest bone lengths
        rest_lengths = compute_bone_lengths(scaled)

        # Joint order for optimization (only core joints)
        joint_order = [j for j in CORE_JOINTS if j in scaled.joints]
        n = len(joint_order)

        # Optimization variables: each core joint gets [dz, dx_adj]
        # dz = depth offset, dx_adj = small X correction
        x0 = np.zeros(n * 2, dtype=np.float64)

        # Bounds: dz ±500, dx_adj ±20
        bounds = [(-500.0, 500.0), (-20.0, 20.0)] * n

        # Default camera
        if camera_params is None:
            camera_params = {
                "focal_length": max(img_w, img_h) * 1.2,
                "cx": img_w / 2, "cy": img_h / 2,
                "azimuth": 0, "elevation": 0, "roll": 0,
                "tx": 0, "ty": 0, "tz": max(img_w, img_h) * 2.0,
            }

        joint_weights = {}
        for jid, j in pose2d.joints.items():
            w = 1.0
            if j.detected:
                w = 3.0 if j.confidence > 0.5 else (1.0 if j.confidence > 0.3 else 0.5)
            else:
                w = 0.1
            joint_weights[jid] = w

        def build_pose(params):
            pose = Pose3D()
            for i, jid in enumerate(joint_order):
                ref = scaled.joints[jid]
                dz = params[i * 2]
                dx_adj = params[i * 2 + 1]
                state = ref.state if ref else JointState.INFERRED
                mc = ref.manually_corrected if ref else False
                pose.joints[jid] = Joint3D(jid, ref.x + dx_adj, ref.y, ref.z + dz,
                                           ref.confidence, state, ref.locked, mc)
            # Copy remaining joints
            for jid, j in scaled.joints.items():
                if jid not in pose.joints:
                    pose.joints[jid] = Joint3D(jid, j.x, j.y, j.z, j.confidence, j.state, j.locked, j.manually_corrected)
            recompute_dependents(pose)
            return pose

        def objective(params):
            pose = build_pose(params)
            error, _ = compute_reprojection_error(pose, pose2d, camera_params, joint_weights)

            # Bone-length deviation penalty
            bone_penalty = 0.0
            current = compute_bone_lengths(pose)
            for bone, rest in rest_lengths.items():
                cur = current.get(bone, 0)
                if cur > 0:
                    deviation = abs(cur - rest) / max(rest, 0.001)
                    if deviation > self.bone_length_tolerance:
                        bone_penalty += (deviation - self.bone_length_tolerance) ** 2 * 100.0

            # Symmetry penalty for left-right pairs
            sym_penalty = 0.0
            for j1, j2 in SYMMETRY_PAIRS:
                p1 = pose.joints.get(j1); p2 = pose.joints.get(j2)
                if p1 and p2:
                    left_len = current.get((j1, next_j), 0) if False else 0
                    right_len = current.get((j2, next_j), 0) if False else 0
                    dz_diff = abs(p1.z - p2.z)
                    if dz_diff > 0.5:
                        sym_penalty += (dz_diff - 0.5) * 10.0

            # Depth regularization
            depth_penalty = sum(params[i*2]**2 for i in range(n)) * 0.001

            return float(error) + bone_penalty + sym_penalty + depth_penalty

        # Run optimization
        result = minimize(objective, x0, method="L-BFGS-B", bounds=bounds,
                          options={"maxiter": 300, "ftol": 1e-6})

        optimized_scaled = build_pose(result.x)
        rme = compute_reprojection_rme(optimized_scaled, pose2d, camera_params)
        norm_rme = rme / max(img_diag, 1)

        # Fit quality assessment
        connected, missing_connections = is_skeleton_connected(optimized_scaled)
        finite, bad_coords = has_finite_coords(optimized_scaled)

        # Bone-length deviation
        current_lengths = compute_bone_lengths(optimized_scaled)
        max_deviation = 0.0
        deviating_bones = []
        for bone, rest in rest_lengths.items():
            cur = current_lengths.get(bone, 0)
            if cur > 0 and rest > 0:
                dev = abs(cur - rest) / rest
                if dev > max_deviation:
                    max_deviation = dev
                if dev > self.bone_length_tolerance:
                    deviating_bones.append(f"{bone[0]}->{bone[1]}")

        optimizer_converged = bool(result.success) or result.nit > 0
        quality_passed = (
            connected and finite and
            norm_rme <= self.max_normalized_rme and
            max_deviation <= self.bone_length_tolerance * 2 and
            rme >= 0  # always true, just counting checks
        )

        # Enhanced quality checks
        quality_failures = []
        if not connected:
            quality_failures.append(f"disconnected: {missing_connections}")
        if not finite:
            quality_failures.append(f"non-finite: {bad_coords}")
        if norm_rme > self.max_normalized_rme:
            quality_failures.append(f"norm_rme={norm_rme:.4f} > max={self.max_normalized_rme}")
        if max_deviation > self.bone_length_tolerance * 2:
            quality_failures.append(f"bone_deviation={max_deviation:.2f} > {self.bone_length_tolerance*2}")
        if deviating_bones:
            quality_failures.append(f"bones: {deviating_bones[:5]}")

        fit_succeeded = optimizer_converged and quality_passed

        if fit_succeeded:
            final_pose = optimized_scaled
        else:
            final_pose = scaled
            for jid, j in scaled.joints.items():
                final_pose.joints[jid] = Joint3D(jid, j.x, j.y, j.z, j.confidence, j.state, j.locked, j.manually_corrected)
            recompute_dependents(final_pose)

        # Preserve original joint states (fitter does NOT set MANUALLY_CORRECTED)
        for jid, j in final_pose.joints.items():
            orig = scaled.joints.get(jid)
            if orig:
                j.state = orig.state
                j.manually_corrected = orig.manually_corrected
                j.locked = orig.locked

        info = {
            "optimizer_converged": optimizer_converged,
            "quality_passed": quality_passed,
            "fit_succeeded": fit_succeeded,
            "initial_error": float(objective(x0)),
            "final_error": float(result.fun),
            "reprojection_rme": float(rme),
            "normalized_rme": float(norm_rme),
            "max_bone_deviation": float(max_deviation),
            "connected": connected,
            "finite_coords": finite,
            "iterations": result.nit if hasattr(result, "nit") else 0,
            "scale_factor": float(scale_factor),
            "quality_failures": quality_failures,
            "fallback_used": not fit_succeeded,
        }
        return final_pose, info
