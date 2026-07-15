"""Orchestrate reference pack exports (1/2/3-image and full packs)."""
import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Any, Optional


class _SafeEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if hasattr(o, "value"):
            return o.value
        if isinstance(o, set):
            return list(o)
        try:
            return bool(o) if isinstance(o, (bool,)) else str(o)
        except Exception:
            return str(o)

from app.domain.models import Pose3D, Pose2D
from app.exporters.export_request import ExportRequest, PackType, OverwritePolicy
from app.exporters.export_service import ExportService
from app.exporters.pack_exporter import (
    create_render_manifest, compute_checksum, generate_pack_name,
)
from app.rendering.blender_renderer import BlenderRenderer


PACK_CAMERAS = {
    "front": {"azimuth": 0, "elevation": 10, "label": "front"},
    "front_left_45": {"azimuth": -45, "elevation": 10, "label": "front_left_45"},
    "left": {"azimuth": -90, "elevation": 10, "label": "left"},
    "rear_left_45": {"azimuth": -135, "elevation": 10, "label": "rear_left_45"},
    "rear": {"azimuth": 180, "elevation": 10, "label": "rear"},
    "rear_right_45": {"azimuth": 135, "elevation": 10, "label": "rear_right_45"},
    "right": {"azimuth": 90, "elevation": 10, "label": "right"},
    "front_right_45": {"azimuth": 45, "elevation": 10, "label": "front_right_45"},
}


class PackOrchestrator:
    def __init__(self, renderer: BlenderRenderer):
        self.renderer = renderer
        self.service = ExportService(renderer)

    def export_one_image(
        self, pose3d: Pose3D, pose2d: Optional[Pose2D],
        project_data: dict, pack_dir: str, pose_id: int,
        camera_params: Optional[dict] = None,
    ) -> list[str]:
        os.makedirs(pack_dir, exist_ok=True)
        ref_dir = os.path.join(pack_dir, "reference")
        os.makedirs(ref_dir, exist_ok=True)

        az = camera_params.get("azimuth", 0) if camera_params else 0
        el = camera_params.get("elevation", 15) if camera_params else 15

        paths = []
        req = ExportRequest(
            profile_key="source_matched_clean", image_format="PNG",
            width=1536, height=2048, jpeg_quality=95,
            transparent=False,
            output_path=os.path.join(ref_dir, f"{generate_pack_name(pose_id)}_pose_primary.png"),
            pack_type=PackType.NONE,
            overwrite=OverwritePolicy.OVERWRITE,
            camera_azimuth=az, camera_elevation=el,
        )
        result = self.service.export(pose3d, pose2d, req, project_data)
        paths.append(result["output_path"])
        self._write_role_manifest(ref_dir, pose_id, result)
        return paths

    def export_two_image(
        self, pose3d: Pose3D, pose2d: Optional[Pose2D],
        project_data: dict, pack_dir: str, pose_id: int,
        camera_params: Optional[dict] = None,
    ) -> list[str]:
        os.makedirs(pack_dir, exist_ok=True)
        ref_dir = os.path.join(pack_dir, "reference")
        support_dir = os.path.join(pack_dir, "support")
        os.makedirs(ref_dir, exist_ok=True)
        os.makedirs(support_dir, exist_ok=True)

        az = camera_params.get("azimuth", 0) if camera_params else 0
        el = camera_params.get("elevation", 15) if camera_params else 15
        paths = []

        # Primary
        req = ExportRequest(
            profile_key="source_matched_clean", image_format="PNG",
            width=1536, height=2048, jpeg_quality=95,
            transparent=False,
            output_path=os.path.join(ref_dir, f"{generate_pack_name(pose_id)}_pose_primary.png"),
            pack_type=PackType.NONE, overwrite=OverwritePolicy.OVERWRITE,
            camera_azimuth=az, camera_elevation=el,
        )
        paths.append(self.service.export(pose3d, pose2d, req, project_data)["output_path"])

        # Depth support (offset camera by 45 deg)
        req = ExportRequest(
            profile_key="depth_readable", image_format="PNG",
            width=1536, height=2048, jpeg_quality=95,
            transparent=False,
            output_path=os.path.join(support_dir, f"{generate_pack_name(pose_id)}_depth_support.png"),
            pack_type=PackType.NONE, overwrite=OverwritePolicy.OVERWRITE,
            camera_azimuth=az - 45, camera_elevation=el,
        )
        paths.append(self.service.export(pose3d, pose2d, req, project_data)["output_path"])
        return paths

    def export_three_image(
        self, pose3d: Pose3D, pose2d: Optional[Pose2D],
        project_data: dict, pack_dir: str, pose_id: int,
        camera_params: Optional[dict] = None,
    ) -> list[str]:
        os.makedirs(pack_dir, exist_ok=True)
        ref_dir = os.path.join(pack_dir, "reference")
        support_dir = os.path.join(pack_dir, "support")
        os.makedirs(ref_dir, exist_ok=True)
        os.makedirs(support_dir, exist_ok=True)

        az = camera_params.get("azimuth", 0) if camera_params else 0
        el = camera_params.get("elevation", 15) if camera_params else 15
        paths = []

        req = ExportRequest(
            profile_key="source_matched_clean", image_format="PNG",
            width=1536, height=2048, jpeg_quality=95,
            transparent=False,
            output_path=os.path.join(ref_dir, f"{generate_pack_name(pose_id)}_pose_primary.png"),
            pack_type=PackType.NONE, overwrite=OverwritePolicy.OVERWRITE,
            camera_azimuth=az, camera_elevation=el,
        )
        paths.append(self.service.export(pose3d, pose2d, req, project_data)["output_path"])

        req = ExportRequest(
            profile_key="depth_readable", image_format="PNG",
            width=1536, height=2048, jpeg_quality=95,
            transparent=False,
            output_path=os.path.join(support_dir, f"{generate_pack_name(pose_id)}_depth_support.png"),
            pack_type=PackType.NONE, overwrite=OverwritePolicy.OVERWRITE,
            camera_azimuth=az - 45, camera_elevation=el,
        )
        paths.append(self.service.export(pose3d, pose2d, req, project_data)["output_path"])

        req = ExportRequest(
            profile_key="silhouette", image_format="PNG",
            width=1536, height=2048, jpeg_quality=95,
            transparent=False,
            output_path=os.path.join(support_dir, f"{generate_pack_name(pose_id)}_silhouette.png"),
            pack_type=PackType.NONE, overwrite=OverwritePolicy.OVERWRITE,
            camera_azimuth=az, camera_elevation=el,
        )
        paths.append(self.service.export(pose3d, pose2d, req, project_data)["output_path"])
        return paths

    def export_full(
        self, pose3d: Pose3D, pose2d: Optional[Pose2D],
        project_data: dict, pack_dir: str, pose_id: int,
        camera_params: Optional[dict] = None,
    ) -> list[str]:
        os.makedirs(pack_dir, exist_ok=True)
        for sub in ["reference", "support", "multiview", "diagnostic", "data"]:
            os.makedirs(os.path.join(pack_dir, sub), exist_ok=True)

        az = camera_params.get("azimuth", 0) if camera_params else 0
        el = camera_params.get("elevation", 15) if camera_params else 15
        paths = []
        pname = generate_pack_name(pose_id)

        # Reference images
        req = ExportRequest(
            profile_key="source_matched_clean", image_format="PNG",
            width=1536, height=2048, jpeg_quality=95,
            transparent=False,
            output_path=os.path.join(pack_dir, "reference", f"{pname}_pose_primary.png"),
            pack_type=PackType.NONE, overwrite=OverwritePolicy.OVERWRITE,
            camera_azimuth=az, camera_elevation=el,
        )
        paths.append(self.service.export(pose3d, pose2d, req, project_data)["output_path"])

        req = ExportRequest(
            profile_key="transparent", image_format="PNG",
            width=1536, height=2048, jpeg_quality=95,
            transparent=True,
            output_path=os.path.join(pack_dir, "reference", f"{pname}_transparent.png"),
            pack_type=PackType.NONE, overwrite=OverwritePolicy.OVERWRITE,
            camera_azimuth=az, camera_elevation=el,
        )
        paths.append(self.service.export(pose3d, pose2d, req, project_data)["output_path"])

        # Multiview renders
        for cam_name, cam_data in PACK_CAMERAS.items():
            req = ExportRequest(
                profile_key="source_matched_clean", image_format="PNG",
                width=1024, height=1536, jpeg_quality=95,
                transparent=False,
                output_path=os.path.join(pack_dir, "multiview", f"{pname}_{cam_name}.png"),
                pack_type=PackType.NONE, overwrite=OverwritePolicy.OVERWRITE,
                camera_azimuth=cam_data["azimuth"],
                camera_elevation=cam_data["elevation"],
            )
            paths.append(self.service.export(pose3d, pose2d, req, project_data)["output_path"])

        # Write pose preset
        from app.persistence.project_repository import ProjectRepository
        repo = ProjectRepository()
        pose3d_data = repo.serialize_pose3d(pose3d)
        preset_path = os.path.join(pack_dir, "data", f"{pname}_pose_preset.json")
        with open(preset_path, "w") as f:
            json.dump(pose3d_data, f, indent=2, cls=_SafeEncoder)
        paths.append(preset_path)

        # Write keypoints
        if pose2d:
            kp_path = os.path.join(pack_dir, "data", f"{pname}_keypoints_2d.json")
            kp_data = repo.serialize_pose2d(pose2d)
            with open(kp_path, "w") as f:
                json.dump(kp_data, f, indent=2, cls=_SafeEncoder)
            paths.append(kp_path)

        kp3d_path = os.path.join(pack_dir, "data", f"{pname}_keypoints_3d.json")
        with open(kp3d_path, "w") as f:
            json.dump(pose3d_data, f, indent=2, cls=_SafeEncoder)
        paths.append(kp3d_path)

        # Write manifest
        manifest_path = os.path.join(pack_dir, "data", f"{pname}_render_manifest.json")
        checksum = compute_checksum(paths[0]) if paths else ""
        manifest = create_render_manifest(
            project_data=project_data,
            pose3d_data=pose3d_data,
            profile="full_pack",
            image_role="PACK",
            output_path=pack_dir,
            resolution=(1536, 2048),
            checksum=checksum,
        )
        manifest["pack_contents"] = paths
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2, cls=_SafeEncoder)
        paths.append(manifest_path)

        # Write README
        readme_path = os.path.join(pack_dir, "README.txt")
        with open(readme_path, "w") as f:
            f.write(f"PoseReferenceForge Local — Reference Pack\n")
            f.write(f"Pack: {pname}\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Files: {len(paths)}\n")
            f.write(f"\nReference images are pose-only references.\n")
            f.write(f"No identity, clothing, or background contamination.\n")
        paths.append(readme_path)

        return paths

    def _write_role_manifest(self, ref_dir: str, pose_id: int, result: dict):
        pname = generate_pack_name(pose_id)
        roles = [
            {"filename": f"{pname}_pose_primary.png", "role": "POSE_PRIMARY",
             "camera": "source_matched", "profile": "source_matched_clean",
             "dimensions": [result.get("width", 0), result.get("height", 0)],
             "checksum": result.get("checksum", ""), "priority": 1},
        ]
        role_path = os.path.join(os.path.dirname(ref_dir), "data", f"{pname}_reference_roles.json")
        os.makedirs(os.path.dirname(role_path), exist_ok=True)
        with open(role_path, "w") as f:
            json.dump(roles, f, indent=2)
