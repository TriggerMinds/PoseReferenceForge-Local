import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.domain.models import Pose2D, Joint2D, Pose3D, Joint3D
from app.preflight.validator import run_preflight


class TestPreflight:
    def test_no_pose_data(self):
        result = run_preflight()
        assert not result.all_passed
        assert len(result.checks) >= 1
        assert any(not c.passed and c.name == "pose_2d_exists" for c in result.checks)

    def test_with_valid_pose2d(self):
        pose2d = Pose2D(image_width=100, image_height=200)
        pose2d.set_joint(Joint2D("pelvis", 50, 100, detected=True, confidence=0.9))
        pose2d.set_joint(Joint2D("neck", 50, 50, detected=True, confidence=0.9))
        pose2d.set_joint(Joint2D("head", 50, 20, detected=True, confidence=0.9))
        pose2d.set_joint(Joint2D("left_shoulder", 30, 60, detected=True, confidence=0.8))
        pose2d.set_joint(Joint2D("right_shoulder", 70, 60, detected=True, confidence=0.8))

        pose3d = Pose3D()
        pose3d.joints["pelvis"] = Joint3D("pelvis", 0, 0, 0)
        pose3d.joints["neck"] = Joint3D("neck", 0, 1, 0)

        result = run_preflight(pose2d=pose2d, pose3d=pose3d)
        assert result.all_passed

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
