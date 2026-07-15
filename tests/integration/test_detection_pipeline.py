import pytest
import sys, os, cv2, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.pose2d.detection_pipeline import run_detection
from app.pose3d.lifting_pipeline import lift_to_3d
from app.services.image_service import ImageService

import ultralytics
ult_dir = os.path.dirname(ultralytics.__file__)
ASSETS_DIR = os.path.join(ult_dir, "assets")


def find_test_image():
    for name in ["bus.jpg", "zidane.jpg"]:
        path = os.path.join(ASSETS_DIR, name)
        if os.path.exists(path):
            return path
    return None


@pytest.mark.skipif(not os.path.exists(ASSETS_DIR), reason="Test assets not available")
class TestDetectionIntegration:
    def test_detect_real_image(self):
        path = find_test_image()
        if not path:
            pytest.skip("No test image found")
        img = cv2.imread(path)
        assert img is not None, f"Could not load {path}"

        result = run_detection(img)
        assert len(result.persons) > 0
        assert len(result.pose2d.joints) > 0
        assert result.detector_name.startswith("YOLO")

    def test_3d_lifting_after_detection(self):
        path = find_test_image()
        if not path:
            pytest.skip("No test image found")
        img = cv2.imread(path)

        result = run_detection(img)
        pose3d = lift_to_3d(result.pose2d)

        assert len(pose3d.joints) > 0
        # Critical joints should exist
        for jid in ["pelvis", "neck", "head"]:
            assert jid in pose3d.joints, f"Missing critical joint: {jid}"

    def test_image_service_integration(self):
        path = find_test_image()
        if not path:
            pytest.skip("No test image found")
        arr, info = ImageService.load_image(path)
        assert arr.shape[2] == 3
        assert info["width"] > 0
        assert info["height"] > 0
