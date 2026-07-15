import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.domain.models import Pose2D, Joint2D, Pose3D, Joint3D
from app.preflight.validator import run_preflight, CRITICAL_JOINTS


class TestPreflight:
    def test_no_pose_data(self):
        result = run_preflight()
        assert not result.all_passed
        assert any(not c.passed and c.name == "pose_2d_exists" for c in result.checks)

    def test_with_valid_pose2d(self):
        pose2d = Pose2D(image_width=100, image_height=200)
        for jid in CRITICAL_JOINTS:
            pose2d.set_joint(Joint2D(jid, 50, 100, detected=True, confidence=0.9))

        pose3d = Pose3D()
        all_joints = ["pelvis", "lower_spine", "upper_spine", "neck", "head",
                     "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
                     "left_wrist", "right_wrist", "left_hand", "right_hand",
                     "left_hip", "right_hip", "left_knee", "right_knee",
                     "left_ankle", "right_ankle", "left_heel", "right_heel",
                     "left_foot", "right_foot"]
        y_pos = 0
        for jid in all_joints:
            pose3d.joints[jid] = Joint3D(jid, 0, y_pos, 0)
            y_pos += 0.1

        result = run_preflight(pose2d=pose2d, pose3d=pose3d)
        assert result.all_passed, f"Checks: {[c.message for c in result.checks if not c.passed]}"

    def test_missing_critical_joints(self):
        pose2d = Pose2D()
        pose2d.set_joint(Joint2D("nose", 50, 50, detected=True))
        # Missing pelvis, neck, etc.

        result = run_preflight(pose2d=pose2d)
        assert any(
            not c.passed and c.name == "critical_joints"
            for c in result.checks
        )

    def test_tiny_resolution(self):
        result = run_preflight(resolution=(8, 8))
        assert any(not c.passed and c.name == "resolution" for c in result.checks)
