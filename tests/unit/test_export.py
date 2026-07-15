import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.exporters.pack_exporter import (
    generate_pack_name,
    generate_filename,
    create_render_manifest,
)
from app.exporters.render_profiles import (
    RenderProfile, RenderConfig, ExportProfile, ImageRole, PROFILES,
)


class TestExport:
    def test_generate_pack_name(self):
        assert generate_pack_name(1) == "Pose_0001"
        assert generate_pack_name(42) == "Pose_0042"
        assert generate_pack_name(9999) == "Pose_9999"

    def test_generate_filename(self):
        name = generate_filename(1, "pose_primary")
        assert name.startswith("Pose_0001")
        assert name.endswith(".png")

    def test_render_manifest_structure(self):
        manifest = create_render_manifest(
            project_data={"application_version": "1.0.0-dev", "project_name": "Test"},
            pose3d_data={"joints": {"pelvis": {"locked": False}}},
            profile="source_matched_clean",
            image_role="POSE_PRIMARY",
            output_path="output.png",
            resolution=(1536, 2048),
            checksum="abc123",
        )
        assert manifest["application_version"] == "1.0.0-dev"
        assert manifest["render_profile"] == "source_matched_clean"
        assert manifest["image_role"] == "POSE_PRIMARY"
        assert manifest["resolution"] == [1536, 2048]

    def test_profiles_exist(self):
        assert "source_matched_clean" in PROFILES
        assert "transparent" in PROFILES
        assert "depth_readable" in PROFILES

    def test_render_config_defaults(self):
        config = RenderConfig()
        assert config.width == 1536
        assert config.height == 2048
        assert config.format == "PNG"
        assert not config.transparent
