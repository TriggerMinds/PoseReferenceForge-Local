import json
import os
import tempfile
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

from app.domain.models import Pose3D, Pose2D
from app.exporters.export_request import ExportRequest, PackType
from app.exporters.render_profiles import RenderConfig, RenderProfile
from app.exporters.pack_exporter import create_render_manifest, compute_checksum
from app.preflight.validator import run_preflight, PreflightResult
from app.rendering.blender_renderer import BlenderRenderer
from app.persistence.project_repository import ProjectRepository


class ExportError(Exception):
    pass


class ExportService:
    def __init__(self, blender_renderer: BlenderRenderer):
        self.renderer = blender_renderer
        self.repo = ProjectRepository()

    @staticmethod
    def resolve_profile(request: ExportRequest) -> RenderConfig:
        profile_map = {
            "source_matched_clean": RenderConfig(
                profile=RenderProfile.SOURCE_MATCHED_CLEAN,
                background_color=(240, 240, 240),
                transparent=False,
            ),
            "transparent": RenderConfig(
                profile=RenderProfile.TRANSPARENT,
                transparent=True,
            ),
            "depth_readable": RenderConfig(
                profile=RenderProfile.DEPTH_READABLE,
                background_color=(200, 200, 210),
                transparent=False,
            ),
            "silhouette": RenderConfig(
                profile=RenderProfile.SILHOUETTE,
                background_color=(255, 255, 255),
                transparent=False,
                show_ground=False,
                show_grid=False,
            ),
            "structural": RenderConfig(
                profile=RenderProfile.STRUCTURAL,
                background_color=(240, 240, 240),
                transparent=False,
                show_ground=True,
                show_skeleton=True,
            ),
            "multi_view": RenderConfig(
                profile=RenderProfile.MULTI_VIEW,
                background_color=(240, 240, 240),
                transparent=False,
            ),
        }
        base = profile_map.get(request.profile_key, profile_map["source_matched_clean"])
        base.width = request.width
        base.height = request.height
        if request.image_format.upper() in ("JPEG", "JPG"):
            base.format = "JPEG"
            base.jpeg_quality = request.jpeg_quality
        else:
            base.format = "PNG"
        base.transparent = request.transparent or base.transparent
        if request.background_color:
            base.background_color = request.background_color
        return base

    def run_preflight(
        self, pose2d: Optional[Pose2D], pose3d: Optional[Pose3D], request: ExportRequest
    ) -> PreflightResult:
        return run_preflight(
            pose2d=pose2d,
            pose3d=pose3d,
            resolution=(request.width, request.height),
            profile=request.profile_key,
        )

    def export(
        self,
        pose3d: Pose3D,
        pose2d: Optional[Pose2D],
        request: ExportRequest,
        project_data: dict,
    ) -> dict:
        output_path = Path(request.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Resolve overwrite policy
        if output_path.exists():
            if request.overwrite.value == "overwrite":
                pass
            elif request.overwrite.value == "numbered":
                counter = 1
                while output_path.exists():
                    stem = output_path.stem.rsplit("_", 1)[0] if "_" in output_path.stem else output_path.stem
                    output_path = output_path.parent / f"{stem}_{counter}{output_path.suffix}"
                    counter += 1
            else:
                raise ExportError(f"File exists: {output_path}")

        config = self.resolve_profile(request)

        preflight = self.run_preflight(pose2d, pose3d, request)
        if not preflight.all_passed:
            critical_checks = [c for c in preflight.checks if not c.passed and c.severity == "critical"]
            if critical_checks:
                msgs = "; ".join(c.message for c in critical_checks)
                raise ExportError(f"Preflight failed: {msgs}")

        # Write temporary pose JSON
        pose3d_data = self.repo.serialize_pose3d(pose3d)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            pose_json_path = f.name
            json.dump(pose3d_data, f, indent=2)

        try:
            success, log = self.renderer.render_from_config(
                pose_json_path=pose_json_path,
                output_path=str(output_path),
                config=config,
                azimuth=request.camera_azimuth,
                elevation=request.camera_elevation,
                distance=request.camera_distance,
                roll=request.camera_roll,
                focal_length=request.camera_focal_length,
            )
            if not success:
                raise ExportError(f"Render failed: {log}")

            if not output_path.exists():
                raise ExportError(f"Output file not created: {output_path}")

            file_size = output_path.stat().st_size
            if file_size == 0:
                raise ExportError("Output file is empty (0 bytes)")

            checksum = compute_checksum(str(output_path))

            manifest = create_render_manifest(
                project_data=project_data,
                pose3d_data=pose3d_data,
                profile=request.profile_key,
                image_role=self._role_for_profile(request.profile_key),
                output_path=str(output_path),
                resolution=(config.width, config.height),
                checksum=checksum,
            )
            manifest["file_size_bytes"] = file_size
            manifest["render_timestamp"] = datetime.now().isoformat()
            manifest["format"] = config.format
            manifest["jpeg_quality"] = config.jpeg_quality if config.format == "JPEG" else None
            manifest["alpha"] = config.transparent
            manifest["camera"] = {
                "azimuth": request.camera_azimuth,
                "elevation": request.camera_elevation,
                "roll": request.camera_roll,
                "distance": request.camera_distance,
                "focal_length": request.camera_focal_length,
            }
            pipeline = project_data.get("pose_pipeline", {})
            manifest["pose_pipeline"] = {
                "initializer": pipeline.get("initializer", ""),
                "fitter": pipeline.get("fitter", ""),
                "fit_attempted": pipeline.get("fit_attempted", False),
                "fit_succeeded": pipeline.get("fit_succeeded", False),
                "fallback_used": pipeline.get("fallback_used", False),
                "initial_error": pipeline.get("initial_error", 0),
                "final_error": pipeline.get("final_error", 0),
            }

            manifest_path = output_path.with_suffix(".manifest.json")
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)

            return {
                "output_path": str(output_path),
                "manifest_path": str(manifest_path),
                "checksum": checksum,
                "file_size": file_size,
                "width": config.width,
                "height": config.height,
                "format": config.format,
                "transparent": config.transparent,
                "preflight": {
                    "all_passed": preflight.all_passed,
                    "checks": [{"name": c.name, "passed": c.passed, "message": c.message} for c in preflight.checks],
                },
            }
        finally:
            try:
                os.unlink(pose_json_path)
            except Exception:
                pass

    def validate_output(self, output_path: str, expected_width: int, expected_height: int, expect_alpha: bool) -> list[str]:
        errors = []
        path = Path(output_path)
        if not path.exists():
            errors.append(f"File not found: {output_path}")
            return errors

        import struct
        with open(path, "rb") as f:
            header = f.read(8)

        if header[:4] == b"\x89PNG":
            errors += self._validate_png(path, expected_width, expected_height, expect_alpha)
        elif header[:2] == b"\xff\xd8":
            errors += self._validate_jpeg(path)
        else:
            errors.append(f"Unknown file format: {header[:4].hex()}")
        return errors

    def _validate_png(self, path: Path, expected_w: int, expected_h: int, expect_alpha: bool) -> list[str]:
        errors = []
        from PIL import Image
        try:
            img = Image.open(path)
            w, h = img.size
            if w != expected_w:
                errors.append(f"Width mismatch: expected {expected_w}, got {w}")
            if h != expected_h:
                errors.append(f"Height mismatch: expected {expected_h}, got {h}")
            if expect_alpha and img.mode != "RGBA":
                errors.append(f"Expected RGBA alpha channel, got mode={img.mode}")
            if not expect_alpha and img.mode not in ("RGB", "L"):
                if img.mode == "RGBA":
                    pass  # PNG may be RGBA even without transparent bg; not an error
        except Exception as e:
            errors.append(f"PNG validation error: {e}")
        return errors

    def _validate_jpeg(self, path: Path) -> list[str]:
        errors = []
        from PIL import Image
        try:
            img = Image.open(path)
            if img.format != "JPEG":
                errors.append(f"Expected JPEG format, got {img.format}")
        except Exception as e:
            errors.append(f"JPEG validation error: {e}")
        return errors

    @staticmethod
    def _role_for_profile(profile_key: str) -> str:
        roles = {
            "source_matched_clean": "POSE_PRIMARY",
            "transparent": "POSE_TRANSPARENT",
            "depth_readable": "POSE_DEPTH_SUPPORT",
            "silhouette": "POSE_SILHOUETTE",
            "structural": "POSE_STRUCTURE_SUPPORT",
            "multi_view": "MULTI_VIEW",
        }
        return roles.get(profile_key, "POSE_PRIMARY")
