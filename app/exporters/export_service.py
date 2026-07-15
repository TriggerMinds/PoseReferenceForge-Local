import json, os, tempfile, uuid
from pathlib import Path
from datetime import datetime
from typing import Optional
from PIL import Image
import numpy as np

from app.domain.models import Pose3D, Pose2D
from app.domain.json_sanitizer import sanitize
from app.exporters.export_request import ExportRequest, PackType, OverwritePolicy
from app.exporters.render_profiles import RenderConfig, RenderProfile
from app.exporters.pack_exporter import create_render_manifest, compute_checksum
from app.preflight.validator import run_preflight, PreflightResult
from app.rendering.blender_renderer import BlenderRenderer
from app.persistence.project_repository import ProjectRepository


class ExportError(Exception):
    pass


class ContentValidationError(ExportError):
    pass


class ExportService:
    def __init__(self, blender_renderer: BlenderRenderer):
        self.renderer = blender_renderer
        self.repo = ProjectRepository()

    @staticmethod
    def resolve_profile(request: ExportRequest) -> RenderConfig:
        profile_map = {
            "source_matched_clean": RenderConfig(profile=RenderProfile.SOURCE_MATCHED_CLEAN, background_color=(240, 240, 240), transparent=False),
            "transparent": RenderConfig(profile=RenderProfile.TRANSPARENT, transparent=True),
            "depth_readable": RenderConfig(profile=RenderProfile.DEPTH_READABLE, background_color=(200, 200, 210), transparent=False),
            "silhouette": RenderConfig(profile=RenderProfile.SILHOUETTE, background_color=(255, 255, 255), transparent=False, show_ground=False, show_grid=False),
            "structural": RenderConfig(profile=RenderProfile.STRUCTURAL, background_color=(240, 240, 240), transparent=False, show_ground=True, show_skeleton=True),
            "multi_view": RenderConfig(profile=RenderProfile.MULTI_VIEW, background_color=(240, 240, 240), transparent=False),
        }
        base = profile_map.get(request.profile_key, profile_map["source_matched_clean"])
        base.width = request.width
        base.height = request.height
        if request.image_format.upper() in ("JPEG", "JPG"):
            base.format = "JPEG"; base.jpeg_quality = request.jpeg_quality
        else:
            base.format = "PNG"
        base.transparent = request.transparent or base.transparent
        if request.background_color:
            base.background_color = request.background_color
        return base

    def run_preflight(self, pose2d, pose3d, request, pipeline=None):
        return run_preflight(pose2d=pose2d, pose3d=pose3d,
            resolution=(request.width, request.height),
            profile=request.profile_key, pipeline=pipeline)

    def validate_content(self, path, expect_alpha=False, bg_color=(240, 240, 240)) -> list[str]:
        errors = []
        if not os.path.exists(path):
            return [f"File not found: {path}"]
        try:
            img = Image.open(path)
            arr = np.array(img)
            w, h = img.size

            if img.mode == "RGBA":
                rgb = arr[:, :, :3]
                alpha = arr[:, :, 3]
                alpha_max = int(alpha.max())
                alpha_nonzero = int((alpha > 0).sum())
                total_px = w * h
                pct_alpha = alpha_nonzero / max(total_px, 1) * 100
            else:
                rgb = arr
                alpha_max = 255
                alpha_nonzero = 0
                pct_alpha = 0.0

            if expect_alpha and alpha_nonzero == 0:
                errors.append("Transparent render has zero non-zero-alpha pixels")
            if expect_alpha and alpha_max < 200:
                errors.append(f"Alpha max too low for transparent render: {alpha_max}")

            r, g, b = rgb[:,:,0].astype(float), rgb[:,:,1].astype(float), rgb[:,:,2].astype(float)
            max_val = int(max(r.max(), g.max(), b.max()))
            min_val = int(min(r.min(), g.min(), b.min()))
            mean_lum = float(np.mean(0.299 * r + 0.587 * g + 0.114 * b))
            std_lum = float(np.std(0.299 * r + 0.587 * g + 0.114 * b))

            # Background color check
            bg_threshold = 20
            bg_r_diff = np.abs(r - bg_color[0])
            bg_g_diff = np.abs(g - bg_color[1])
            bg_b_diff = np.abs(b - bg_color[2])
            bg_mask = (bg_r_diff < bg_threshold) & (bg_g_diff < bg_threshold) & (bg_b_diff < bg_threshold)
            fg_pixels = int((~bg_mask).sum())
            fg_pct = fg_pixels / max(w * h, 1) * 100

            min_dim = 10
            rows = np.any(~bg_mask, axis=1)
            cols = np.any(~bg_mask, axis=0)
            if rows.any() and cols.any():
                ymin, ymax = np.where(rows)[0][[0, -1]]
                xmin, xmax = np.where(cols)[0][[0, -1]]
                fg_h = ymax - ymin
                fg_w = xmax - xmin
                border_margin = int(min(h, w) * 0.02)
                touches_border = ymin <= border_margin or ymax >= h-1-border_margin or xmin <= border_margin or xmax >= w-1-border_margin
            else:
                fg_h = fg_w = 0
                touches_border = True

            # Critical failures
            if max_val <= 5 and fg_pct < 10:
                errors.append(f"Render is nearly black (max={max_val}, fg={fg_pct:.1f}%)")
            if mean_lum < 3 and std_lum < 2:
                errors.append(f"Render has no meaningful content (mean_lum={mean_lum:.1f}, std={std_lum:.1f})")
            if expect_alpha is False and fg_pct < 1:
                errors.append(f"No visible foreground (fg={fg_pct:.1f}%)")
            if fg_h < min_dim or fg_w < min_dim:
                errors.append(f"Foreground too small: {fg_w}x{fg_h}")
            if touches_border and fg_pct < 90:
                errors.append("Mannequin touches image border or is absent")
        except Exception as e:
            errors.append(f"Content validation error: {e}")
        return errors

    def export(self, pose3d: Pose3D, pose2d: Optional[Pose2D], request: ExportRequest, project_data: dict) -> dict:
        output_path = Path(request.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if output_path.exists():
            if request.overwrite.value == "overwrite":
                pass
            elif request.overwrite.value == "numbered":
                c = 1
                while output_path.exists():
                    stem = output_path.stem.rsplit("_", 1)[0] if "_" in output_path.stem else output_path.stem
                    output_path = output_path.parent / f"{stem}_{c}{output_path.suffix}"; c += 1
            else:
                raise ExportError(f"File exists: {output_path}")

        config = self.resolve_profile(request)
        pipeline = project_data.get("pose_pipeline", {})
        preflight = self.run_preflight(pose2d, pose3d, request, pipeline=pipeline)
        if not preflight.all_passed:
            critical = [c for c in preflight.checks if not c.passed and c.severity == "critical"]
            if critical:
                raise ExportError("Preflight failed: " + "; ".join(c.message for c in critical))

        pose3d_data = self.repo.serialize_pose3d(pose3d)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            pose_json_path = f.name
            json.dump(pose3d_data, f)

        cam = request.export_camera

        # Atomic: render to temp filename
        temp_path = output_path.parent / (output_path.stem + ".rendering" + output_path.suffix)

        try:
            success, log = self.renderer.render_from_config(
                pose_json_path=pose_json_path, output_path=str(temp_path), config=config,
                azimuth=cam.azimuth, elevation=cam.elevation, distance=cam.distance,
                roll=cam.roll, focal_px=cam.focal_px,
                source_w=request.source_width or request.width,
                source_h=request.source_height or request.height,
                shift_x=cam.shift_x, shift_y=cam.shift_y,
            )
            if not success:
                raise ExportError(f"Render failed: {log[:1500]}")

            if not temp_path.exists():
                raise ExportError(f"Render temp file not created: {temp_path}")

            file_size = temp_path.stat().st_size
            if file_size == 0:
                raise ExportError("Output file is empty (0 bytes)")

            # Content validation
            expect_alpha = request.transparent or config.transparent or request.profile_key == "transparent"
            content_errors = self.validate_content(str(temp_path), expect_alpha=expect_alpha,
                bg_color=config.background_color)
            if content_errors:
                try:
                    temp_path.unlink()
                except Exception:
                    pass
                raise ContentValidationError("Content validation failed: " + "; ".join(content_errors))

            checksum = compute_checksum(str(temp_path))

            # Atomic rename to final path (os.replace overwrites destination)
            os.replace(str(temp_path), str(output_path))

            manifest = create_render_manifest(
                project_data=project_data, pose3d_data=pose3d_data,
                profile=request.profile_key,
                image_role=self._role_for_profile(request.profile_key),
                output_path=str(output_path), resolution=(config.width, config.height),
                checksum=checksum,
            )
            manifest["file_size_bytes"] = file_size
            manifest["render_timestamp"] = datetime.now().isoformat()
            manifest["format"] = config.format
            manifest["jpeg_quality"] = config.jpeg_quality if config.format == "JPEG" else None
            manifest["alpha"] = config.transparent or request.profile_key == "transparent"
            manifest["camera"] = {
                "azimuth": cam.azimuth, "elevation": cam.elevation,
                "roll": cam.roll, "distance": cam.distance,
                "focal_px": cam.focal_px, "blender_lens_mm": cam.blender_lens_mm,
                "sensor_width_mm": cam.sensor_width_mm,
                "shift_x": cam.shift_x, "shift_y": cam.shift_y,
                "source_width": cam.source_width, "source_height": cam.source_height,
            }
            manifest["content_validation"] = {"passed": True, "checks": content_errors}
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
                json.dump(sanitize(manifest), f, indent=2)

            return {
                "output_path": str(output_path), "manifest_path": str(manifest_path),
                "checksum": checksum, "file_size": file_size,
                "width": config.width, "height": config.height,
                "format": config.format, "transparent": config.transparent,
                "preflight": {"all_passed": preflight.all_passed,
                    "checks": [{"name": c.name, "passed": c.passed, "message": c.message} for c in preflight.checks]},
            }
        except (ContentValidationError, ExportError):
            raise
        except Exception as e:
            raise ExportError(str(e))
        finally:
            try:
                os.unlink(pose_json_path)
            except Exception:
                pass
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except Exception:
                pass

    def validate_output(self, output_path, expected_w, expected_h, expect_alpha):
        errors = []
        p = Path(output_path)
        if not p.exists():
            return [f"File not found: {output_path}"]
        from PIL import Image
        try:
            img = Image.open(output_path)
            if img.size != (expected_w, expected_h):
                errors.append(f"Size: {img.size} != ({expected_w}, {expected_h})")
            if expect_alpha and img.mode != "RGBA":
                errors.append(f"Expected RGBA, got {img.mode}")
        except Exception as e:
            errors.append(str(e))
        return errors

    @staticmethod
    def _role_for_profile(profile_key: str) -> str:
        return {"source_matched_clean": "POSE_PRIMARY", "transparent": "POSE_TRANSPARENT",
                "depth_readable": "POSE_DEPTH_SUPPORT", "silhouette": "POSE_SILHOUETTE",
                "structural": "POSE_STRUCTURE_SUPPORT", "multi_view": "MULTI_VIEW"}.get(profile_key, "POSE_PRIMARY")
