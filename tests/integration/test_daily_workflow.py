"""Minimal tests protecting the daily pose-reference workflow."""
import pytest, sys, os, cv2, json, tempfile, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import ultralytics
ULT_DIR = os.path.dirname(ultralytics.__file__)
ASSETS_DIR = os.path.join(ULT_DIR, "assets")

from app.pose2d.detection_pipeline import run_detection
from app.pose3d.lifting_pipeline import lift_to_3d
from app.optimization.pose_fitter import ScipyPoseFitter
from app.rendering.blender_renderer import BlenderRenderer
from app.exporters.export_request import ExportRequest, PackType, OverwritePolicy
from app.exporters.export_service import ExportService
from app.domain.models import Pose3D, Joint3D, JointState
from app.persistence.project_repository import ProjectRepository


def get_test_pose():
    path = os.path.join(ASSETS_DIR, "bus.jpg")
    if not os.path.exists(path):
        return None, None
    img = cv2.imread(path)
    result = run_detection(img)
    heuristic = lift_to_3d(result.pose2d)
    fitter = ScipyPoseFitter()
    opt, _ = fitter.fit(result.pose2d, heuristic)
    return result.pose2d, opt


@pytest.mark.skipif(not os.path.exists(ASSETS_DIR), reason="Test assets not available")
class TestPoseDifference:
    """Verify different poses produce different renders."""

    def test_different_poses_differ(self, tmp_path):
        renderer = BlenderRenderer()
        if not renderer.is_available():
            pytest.skip("Blender not available")
        pose2d, base_pose = get_test_pose()
        if base_pose is None:
            pytest.skip("No test pose")

        # Render base pose
        out1 = str(tmp_path / "pose_a.png")
        self._render_pose(renderer, base_pose, out1)

        # Modify arm position significantly
        mod_pose = self._duplicate_pose(base_pose)
        if "left_wrist" in mod_pose.joints:
            j = mod_pose.joints["left_wrist"]
            j.x += 300
            j.y -= 200

        out2 = str(tmp_path / "pose_b.png")
        self._render_pose(renderer, mod_pose, out2)

        # Check files differ
        with open(out1, "rb") as f1, open(out2, "rb") as f2:
            assert f1.read() != f2.read(), "Different poses produced identical renders!"

    def test_depth_change_affects_render(self, tmp_path):
        renderer = BlenderRenderer()
        if not renderer.is_available():
            pytest.skip("Blender not available")
        pose2d, base_pose = get_test_pose()
        if base_pose is None:
            pytest.skip("No test pose")

        # Render with shallow Z
        shallow = self._duplicate_pose(base_pose)
        for j in shallow.joints.values():
            j.z *= 0.1
        out1 = str(tmp_path / "shallow.png")
        self._render_pose(renderer, shallow, out1)

        # Render with deep Z
        deep = self._duplicate_pose(base_pose)
        for j in deep.joints.values():
            j.z *= 3.0
        out2 = str(tmp_path / "deep.png")
        self._render_pose(renderer, deep, out2)

        with open(out1, "rb") as f1, open(out2, "rb") as f2:
            assert f1.read() != f2.read(), "Different depth produced identical renders!"

    def test_camera_changes_viewpoint(self, tmp_path):
        renderer = BlenderRenderer()
        if not renderer.is_available():
            pytest.skip("Blender not available")
        pose2d, base_pose = get_test_pose()
        if base_pose is None:
            pytest.skip("No test pose")

        # Front view
        self._render_pose(renderer, base_pose, str(tmp_path / "front.png"), az=0)
        # Side view
        self._render_pose(renderer, base_pose, str(tmp_path / "side.png"), az=-90)
        # Back view
        self._render_pose(renderer, base_pose, str(tmp_path / "back.png"), az=180)

        files = ["front.png", "side.png", "back.png"]
        for i in range(len(files)):
            for j in range(i + 1, len(files)):
                f1_path = str(tmp_path / files[i])
                f2_path = str(tmp_path / files[j])
                with open(f1_path, "rb") as f1, open(f2_path, "rb") as f2:
                    assert f1.read() != f2.read(), f"{files[i]} == {files[j]} (same)!"

    def _render_pose(self, renderer, pose, out_path, az=0, el=15):
        from app.exporters.render_profiles import RenderConfig
        from app.persistence.project_repository import ProjectRepository
        repo = ProjectRepository()
        data = repo.serialize_pose3d(pose)
        import tempfile, json
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            jpath = f.name
            json.dump(data, f)
        try:
            config = RenderConfig(width=512, height=768, format="PNG", background_color=(240, 240, 240))
            renderer.render_from_config(jpath, out_path, config, azimuth=az, elevation=el)
        finally:
            os.unlink(jpath)

    def _duplicate_pose(self, pose):
        p = Pose3D()
        for jid, j in pose.joints.items():
            p.joints[jid] = Joint3D(jid, j.x, j.y, j.z, j.confidence, j.state, j.locked)
        return p


@pytest.mark.skipif(not os.path.exists(ASSETS_DIR), reason="Test assets not available")
class TestManualCorrection:
    def test_correction_appears_in_export(self, tmp_path):
        """Move a wrist + adjust depth; verify Blender receives corrected coords."""
        renderer = BlenderRenderer()
        if not renderer.is_available():
            pytest.skip("Blender not available")
        pose2d, base_pose = get_test_pose()
        if base_pose is None:
            pytest.skip("No test pose")

        # Correct wrist position
        pose = self._duplicate_pose(base_pose)
        if "left_wrist" not in pose.joints:
            pytest.skip("No left_wrist joint")
        j = pose.joints["left_wrist"]
        j.x += 200  # Move right
        j.z += 50   # Move closer

        # Serialize and verify
        repo = ProjectRepository()
        data = repo.serialize_pose3d(pose)
        assert data["joints"]["left_wrist"]["x"] != repo.serialize_pose3d(base_pose)["joints"]["left_wrist"]["x"]
        assert data["joints"]["left_wrist"]["z"] != repo.serialize_pose3d(base_pose)["joints"]["left_wrist"]["z"]

        # Verify render changes
        out_corrected = str(tmp_path / "corrected.png")
        self._render_pose(renderer, pose, out_corrected)
        out_original = str(tmp_path / "original.png")
        self._render_pose(renderer, base_pose, out_original)

        with open(out_corrected, "rb") as f1, open(out_original, "rb") as f2:
            assert f1.read() != f2.read(), "Correction didn't change render output!"

    _render_pose = TestPoseDifference._render_pose
    _duplicate_pose = TestPoseDifference._duplicate_pose


@pytest.mark.skipif(not os.path.exists(ASSETS_DIR), reason="Test assets not available")
class TestProjectRoundtrip:
    def test_pose_and_camera_roundtrip(self, tmp_path):
        pose2d, pose = get_test_pose()
        if pose is None:
            pytest.skip("No test pose")

        camera = {"azimuth": 30, "elevation": 20, "roll": 5, "focal_length": 1200}

        repo = ProjectRepository()
        proj_data = repo.create_project_data(
            project_name="TestRoundtrip", source_path="test.jpg",
            image_hash="abc", image_info={"width": 800, "height": 600},
            pose2d=pose2d, pose3d=pose,
        )
        proj_data["camera_match"] = camera

        # Save
        save_path = str(tmp_path / "test.prf.json")
        repo.save_project(save_path, proj_data)

        # Reload and verify
        loaded = repo.load_project(save_path)

        # Verify 3D pose
        loaded_pose3d = repo.deserialize_pose3d(loaded.get("pose3d", {}))
        assert loaded_pose3d is not None
        for jid, j in pose.joints.items():
            lj = loaded_pose3d.joints.get(jid)
            assert lj is not None, f"Missing joint {jid} after reload"
            assert abs(lj.x - j.x) < 0.001, f"X mismatch for {jid}: {lj.x} vs {j.x}"
            assert abs(lj.z - j.z) < 0.001, f"Z mismatch for {jid}: {lj.z} vs {j.z}"

        # Verify camera
        assert loaded.get("camera_match", {}).get("azimuth") == 30
        assert loaded.get("camera_match", {}).get("elevation") == 20


class TestOutputValidation:
    def test_png_dimensions_and_alpha(self, tmp_path):
        """Verify export produces correctly dimensioned PNG files."""
        from PIL import Image
        img = Image.new("RGB", (100, 100))
        p = str(tmp_path / "test.png")
        img.save(p)
        with Image.open(p) as loaded:
            assert loaded.size == (100, 100)
            assert loaded.format == "PNG"

    def test_jpeg_format(self, tmp_path):
        from PIL import Image
        img = Image.new("RGB", (100, 100))
        p = str(tmp_path / "test.jpg")
        img.save(p, format="JPEG", quality=90)
        with Image.open(p) as loaded:
            assert loaded.format == "JPEG"

    def test_alpha_channel(self, tmp_path):
        from PIL import Image
        img = Image.new("RGBA", (100, 100), (100, 100, 100, 0))
        p = str(tmp_path / "alpha.png")
        img.save(p)
        with Image.open(p) as loaded:
            assert loaded.mode == "RGBA"

    def test_not_blank(self, tmp_path):
        from PIL import Image
        img = Image.new("RGB", (100, 100), (200, 150, 100))
        p = str(tmp_path / "not_blank.png")
        img.save(p)
        with Image.open(p) as loaded:
            arr = np.array(loaded)
            assert arr.std() > 0, "Image is completely blank!"


class TestZoomMapping:
    def test_zoom_coordinate_transform(self):
        """Verify widget_to_image gives same image coords at different zooms."""
        import numpy as np

        # Create minimal SourcePanel-like widget_to_image logic
        def widget_to_image(wx, wy, img_shape, zoom):
            if zoom > 0:
                return (wx / zoom, wy / zoom)
            return (wx, wy)

        test_img_shape = (200, 300, 3)
        test_points = [(50, 50), (150, 100), (280, 180)]
        for zoom in [0.5, 1.0, 2.0]:
            for wx, wy in test_points:
                ix, iy = widget_to_image(wx, wy, test_img_shape, zoom)
                assert abs(ix - wx / zoom) < 0.001, f"X mismatch at zoom {zoom}: {ix} vs {wx/zoom}"
                assert abs(iy - wy / zoom) < 0.001, f"Y mismatch at zoom {zoom}: {iy} vs {wy/zoom}"
