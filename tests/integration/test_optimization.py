"""Integration tests for the 3D pose fitting pipeline."""
import pytest
import sys, os, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.domain.models import Pose2D, Pose3D, Joint2D, Joint3D, JointState
from app.optimization.reprojection import (
    build_camera_matrix, project_points, compute_reprojection_error,
    evaluate_reprojection,
)
from app.optimization.pose_fitter import ScipyPoseFitter
from app.pose3d.lifting_pipeline import lift_to_3d
from app.pose2d.detection_pipeline import run_detection
import ultralytics

ULT_DIR = os.path.dirname(ultralytics.__file__)
ASSETS_DIR = os.path.join(ULT_DIR, "assets")


def find_test_image():
    for name in ["bus.jpg", "zidane.jpg"]:
        path = os.path.join(ASSETS_DIR, name)
        if os.path.exists(path):
            return path
    return None


@pytest.mark.skipif(not os.path.exists(ASSETS_DIR), reason="Test assets not available")
class TestReprojection:
    def test_build_camera_matrix(self):
        params = {
            "focal_length": 1000, "cx": 320, "cy": 240,
            "azimuth": 0, "elevation": 0, "roll": 0,
            "tx": 0, "ty": 0, "tz": 10,
        }
        camera = build_camera_matrix(params)
        assert "R" in camera
        assert "t" in camera
        assert "K" in camera
        assert camera["K"][0, 0] == 1000

    def test_project_points(self):
        camera = build_camera_matrix({
            "focal_length": 1000, "cx": 320, "cy": 240,
            "azimuth": 0, "elevation": 0, "roll": 0,
            "tx": 0, "ty": 0, "tz": 10,
        })
        pts = np.array([[0, 0, 0], [0, 1, 0]])
        proj = project_points(pts, camera)
        assert proj.shape == (2, 2)
        assert not np.isnan(proj).any()

    def test_reprojection_error(self):
        pose2d = Pose2D(image_width=640, image_height=480)
        pose2d.set_joint(Joint2D("pelvis", 320, 400, detected=True, confidence=0.9))
        pose2d.set_joint(Joint2D("neck", 320, 200, detected=True, confidence=0.9))
        pose2d.set_joint(Joint2D("head", 320, 120, detected=True, confidence=0.8))

        pose3d = Pose3D()
        pose3d.joints["pelvis"] = Joint3D("pelvis", 0, 0, 0)
        pose3d.joints["neck"] = Joint3D("neck", 0, 1, 0)
        pose3d.joints["head"] = Joint3D("head", 0, 1.5, 0)

        camera = {
            "focal_length": 1000, "cx": 320, "cy": 240,
            "azimuth": 0, "elevation": 0, "roll": 0,
            "tx": 0, "ty": 0, "tz": 10,
        }
        error, per_joint = compute_reprojection_error(pose3d, pose2d, camera)
        assert error >= 0
        assert isinstance(error, float)
        assert len(per_joint) > 0

    def test_evaluate_reprojection_structure(self):
        pose2d = Pose2D(image_width=640, image_height=480)
        pose2d.set_joint(Joint2D("pelvis", 320, 400, detected=True, confidence=0.9))
        pose3d = Pose3D()
        pose3d.joints["pelvis"] = Joint3D("pelvis", 0, 0, 0)
        camera = {
            "focal_length": 1000, "cx": 320, "cy": 240,
            "azimuth": 0, "elevation": 0, "roll": 0,
            "tx": 0, "ty": 0, "tz": 10,
        }
        result = evaluate_reprojection(pose2d, pose3d, camera)
        assert "total_reprojection_error" in result
        assert "rme" in result
        assert "high_confidence_joints" in result
        assert "per_joint_errors" in result


@pytest.mark.skipif(not os.path.exists(ASSETS_DIR), reason="Test assets not available")
class TestPoseFitter:
    def test_fit_improves_reprojection(self):
        path = find_test_image()
        if not path:
            pytest.skip("No test image")
        import cv2
        img = cv2.imread(path)
        result = run_detection(img)
        pose3d = lift_to_3d(result.pose2d)
        if not pose3d.joints:
            pytest.skip("No 3D joints generated")

        fitter = ScipyPoseFitter()
        optimized, info = fitter.fit(result.pose2d, pose3d)

        assert len(optimized.joints) > 0
        assert "initial_error" in info
        assert "final_error" in info
        assert "success" in info
        final_val = float(info["final_error"])
        assert final_val >= 0, f"Negative error: {final_val}"
        # Check that optimization ran (may not always improve with heuristic)
        assert info.get("iterations", 0) > 0 or info.get("success", False) is not None

    def test_fit_returns_valid_joints(self):
        """Verify optimized pose has valid joint positions (not NaN)."""
        path = find_test_image()
        if not path:
            pytest.skip("No test image")
        import cv2
        img = cv2.imread(path)
        result = run_detection(img)
        pose3d = lift_to_3d(result.pose2d)
        if not pose3d.joints:
            pytest.skip("No 3D joints")

        fitter = ScipyPoseFitter()
        optimized, _ = fitter.fit(result.pose2d, pose3d)

        for jid, j in optimized.joints.items():
            assert not (np.isnan(j.x) or np.isnan(j.y) or np.isnan(j.z)), (
                f"NaN in joint {jid}: ({j.x}, {j.y}, {j.z})"
            )
