from dataclasses import dataclass, field
from typing import Optional

from app.domain.models import Pose2D, Pose3D


@dataclass
class PreflightCheck:
    name: str
    passed: bool
    severity: str  # "critical", "warning", "info"
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
) -> PreflightResult:
    checks: list[PreflightCheck] = []
    critical_failures = 0

    # Check 1: Pose exists
    if pose2d is None:
        checks.append(PreflightCheck("pose_2d_exists", False, "critical", "No 2D pose data"))
        critical_failures += 1
    else:
        checks.append(PreflightCheck("pose_2d_exists", True, "info", "2D pose data present"))

    # Check 2: 3D pose exists
    if pose3d is None:
        checks.append(PreflightCheck("pose_3d_exists", False, "critical", "No 3D pose data"))
        critical_failures += 1
    else:
        n_joints = len(pose3d.joints)
        checks.append(PreflightCheck("pose_3d_exists", True, "info", f"{n_joints} 3D joints"))

    # Check 3: Critical joints present
    critical_joints = ["pelvis", "neck", "head", "left_shoulder", "right_shoulder"]
    if pose2d:
        missing = [j for j in critical_joints if j not in pose2d.joints or not pose2d.joints[j].detected]
        if missing:
            checks.append(PreflightCheck("critical_joints", False, "warning", f"Missing joints: {missing}"))
        else:
            checks.append(PreflightCheck("critical_joints", True, "info", "All critical joints present"))

    # Check 4: Resolution valid
    if resolution[0] < 64 or resolution[1] < 64:
        checks.append(PreflightCheck("resolution", False, "critical", "Resolution too small"))
        critical_failures += 1
    else:
        checks.append(PreflightCheck("resolution", True, "info", f"Resolution: {resolution[0]}x{resolution[1]}"))

    # Check 5: Low confidence joints
    if pose2d:
        low_conf = [j.joint_id for j in pose2d.joints.values() if j.detected and j.confidence < 0.3]
        if low_conf:
            checks.append(PreflightCheck("low_confidence", False, "warning", f"Low confidence: {low_conf}"))
        else:
            checks.append(PreflightCheck("low_confidence", True, "info", "No low-confidence joints"))

    return PreflightResult(
        all_passed=critical_failures == 0,
        checks=checks,
    )
