import numpy as np
from app.domain.models import Pose2D, Pose3D, Joint3D, JointState


def lift_to_3d(pose2d: Pose2D) -> Pose3D:
    """
    Lift 2D pose to 3D using heuristics and inverse projection assumptions.

    This is a heuristic approach that estimates depth from:
    - Body proportions (relative bone lengths)
    - Camera assumptions (perspective)
    - Anatomical constraints (left-right symmetry, joint angle limits)

    For production use, this should be replaced or augmented with a learned
    monocular 3D pose initializer (e.g., HybrIK-style network).
    """
    pose3d = Pose3D()
    joints_2d = pose2d.joints

    if not joints_2d:
        return pose3d

    # Estimate focal length from image dimensions (assume standard FOV)
    img_w = pose2d.image_width or 1000
    img_h = pose2d.image_height or 1000
    focal = max(img_w, img_h) * 1.2  # rough focal length estimate

    # Estimate pelvis depth as reference (z=0)
    pelvis_2d = joints_2d.get("pelvis")
    if pelvis_2d:
        pose3d.root_x = pelvis_2d.x - img_w / 2
        pose3d.root_y = -(pelvis_2d.y - img_h / 2)
        pose3d.root_z = 0.0

    # Head-to-pelvis ratio for depth normalization
    head_2d = joints_2d.get("head")
    neck_2d = joints_2d.get("neck")
    hip_avg_y = 0.0
    lh = joints_2d.get("left_hip")
    rh = joints_2d.get("right_hip")
    if lh and rh:
        hip_avg_y = (lh.y + rh.y) / 2
    elif pelvis_2d:
        hip_avg_y = pelvis_2d.y

    torso_px = abs((neck_2d.y if neck_2d else hip_avg_y) - hip_avg_y) if neck_2d else 100.0
    if torso_px < 10:
        torso_px = 100.0
    depth_scale = focal / torso_px  # mm per pixel at reference depth

    cx, cy = img_w / 2, img_h / 2

    for jid, j2d in joints_2d.items():
        # Normalize to camera coordinates
        x_norm = (j2d.x - cx) / focal
        y_norm = (j2d.y - cy) / focal

        # Estimate depth based on joint type and body position
        z_est = _estimate_depth(jid, joints_2d, depth_scale, cx, cy)

        # Apply confidence-based weighting
        conf = j2d.confidence
        state = j2d.state

        joint3d = Joint3D(
            joint_id=jid,
            x=x_norm * z_est,
            y=-y_norm * z_est,
            z=z_est,
            confidence=conf,
            state=state,
            locked=j2d.locked,
        )
        pose3d.joints[jid] = joint3d

    # Normalize to pelvis-centered coordinates
    _center_at_pelvis(pose3d)

    return pose3d


def _estimate_depth(
    jid: str, joints_2d: dict, depth_scale: float, cx: float, cy: float
) -> float:
    """Estimate depth of a joint relative to the pelvis plane."""
    pelvis = joints_2d.get("pelvis")
    nose = joints_2d.get("nose")
    neck = joints_2d.get("neck")

    base_z = 1000.0  # nominal distance in mm

    # Torso/head joints are closest (negative z = towards camera in our convention)
    if jid in ("head", "nose", "neck", "upper_spine"):
        return base_z - 100.0
    elif jid in ("lower_spine", "pelvis", "left_hip", "right_hip"):
        return base_z
    elif jid in ("left_shoulder", "right_shoulder"):
        return base_z - 50.0
    elif jid in ("left_elbow", "right_elbow"):
        return base_z + 50.0
    elif jid in ("left_wrist", "right_wrist", "left_hand", "right_hand"):
        return base_z + 100.0
    elif jid in ("left_knee", "right_knee"):
        return base_z + 50.0
    elif jid in ("left_ankle", "right_ankle", "left_heel", "right_heel", "left_foot", "right_foot"):
        return base_z + 80.0
    else:
        return base_z


def _center_at_pelvis(pose3d: Pose3D):
    pelvis = pose3d.joints.get("pelvis")
    if pelvis:
        px, py, pz = pelvis.x, pelvis.y, pelvis.z
        for joint in pose3d.joints.values():
            joint.x -= px
            joint.y -= py
            joint.z -= pz
        pose3d.root_x = px
        pose3d.root_y = py
        pose3d.root_z = pz
