"""Integration tests for reference pack export."""
import pytest
import sys, os, json, cv2
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.pose2d.detection_pipeline import run_detection
from app.pose3d.lifting_pipeline import lift_to_3d
from app.optimization.pose_fitter import ScipyPoseFitter
from app.exporters.pack_orchestrator import PackOrchestrator
from app.rendering.blender_renderer import BlenderRenderer
from app.library.pose_library import PoseLibrary

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
class TestPackExport:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.tmp = tmp_path
        renderer = BlenderRenderer()
        if not renderer.is_available():
            pytest.skip("Blender not available")
        self.orchestrator = PackOrchestrator(renderer)

        path = find_test_image()
        if not path:
            pytest.skip("No test image")
        img = cv2.imread(path)
        result = run_detection(img)
        heuristic = lift_to_3d(result.pose2d)
        fitter = ScipyPoseFitter()
        pose3d, _ = fitter.fit(result.pose2d, heuristic)
        self.pose3d = pose3d
        self.pose2d = result.pose2d
        self.project_data = {
            "application_version": "1.0.0-dev",
            "project_name": "PackTest",
            "camera_match": {"azimuth": 0, "elevation": 15},
        }

    def test_one_image_pack(self):
        pack_dir = str(self.tmp / "one_image")
        paths = self.orchestrator.export_one_image(
            self.pose3d, self.pose2d, self.project_data, pack_dir, 1)
        assert len(paths) >= 1
        for p in paths:
            assert os.path.exists(p), f"Missing: {p}"
            assert os.path.getsize(p) > 1000

    def test_two_image_pack(self):
        pack_dir = str(self.tmp / "two_image")
        paths = self.orchestrator.export_two_image(
            self.pose3d, self.pose2d, self.project_data, pack_dir, 1)
        assert len(paths) >= 2
        for p in paths:
            assert os.path.exists(p)

    def test_three_image_pack(self):
        pack_dir = str(self.tmp / "three_image")
        paths = self.orchestrator.export_three_image(
            self.pose3d, self.pose2d, self.project_data, pack_dir, 1)
        assert len(paths) >= 3
        for p in paths:
            assert os.path.exists(p)

    def test_full_pack(self):
        pack_dir = str(self.tmp / "full")
        paths = self.orchestrator.export_full(
            self.pose3d, self.pose2d, self.project_data, pack_dir, 1)
        assert len(paths) >= 15  # Many renders + data files
        for p in paths:
            assert os.path.exists(p), f"Missing: {p}"
        # Check for key files
        has_png = any(p.endswith(".png") for p in paths)
        has_json = any(p.endswith(".json") for p in paths)
        has_txt = any(p.endswith(".txt") for p in paths)
        assert has_png, "No PNG files in pack"
        assert has_json, "No JSON files in pack"
        assert has_txt, "No README in pack"

    def test_deterministic_output(self):
        pack_dir1 = str(self.tmp / "det1")
        paths1 = self.orchestrator.export_one_image(
            self.pose3d, self.pose2d, self.project_data, pack_dir1, 1)
        pack_dir2 = str(self.tmp / "det2")
        paths2 = self.orchestrator.export_one_image(
            self.pose3d, self.pose2d, self.project_data, pack_dir2, 1)
        # Same pose should produce same filenames
        for p1, p2 in zip(sorted(paths1), sorted(paths2)):
            assert os.path.basename(p1) == os.path.basename(p2)


class TestPoseLibrary:
    def test_save_and_load(self, tmp_path):
        from app.domain.models import Pose3D, Joint3D
        db_path = os.path.join(str(tmp_path), "test_lib.db")
        lib = PoseLibrary(db_path)

        pose = Pose3D()
        pose.joints["pelvis"] = Joint3D("pelvis", 0, 0, 0, confidence=0.9)
        pose.joints["neck"] = Joint3D("neck", 0, 1, 0, confidence=0.8)

        pid = lib.save(name="TestPose", pose3d=pose, tags="test,standing")
        assert pid is not None

        loaded = lib.load(pid)
        assert loaded is not None
        assert len(loaded.joints) == 2
        assert loaded.joints["pelvis"].x == 0.0

    def test_search(self, tmp_path):
        db_path = os.path.join(str(tmp_path), "test_lib2.db")
        lib = PoseLibrary(db_path)
        from app.domain.models import Pose3D, Joint3D
        p = Pose3D()
        p.joints["pelvis"] = Joint3D("pelvis", 0, 0, 0)
        lib.save(name="Standing", pose3d=p, tags="standing")
        lib.save(name="Sitting", pose3d=p, tags="seated")
        results = lib.search("Standing")
        assert len(results) >= 1
        assert any(r["name"] == "Standing" for r in results)

    def test_delete_and_rename(self, tmp_path):
        db_path = os.path.join(str(tmp_path), "test_lib3.db")
        lib = PoseLibrary(db_path)
        from app.domain.models import Pose3D, Joint3D
        p = Pose3D()
        p.joints["pelvis"] = Joint3D("pelvis", 0, 0, 0)
        pid = lib.save(name="ToDelete", pose3d=p)
        assert lib.rename(pid, "Renamed")
        entries = lib.list_all()
        assert any(e["name"] == "Renamed" for e in entries)
        assert lib.delete(pid)
        assert lib.load(pid) is None

    def test_duplicate(self, tmp_path):
        db_path = os.path.join(str(tmp_path), "test_lib4.db")
        lib = PoseLibrary(db_path)
        from app.domain.models import Pose3D, Joint3D
        p = Pose3D()
        p.joints["pelvis"] = Joint3D("pelvis", 0, 0, 0)
        pid = lib.save(name="Original", pose3d=p)
        new_id = lib.duplicate(pid, "Copy")
        assert new_id is not None
        assert new_id != pid
        entries = lib.list_all()
        names = [e["name"] for e in entries]
        assert "Original" in names
        assert "Copy" in names
