import numpy as np
from pathlib import Path
from PIL import Image, ImageOps
import filetype


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
SUPPORTED_MIMES = {"image/jpeg", "image/png", "image/webp"}


class ImageImportError(Exception):
    pass


class ImageService:

    @staticmethod
    def validate_path(path: str | Path) -> Path:
        p = Path(path)
        if not p.exists():
            raise ImageImportError(f"File not found: {p}")
        if p.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ImageImportError(f"Unsupported format: {p.suffix}. Supported: {SUPPORTED_EXTENSIONS}")
        kind = filetype.guess(str(p))
        if kind and kind.mime not in SUPPORTED_MIMES:
            raise ImageImportError(f"Unsupported MIME type: {kind.mime}")
        return p

    @staticmethod
    def load_image(path: str | Path) -> tuple[np.ndarray, dict]:
        p = ImageService.validate_path(path)
        img = Image.open(p)
        exif_data = img.getexif() if hasattr(img, "getexif") else {}

        # Apply EXIF orientation
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        # Convert to RGB numpy array
        if img.mode != "RGB":
            img = img.convert("RGB")

        arr = np.array(img, dtype=np.uint8)
        info = {
            "path": str(p.absolute()),
            "width": arr.shape[1],
            "height": arr.shape[0],
            "channels": arr.shape[2] if len(arr.shape) == 3 else 1,
            "format": p.suffix.lower().lstrip("."),
            "file_size": p.stat().st_size,
            "exif": exif_data,
        }
        return arr, info

    @staticmethod
    def hash_image(image: np.ndarray) -> str:
        import hashlib
        return hashlib.sha256(image.tobytes()).hexdigest()
