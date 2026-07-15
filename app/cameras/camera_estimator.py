import numpy as np
from dataclasses import dataclass
from app.domain.models import Pose2D, Pose3D


@dataclass
class CameraMatch:
    azimuth: float = 0.0
    elevation: float = 0.0
    roll: float = 0.0
    focal_length: float = 50.0
    subject_distance: float = 2.0
    sensor_width: float = 36.0
    fov: float = 40.0
    perspective: bool = True
    offset_x: float = 0.0
    offset_y: float = 0.0
    scale: float = 1.0


def estimate_camera(
    pose2d: Pose2D,
    pose3d: Pose3D,
) -> CameraMatch:
    """
    Estimate camera parameters by comparing 2D landmark projections
    with detected 2D landmarks.

    This is a heuristic initial alignment. User refinement is expected.
    """
    cam = CameraMatch()

    # Estimate body orientation from shoulder/hip line
    ls2d = pose2d.get_joint("left_shoulder")
    rs2d = pose2d.get_joint("right_shoulder")
    nose = pose2d.get_joint("nose")

    if ls2d and rs2d:
        # Shoulder line angle gives rough azimuth estimate
        dx = rs2d.x - ls2d.x
        shoulder_px = abs(dx)

        # If shoulders are narrow in 2D, body is likely side-on
        if shoulder_px < 30:
            # Side view: check nose position relative to shoulder center
            if nose and ls2d:
                offset = nose.x - ls2d.x
                if offset < -10:
                    cam.azimuth = 90.0  # facing right
                elif offset > 10:
                    cam.azimuth = -90.0  # facing left
                else:
                    cam.azimuth = 180.0  # facing away
        else:
            # Shoulder ratio indicates facing direction
            cam.azimuth = 0.0  # front-facing

    # Estimate elevation from head-to-pelvis ratio
    head = pose2d.get_joint("head")
    pelvis = pose2d.get_joint("pelvis")
    if head and pelvis:
        torso_px = abs(pelvis.y - head.y)
        img_h = pose2d.image_height or 1000
        ratio = torso_px / img_h
        if ratio < 0.2:
            cam.elevation = 30.0  # looking down
        elif ratio > 0.5:
            cam.elevation = -15.0  # looking up
        else:
            cam.elevation = 0.0

    return cam
