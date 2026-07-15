from dataclasses import dataclass, field
from enum import Enum


class RenderProfile(str, Enum):
    SOURCE_MATCHED_CLEAN = "source_matched_clean"
    TRANSPARENT = "transparent"
    DEPTH_READABLE = "depth_readable"
    SILHOUETTE = "silhouette"
    STRUCTURAL = "structural"
    MULTI_VIEW = "multi_view"
    CUSTOM = "custom"


class ImageRole(str, Enum):
    POSE_PRIMARY = "POSE_PRIMARY"
    POSE_TRANSPARENT = "POSE_TRANSPARENT"
    POSE_DEPTH_SUPPORT = "POSE_DEPTH_SUPPORT"
    POSE_STRUCTURE_SUPPORT = "POSE_STRUCTURE_SUPPORT"
    POSE_SILHOUETTE = "POSE_SILHOUETTE"
    MULTI_VIEW = "MULTI_VIEW"
    DIAGNOSTIC_OVERLAY = "DIAGNOSTIC_OVERLAY"
    DIAGNOSTIC_SKELETON = "DIAGNOSTIC_SKELETON"
    DIAGNOSTIC_CONFIDENCE = "DIAGNOSTIC_CONFIDENCE"


@dataclass
class RenderConfig:
    profile: RenderProfile = RenderProfile.SOURCE_MATCHED_CLEAN
    width: int = 1536
    height: int = 2048
    format: str = "PNG"
    jpeg_quality: int = 95
    background_color: tuple[int, int, int] = (240, 240, 240)
    transparent: bool = False
    show_ground: bool = False
    show_grid: bool = False
    show_skeleton: bool = False
    show_labels: bool = False
    show_floor_shadow: bool = False
    mannequin_preset: str = "female_neutral"
    camera_name: str = "source_matched"
    anti_aliasing: bool = True
    safe_margins: bool = True


@dataclass
class ExportProfile:
    name: str
    role: ImageRole
    config: RenderConfig = field(default_factory=RenderConfig)


PROFILES: dict[str, ExportProfile] = {
    "source_matched_clean": ExportProfile(
        name="Source-Matched Clean",
        role=ImageRole.POSE_PRIMARY,
        config=RenderConfig(
            profile=RenderProfile.SOURCE_MATCHED_CLEAN,
            background_color=(240, 240, 240),
            transparent=False,
            show_ground=False,
            show_grid=False,
        ),
    ),
    "transparent": ExportProfile(
        name="Transparent",
        role=ImageRole.POSE_TRANSPARENT,
        config=RenderConfig(
            profile=RenderProfile.TRANSPARENT,
            transparent=True,
            show_ground=False,
            show_grid=False,
        ),
    ),
    "depth_readable": ExportProfile(
        name="Depth-Readable",
        role=ImageRole.POSE_DEPTH_SUPPORT,
        config=RenderConfig(
            profile=RenderProfile.DEPTH_READABLE,
            background_color=(200, 200, 210),
            show_ground=False,
            show_grid=False,
        ),
    ),
}
