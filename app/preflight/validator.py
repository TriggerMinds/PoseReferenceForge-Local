"""Export preflight with fit quality, connectivity and pose integrity checks."""
from dataclasses import dataclass, field
from typing import Optional, Any
import numpy as np

from app.domain.models import Pose2D, Pose3D, JointState
from app.optimization.pose_fitter import (
    compute_raw_bone_lengths as compute_bone_lengths,
    geometric_connectivity,
    SKELETON_BONES,
)


LOW_CONFIDENCE_THRESHOLD = 0.3
CRITICAL_JOINTS = ["pelvis", "neck", "head", "left_shoulder", "right_shoulder",
                   "left_hip", "right_hip", "left_knee", "right_knee",
                   "left_ankle", "right_ankle"]


@dataclass
class PreflightCheck:
    name: str
    passed: bool
    severity: str
    message: str
    details: str = ""


@dataclass
class PreflightResult:
    all_passed: bool
    checks: list[PreflightCheck] = field(default_factory=list)
    overrides: list[str] = field(default_factory=list)


def run_preflight(
    pose2d: Optional[Pose2D] = None,
    pose3d: Optional[Pose3D] = None,
    resolution: tuple[int, int] = (1536, 2048),
    profile: str = "source_matched_clean",
    pipeline: Optional[dict[str, Any]] = None,
) -> PreflightResult:
    checks: list[PreflightCheck] = []
    critical_failures = 0

    if pose2d is None:
        checks.append(PreflightCheck("pose_2d_exists", False, "critical", "No 2D pose data"))
        critical_failures += 1
    else:
        checks.append(PreflightCheck("pose_2d_exists", True, "info", "2D pose data present"))

    if pose3d is None:
        checks.append(PreflightCheck("pose_3d_exists", False, "critical", "No 3D pose data"))
        critical_failures += 1
    else:
        n_joints = len(pose3d.joints)
        checks.append(PreflightCheck("pose_3d_exists", True, "info", f"{n_joints} 3D joints"))

        # Finite coordinate check
        nonfinite = [jid for jid, j in pose3d.joints.items() if not np.isfinite(j.x) or not np.isfinite(j.y) or not np.isfinite(j.z)]
        if nonfinite:
            checks.append(PreflightCheck("finite_coords", False, "critical", f"Non-finite joints: {nonfinite}"))
            critical_failures += 1
        else:
            checks.append(PreflightCheck("finite_coords", True, "info", "All coordinates finite"))

        # Skeleton connectivity (geometric)
        connected, conn_detail = geometric_connectivity(pose3d)
        if not connected:
            all_issues = []
            # Only flag non-hand/foot zero-length as critical
            zero_major = [z for z in conn_detail.get("zero_length", [])
                         if not any(h in z for h in ["hand", "heel", "foot"])]
            if zero_major:
                all_issues.append(f"zero_major={zero_major}")
            if conn_detail.get("missing"):
                all_issues.append(f"missing={conn_detail['missing']}")
            if conn_detail.get("nonfinite"):
                all_issues.append(f"nonfinite={conn_detail['nonfinite']}")
            if all_issues:
                checks.append(PreflightCheck("skeleton_connected", False, "critical", f"Connectivity: {'; '.join(all_issues)}"))
                critical_failures += 1
            else:
                checks.append(PreflightCheck("skeleton_connected", True, "info", "Skeleton connected (minor hand/foot near zero)"))
        else:
            checks.append(PreflightCheck("skeleton_connected", True, "info", "Skeleton geometrically connected"))

        # Bone-length sanity (raw, not clamped)
        lengths = compute_bone_lengths(pose3d)
        major_bones = [b for b in lengths.keys()
                       if not any(h in b[1] for h in ["hand", "heel", "foot"])]
        zero_major = [f"{b[0]}->{b[1]}" for b in major_bones if lengths[b] < 0.001]
        zero_minor = [f"{b[0]}->{b[1]}" for b in lengths if b not in major_bones and lengths[b] < 0.001]
        if zero_major:
            checks.append(PreflightCheck("bone_lengths", False, "critical", f"Zero-length major bones: {zero_major}"))
            critical_failures += 1
        elif zero_minor:
            checks.append(PreflightCheck("bone_lengths", False, "warning", f"Short hand/foot: {zero_minor}"))
        else:
            checks.append(PreflightCheck("bone_lengths", True, "info", "Bone lengths non-zero"))

        # Body bounding-box sanity
        vals = [(j.x, j.y, j.z) for j in pose3d.joints.values()]
        if vals:
            xs, ys, zs = zip(*vals)
            bbox_size = max(max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs))
            if bbox_size > 1000:
                checks.append(PreflightCheck("bbox_sanity", False, "warning", f"Bounding box too large: {bbox_size:.0f}"))
            elif bbox_size < 0.01:
                checks.append(PreflightCheck("bbox_sanity", False, "warning", f"Bounding box too small: {bbox_size:.4f}"))
            else:
                checks.append(PreflightCheck("bbox_sanity", True, "info", f"Bounding box: {bbox_size:.2f}"))

        # Fit pipeline status
        if pipeline:
            fit_attempted = pipeline.get("fit_attempted", False)
            fit_succeeded = pipeline.get("fit_succeeded", False)
            fallback = pipeline.get("fallback_used", False)
            if not fit_attempted:
                checks.append(PreflightCheck("fit_attempted", False, "warning", "3D fitting not performed"))
            elif not fit_succeeded:
                checks.append(PreflightCheck("fit_succeeded", False, "warning", "3D fitting failed, using fallback"))
            elif fallback:
                checks.append(PreflightCheck("fit_quality", False, "warning", "Fallback pose in use"))

    # Critical joints present
    if pose2d:
        missing_joints = [j for j in CRITICAL_JOINTS if j not in pose2d.joints or not pose2d.joints[j].detected]
        if missing_joints:
            checks.append(PreflightCheck("critical_joints", False, "warning", f"Missing critical: {missing_joints}"))
        else:
            checks.append(PreflightCheck("critical_joints", True, "info", "All critical joints present"))

    # Low-confidence joint review
    low_conf = []
    if pose2d:
        for jid, j in pose2d.joints.items():
            if j.detected and j.confidence < LOW_CONFIDENCE_THRESHOLD:
                if jid in CRITICAL_JOINTS:
                    low_conf.append(jid)
    if low_conf:
        checks.append(PreflightCheck("low_confidence", False, "warning", f"Low-confidence critical: {low_conf}"))
        if any(k in low_conf for k in ("left_knee", "right_knee", "left_ankle", "right_ankle")):
            checks.append(PreflightCheck("leg_confidence", False, "warning",
                "Low confidence in lower-body joints. Full-body pose may be unreliable."))
    else:
        checks.append(PreflightCheck("low_confidence", True, "info", "No critical low-confidence joints"))

    # Resolution
    if resolution[0] < 64 or resolution[1] < 64:
        checks.append(PreflightCheck("resolution", False, "critical", "Resolution too small"))
        critical_failures += 1
    else:
        checks.append(PreflightCheck("resolution", True, "info", f"Resolution: {resolution[0]}x{resolution[1]}"))

    # Manual correction consistency
    if pose3d:
        mc_via_state = sum(1 for j in pose3d.joints.values() if j.state == JointState.MANUALLY_CORRECTED)
        mc_via_flag = sum(1 for j in pose3d.joints.values() if j.manually_corrected)
        if mc_via_state != mc_via_flag:
            checks.append(PreflightCheck("manual_correction_consistency", False, "warning",
                f"State/flag mismatch: {mc_via_state} state, {mc_via_flag} flag"))
        else:
            checks.append(PreflightCheck("manual_correction_consistency", True, "info",
                f"Manual corrections: {mc_via_state}"))

    return PreflightResult(
        all_passed=critical_failures == 0,
        checks=checks,
    )
