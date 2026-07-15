import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional


REFERENCE_ROLES_SCHEMA = {
    "POSE_PRIMARY": "Primary pose reference image",
    "POSE_TRANSPARENT": "Transparent pose reference image",
    "POSE_DEPTH_SUPPORT": "Depth-readable supporting angle",
    "POSE_STRUCTURE_SUPPORT": "Structural/skeleton support image",
    "POSE_SILHOUETTE": "Silhouette image",
    "MULTI_VIEW": "Multi-view supplementary image",
}


def generate_pack_name(pose_id: int, base_name: str = "Pose") -> str:
    return f"{base_name}_{pose_id:04d}"


def generate_filename(pose_id: int, role: str, ext: str = "png") -> str:
    name = generate_pack_name(pose_id)
    return f"{name}_{role.lower()}.{ext}"


def create_render_manifest(
    project_data: dict,
    pose3d_data: dict,
    profile: str,
    image_role: str,
    output_path: str,
    resolution: tuple[int, int],
    checksum: str,
) -> dict:
    return {
        "application_version": project_data.get("application_version", "1.0.0-dev"),
        "project_name": project_data.get("project_name", "Untitled"),
        "source_image_hash": project_data.get("image_hash", ""),
        "source_image_dimensions": [
            project_data.get("image_info", {}).get("width", 0),
            project_data.get("image_info", {}).get("height", 0),
        ],
        "render_profile": profile,
        "image_role": image_role,
        "resolution": list(resolution),
        "format": "PNG",
        "alpha": profile in ("transparent",),
        "output_path": output_path,
        "output_checksum": checksum,
        "application_timestamp": datetime.now().isoformat(),
        "pose3d_summary": {
            "joint_count": len(pose3d_data.get("joints", {})),
            "locked_joints": [
                jid for jid, j in pose3d_data.get("joints", {}).items()
                if j.get("locked")
            ],
        },
    }


def create_quality_report(
    project_data: dict,
    preflight_results: dict,
    readability_score: dict,
    pose_similarity: dict,
) -> dict:
    return {
        "application_version": project_data.get("application_version", "1.0.0-dev"),
        "project_name": project_data.get("project_name", "Untitled"),
        "preflight": preflight_results,
        "readability": readability_score,
        "pose_similarity": pose_similarity,
        "timestamp": datetime.now().isoformat(),
    }


def compute_checksum(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
