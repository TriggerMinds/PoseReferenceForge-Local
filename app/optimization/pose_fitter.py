"""Constrained pose fitting with bone-length preservation and global alignment."""
import numpy as np
from typing import Optional
from scipy.optimize import minimize

from app.domain.models import Pose2D, Pose3D, Joint3D, JointState
from app.optimization.reprojection import compute_reprojection_error, build_camera_matrix, project_points
from app.optimization.interfaces import PoseFitter

SKELETON_BONES = [
    ("pelvis","lower_spine"),("lower_spine","upper_spine"),("upper_spine","neck"),("neck","head"),
    ("neck","left_shoulder"),("neck","right_shoulder"),
    ("left_shoulder","left_elbow"),("right_shoulder","right_elbow"),
    ("left_elbow","left_wrist"),("right_elbow","right_wrist"),
    ("left_wrist","left_hand"),("right_wrist","right_hand"),
    ("pelvis","left_hip"),("pelvis","right_hip"),
    ("left_hip","left_knee"),("right_hip","right_knee"),
    ("left_knee","left_ankle"),("right_knee","right_ankle"),
    ("left_ankle","left_heel"),("right_ankle","right_heel"),
    ("left_heel","left_foot"),("right_heel","right_foot"),
]

CORE_JOINTS = [
    "pelvis","lower_spine","upper_spine","neck",
    "left_shoulder","right_shoulder","left_elbow","right_elbow",
    "left_wrist","right_wrist","left_hip","right_hip",
    "left_knee","right_knee","left_ankle","right_ankle",
]

DEPENDENT_PARENTS = {
    "head": "neck", "left_hand": "left_wrist", "right_hand": "right_wrist",
    "left_heel": "left_ankle", "right_heel": "right_ankle",
    "left_foot": "left_ankle", "right_foot": "right_ankle",
}


def compute_raw_bone_lengths(pose):
    lengths = {}
    for j1, j2 in SKELETON_BONES:
        p1, p2 = pose.joints.get(j1), pose.joints.get(j2)
        if p1 and p2:
            d = np.sqrt((p1.x-p2.x)**2 + (p1.y-p2.y)**2 + (p1.z-p2.z)**2)
            lengths[(j1, j2)] = d
    return lengths


def compute_reprojection_rme(pose3d, pose2d, camera_params):
    err, _ = compute_reprojection_error(pose3d, pose2d, camera_params)
    return float(np.sqrt(err))


def geometric_connectivity(pose):
    """Check actual geometric connectivity, not just key presence."""
    missing = []; zero_len = []; excess_len = []; nonfinite = []
    scale = 1.0
    vals = [(j.x, j.y, j.z) for j in pose.joints.values()]
    if vals:
        xs, ys, zs = zip(*vals)
        scale = max(max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs), 0.1)
    for j1, j2 in SKELETON_BONES:
        if j1 not in pose.joints: missing.append(j1)
        if j2 not in pose.joints: missing.append(j2)
        if j1 in pose.joints and j2 in pose.joints:
            p1, p2 = pose.joints[j1], pose.joints[j2]
            d = np.sqrt((p1.x-p2.x)**2 + (p1.y-p2.y)**2 + (p1.z-p2.z)**2)
            if d < 0.0001:
                zero_len.append(f"{j1}->{j2}")
            if d > scale * 2:
                excess_len.append(f"{j1}->{j2} ({d:.2f} > {scale*2:.2f})")
    for jid, j in pose.joints.items():
        if not np.isfinite(j.x) or not np.isfinite(j.y) or not np.isfinite(j.z):
            nonfinite.append(jid)
    connected = len(missing) == 0 and len(zero_len) == 0 and len(nonfinite) == 0
    return connected, {"missing": missing, "zero_length": zero_len, "excessive": excess_len, "nonfinite": nonfinite}


DEFAULT_REST_VECTORS = {
    "head": (0, 0.12, 0), "left_hand": (0.03, -0.05, 0), "right_hand": (-0.03, -0.05, 0),
    "left_heel": (0, -0.02, 0.01), "right_heel": (0, -0.02, -0.01),
    "left_foot": (0.02, -0.03, 0.01), "right_foot": (-0.02, -0.03, -0.01),
}


def recompute_dependents_scale_aware(pose, rest_vectors=None):
    """Recompute dependent joints preserving original rest lengths and directions."""
    if rest_vectors is None:
        rest_vectors = {}
        for dep, parent in DEPENDENT_PARENTS.items():
            p, d = pose.joints.get(parent), pose.joints.get(dep)
            if p and d:
                rv = (d.x - p.x, d.y - p.y, d.z - p.z)
                length = np.sqrt(rv[0]**2 + rv[1]**2 + rv[2]**2)
                rest_vectors[dep] = rv if length > 0.001 else DEFAULT_REST_VECTORS.get(dep, (0, -0.03, 0))
    for dep, parent in DEPENDENT_PARENTS.items():
        p = pose.joints.get(parent)
        j = pose.joints.get(dep)
        if p and j and not j.locked and not j.manually_corrected:
            rv = rest_vectors.get(dep, DEFAULT_REST_VECTORS.get(dep, (0, -0.03, 0)))
            j.x = p.x + rv[0]; j.y = p.y + rv[1]; j.z = p.z + rv[2]
    return pose


def auto_scale_pose(pose3d, pose2d):
    img_w, img_h = pose2d.image_width or 1000, pose2d.image_height or 1000
    detected = [j for j in pose2d.joints.values() if j.detected]
    if len(detected) < 3: return pose3d, 1.0, 0, 0
    xs2 = [j.x for j in detected]; ys2 = [j.y for j in detected]
    cx2 = (max(xs2)+min(xs2))/2; cy2 = (max(ys2)+min(ys2))/2
    vals = [(j.x,j.y,j.z) for j in pose3d.joints.values()]
    if not vals: return pose3d, 1.0, 0, 0
    xs3, ys3, zs3 = zip(*vals)
    cx3 = (max(xs3)+min(xs3))/2; cy3 = (max(ys3)+min(ys3))/2
    bbox_w3 = max(xs3)-min(xs3); bbox_h3 = max(ys3)-min(ys3)
    bbox_w2 = max(xs2)-min(xs2); bbox_h2 = max(ys2)-min(ys2)
    if bbox_w3 < 0.01 or bbox_h3 < 0.01: return pose3d, 1.0, 0, 0
    scale = (max(bbox_w2, bbox_h2) / max(bbox_w3, bbox_h3)) * 0.5
    scale = max(0.01, min(100.0, scale))
    new = Pose3D()
    for jid, j in pose3d.joints.items():
        new.joints[jid] = Joint3D(jid, j.x*scale, j.y*scale, j.z*scale, j.confidence, j.state, j.locked, j.manually_corrected)
    return new, scale, cx2 - cx3*scale, cy2 - cy3*scale


class ScipyPoseFitter(PoseFitter):
    def __init__(self):
        self.bone_length_tolerance = 0.5
        self.max_normalized_rme = 0.35

    def fit(self, pose2d, pose3d, camera_params=None):
        img_w, img_h = pose2d.image_width or 1000, pose2d.image_height or 1000
        img_diag = np.sqrt(img_w**2 + img_h**2)

        scaled, scale_factor, global_tx, global_ty = auto_scale_pose(pose3d, pose2d)
        rest_lengths = compute_raw_bone_lengths(scaled)
        dep_rest_vectors = {}
        for dep, parent in DEPENDENT_PARENTS.items():
            p, d = scaled.joints.get(parent), scaled.joints.get(dep)
            if p and d:
                rv = (d.x - p.x, d.y - p.y, d.z - p.z)
                length = np.sqrt(rv[0]**2 + rv[1]**2 + rv[2]**2)
                if length > 0.001:
                    dep_rest_vectors[dep] = rv

        joint_order = [j for j in CORE_JOINTS if j in scaled.joints]
        n = len(joint_order)

        # Variables: [global_scale, global_tx, global_ty, dz_i, dx_i for each core joint]
        # global_scale: 1x, global_tx: 1x, global_ty: 1x, per joint: dz + dx_adj
        n_global = 3
        x0 = np.zeros(n_global + n * 2, dtype=np.float64)
        bounds = [(0.5, 2.0), (-500.0, 500.0), (-500.0, 500.0)] + [(-500.0, 500.0), (-20.0, 20.0)] * n

        if camera_params is None:
            camera_params = {
                "focal_length": max(img_w, img_h) * 1.2, "cx": img_w/2, "cy": img_h/2,
                "azimuth": 0, "elevation": 0, "roll": 0, "tx": 0, "ty": 0,
                "tz": max(img_w, img_h) * 2.0,
            }

        joint_weights = {}
        for jid, j in pose2d.joints.items():
            w = 3.0 if j.detected and j.confidence > 0.5 else (1.0 if j.detected else 0.1)
            joint_weights[jid] = w

        def build_pose(params):
            gs = params[0]; gtx = params[1]; gty = params[2]
            pose = Pose3D()
            for i, jid in enumerate(joint_order):
                ref = scaled.joints[jid]
                dz = params[n_global + i*2]
                dx = params[n_global + i*2 + 1]
                pose.joints[jid] = Joint3D(jid,
                    ref.x*gs + dx + gtx, ref.y*gs + gty, ref.z*gs + dz,
                    ref.confidence, ref.state, ref.locked, ref.manually_corrected)
            for jid, j in scaled.joints.items():
                if jid not in pose.joints:
                    pose.joints[jid] = Joint3D(jid, j.x, j.y, j.z, j.confidence, j.state, j.locked, j.manually_corrected)
            recompute_dependents_scale_aware(pose, dep_rest_vectors)
            return pose

        def objective(params):
            pose = build_pose(params)
            error, _ = compute_reprojection_error(pose, pose2d, camera_params, joint_weights)
            gs = params[0]
            cur = compute_raw_bone_lengths(pose)
            bone_penalty = 0.0
            for bone, rest in rest_lengths.items():
                cur_len = cur.get(bone, 0)
                # Normalize current length by global scale for rest comparison
                normed = cur_len / max(gs, 0.01) if cur_len > 0.0001 else 0
                if normed > 0.0001 and rest > 0.0001:
                    dev = abs(normed - rest) / rest
                    if dev > self.bone_length_tolerance:
                        bone_penalty += (dev - self.bone_length_tolerance)**2 * 100.0
                elif rest > 0.0001 and cur_len <= 0.0001:
                    bone_penalty += 1000.0  # collapsed bone
            depth_penalty = sum(params[n_global + i*2]**2 for i in range(n)) * 0.001
            return float(error) + bone_penalty + depth_penalty

        result = minimize(objective, x0, method="L-BFGS-B", bounds=bounds,
                          options={"maxiter": 300, "ftol": 1e-6})

        optimized = build_pose(result.x)
        rme = compute_reprojection_rme(optimized, pose2d, camera_params)
        norm_rme = rme / max(img_diag, 1)

        connected, conn_detail = geometric_connectivity(optimized)
        cur_lengths = compute_raw_bone_lengths(optimized)
        max_dev = 0.0; deviating = []
        for bone, rest in rest_lengths.items():
            cur_len = cur_lengths.get(bone, 0)
            if cur_len > 0.0001 and rest > 0.0001:
                dev = abs(cur_len - rest) / rest
                if dev > max_dev: max_dev = dev
                if dev > self.bone_length_tolerance:
                    deviating.append(f"{bone[0]}->{bone[1]}")
        # Only major bones (not hand/foot/heels) must be non-zero
        major_zero = any(l <= 0.0001 for b, l in cur_lengths.items()
                        if not any(h in str(b[1]) for h in ["hand", "heel", "foot"]))
        quality_passed = (
            connected and not major_zero and
            len(conn_detail.get("missing", [])) == 0 and
            norm_rme <= self.max_normalized_rme and max_dev <= self.bone_length_tolerance * 2.5
        )
        optimizer_converged = bool(result.success) or result.nit > 0
        fit_succeeded = optimizer_converged and quality_passed

        quality_failures = []
        if not connected:
            for k, v in conn_detail.items():
                if v: quality_failures.append(f"{k}: {v[:3]}")
        if major_zero: quality_failures.append("zero_length_major_bones")
        if norm_rme > self.max_normalized_rme:
            quality_failures.append(f"norm_rme={norm_rme:.4f}")
        if max_dev > self.bone_length_tolerance * 2.5:
            quality_failures.append(f"max_bone_dev={max_dev:.2f}")

        if fit_succeeded:
            final_pose = optimized
        else:
            final_pose = scaled
            for jid, j in scaled.joints.items():
                final_pose.joints[jid] = Joint3D(jid, j.x, j.y, j.z, j.confidence, j.state, j.locked, j.manually_corrected)
            recompute_dependents_scale_aware(final_pose, dep_rest_vectors)

        # Preserve original states
        for jid, j in final_pose.joints.items():
            orig = scaled.joints.get(jid)
            if orig:
                j.state = orig.state; j.manually_corrected = orig.manually_corrected; j.locked = orig.locked

        info = {
            "fitter": "ScipyPoseFitter_v2",
            "optimizer_converged": optimizer_converged,
            "quality_passed": quality_passed,
            "fit_succeeded": fit_succeeded,
            "fallback_used": not fit_succeeded,
            "initial_error": float(objective(x0)),
            "final_error": float(result.fun),
            "reprojection_rme": float(rme),
            "normalized_rme": float(norm_rme),
            "max_bone_deviation": float(max_dev),
            "invalid_bones": deviating,
            "disconnected_bones": conn_detail.get("missing", []),
            "quality_failures": quality_failures,
            "iterations": result.nit if hasattr(result, "nit") else 0,
            "scale_factor": float(scale_factor),
            "global_scale": float(result.x[0]),
            "global_tx": float(result.x[1]),
            "global_ty": float(result.x[2]),
        }
        return final_pose, info
