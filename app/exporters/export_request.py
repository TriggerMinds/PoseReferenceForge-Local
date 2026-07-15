from dataclasses import dataclass, field
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
class ExportRequest:
    profile_key: str
    image_format: str  # "PNG" or "JPEG"
    width: int
    height: int
    jpeg_quality: int
    transparent: bool
    output_path: str
    pack_type: PackType
    camera: str = "source_matched"
    overwrite: OverwritePolicy = OverwritePolicy.PROMPT
    background_color: tuple[int, int, int] = (240, 240, 240)
