from dataclasses import dataclass
from enum import Enum


class PackType(Enum):
    NONE = "none"
    ONE_IMAGE = "1img"
    TWO_IMAGE = "2img"
    THREE_IMAGE = "3img"
    FULL = "full"


class OverwritePolicy(Enum):
    PROMPT = "prompt"
    OVERWRITE = "overwrite"
    NUMBERED = "numbered"


@dataclass
class ExportCamera:
    azimuth: float = 0.0
    elevation: float = 15.0
    roll: float = 0.0
    focal_px: float = 1500.0
    sensor_width_mm: float = 36.0
    distance: float = 0.0
    shift_x: float = 0.0
    shift_y: float = 0.0
    source_width: int = 0
    source_height: int = 0

    @property
    def blender_lens_mm(self) -> float:
        sw = max(self.source_width, 1)
        return self.focal_px * self.sensor_width_mm / sw


@dataclass
class ExportRequest:
    profile_key: str
    image_format: str
    width: int
    height: int
    jpeg_quality: int
    transparent: bool
    output_path: str
    pack_type: PackType
    camera: str = "source_matched"
    overwrite: OverwritePolicy = OverwritePolicy.PROMPT
    background_color: tuple[int, int, int] = (240, 240, 240)
    camera_azimuth: float = 0.0
    camera_elevation: float = 15.0
    camera_roll: float = 0.0
    camera_distance: float = 0.0
    camera_focal_length: float = 1500.0
    camera_shift_x: float = 0.0
    camera_shift_y: float = 0.0
    source_width: int = 0
    source_height: int = 0

    @property
    def export_camera(self) -> ExportCamera:
        return ExportCamera(
            azimuth=self.camera_azimuth,
            elevation=self.camera_elevation,
            roll=self.camera_roll,
            focal_px=self.camera_focal_length,
            distance=self.camera_distance,
            shift_x=self.camera_shift_x,
            shift_y=self.camera_shift_y,
            source_width=self.source_width or self.width,
            source_height=self.source_height or self.height,
        )
