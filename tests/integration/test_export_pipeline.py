import pytest
import sys, os, json, shutil, tempfile
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.pose2d.detection_pipeline import run_detection
from app.pose3d.lifting_pipeline import lift_to_3d
from app.exporters.export_request import ExportRequest, PackType
from app.exporters.export_service import ExportService, ExportError
from app.rendering.blender_renderer import BlenderRenderer
from app.exporters.pack_exporter import compute_checksum

import ultralytics
ULT_DIR = os.path.dirname(ultralytics.__file__)
ASSETS_DIR = os.path.join(ULT_DIR, "assets")


def find_test_image():
    for name in ["bus.jpg", "zidane.jpg"]:
        path = os.path.join(ASSETS_DIR, name)
        if os.path.exists(path):
            return path
    return None


def get_test_pose3d():
    path = find_test_image()
    if not path:
        return None
    import cv2
    img = cv2.imread(path)
    result = run_detection(img)
    return lift_to_3d(result.pose2d), result.pose2d


@pytest.mark.skipif(not os.path.exists(ASSETS_DIR), reason="Test assets not available")
class TestExportPipeline:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.tmp = tmp_path
        self.renderer = BlenderRenderer()
        if not self.renderer.is_available():
            pytest.skip("Blender not available")
        pose3d, pose2d = get_test_pose3d()
        self.pose3d = pose3d
        self.pose2d = pose2d
        if pose3d is None:
            pytest.skip("Could not generate test pose")
        self.project_data = {
            "application_version": "1.0.0-dev",
            "project_name": "Test",
            "image_hash": "test_hash",
            "image_info": {"width": 810, "height": 1080},
        }

    def _export(self, request: ExportRequest):
        service = ExportService(self.renderer)
        return service.export(
            pose3d=self.pose3d,
            pose2d=self.pose2d,
            request=request,
            project_data=self.project_data,
        )

    def test_clean_png_export(self):
        path = str(self.tmp / "test_clean.png")
        req = ExportRequest(
            profile_key="source_matched_clean",
            image_format="PNG",
            width=1024, height=1536,
            jpeg_quality=95,
            transparent=False,
            output_path=path,
            pack_type=PackType.NONE,
        )
        result = self._export(req)
        assert os.path.exists(path), "Output file not created"
        assert os.path.getsize(path) > 1000, "Output file too small"
        assert result["format"] == "PNG"
        assert result["width"] == 1024
        assert result["height"] == 1536
        assert result["checksum"] == compute_checksum(path)
        assert os.path.exists(result["manifest_path"])

        # Validate dimensions
        errors = self._validate(path, 1024, 1536, False)
        assert len(errors) == 0, f"Validation errors: {errors}"

    def test_transparent_png_export(self):
        path = str(self.tmp / "test_transparent.png")
        req = ExportRequest(
            profile_key="transparent",
            image_format="PNG",
            width=1024, height=1536,
            jpeg_quality=95,
            transparent=True,
            output_path=path,
            pack_type=PackType.NONE,
        )
        result = self._export(req)
        assert os.path.exists(path)
        errors = self._validate(path, 1024, 1536, True)
        assert len(errors) == 0, f"Validation errors: {errors}"
        assert result["transparent"] is True

    def test_jpeg_export(self):
        path = str(self.tmp / "test_reference.jpg")
        req = ExportRequest(
            profile_key="source_matched_clean",
            image_format="JPEG",
            width=1024, height=1536,
            jpeg_quality=90,
            transparent=False,
            output_path=path,
            pack_type=PackType.NONE,
        )
        result = self._export(req)
        assert os.path.exists(path)

        # Validate JPEG format
        from PIL import Image
        img = Image.open(path)
        assert img.format == "JPEG"
        assert img.size == (1024, 1536)

    def test_depth_readable_export(self):
        path = str(self.tmp / "test_depth.png")
        req = ExportRequest(
            profile_key="depth_readable",
            image_format="PNG",
            width=1024, height=1536,
            jpeg_quality=95,
            transparent=False,
            output_path=path,
            pack_type=PackType.NONE,
        )
        result = self._export(req)
        assert os.path.exists(path)
        errors = self._validate(path, 1024, 1536, False)
        assert len(errors) == 0

    def test_manifest_generation(self):
        path = str(self.tmp / "test_manifest.png")
        req = ExportRequest(
            profile_key="source_matched_clean",
            image_format="PNG",
            width=1024, height=1536,
            jpeg_quality=95,
            transparent=False,
            output_path=path,
            pack_type=PackType.NONE,
        )
        result = self._export(req)
        manifest_path = result["manifest_path"]
        assert os.path.exists(manifest_path)

        with open(manifest_path) as f:
            manifest = json.load(f)
        assert manifest["application_version"] == "1.0.0-dev"
        assert manifest["resolution"] == [1024, 1536]
        assert manifest["output_checksum"] == result["checksum"]
        assert manifest["file_size_bytes"] > 0

    def test_missing_blender_path_raises(self):
        renderer = BlenderRenderer()
        renderer.blender_path = "C:\\nonexistent\\blender.exe"
        service = ExportService(renderer)
        path = str(self.tmp / "fail.png")
        req = ExportRequest(
            profile_key="source_matched_clean",
            image_format="PNG",
            width=1024, height=1536,
            jpeg_quality=95,
            transparent=False,
            output_path=path,
            pack_type=PackType.NONE,
        )
        with pytest.raises(ExportError):
            service.export(
                pose3d=self.pose3d,
                pose2d=self.pose2d,
                request=req,
                project_data=self.project_data,
            )

    def _validate(self, path, w, h, expect_alpha):
        errors = []
        from PIL import Image
        try:
            img = Image.open(path)
            if img.size != (w, h):
                errors.append(f"Size mismatch: {img.size} != ({w}, {h})")
            if expect_alpha and img.mode != "RGBA":
                errors.append(f"Expected RGBA, got {img.mode}")
            if img.format == "PNG":
                pass
        except Exception as e:
            errors.append(str(e))
        return errors
