import pytest
import sys, os, tempfile, numpy as np
from PIL import Image
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.services.image_service import ImageService, ImageImportError


class TestImageService:
    def test_validate_path_nonexistent(self):
        with pytest.raises(ImageImportError, match="not found"):
            ImageService.validate_path("/nonexistent/path.jpg")

    def test_validate_path_unsupported(self):
        with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as f:
            path = f.name
        try:
            with pytest.raises(ImageImportError, match="Unsupported"):
                ImageService.validate_path(path)
        finally:
            os.unlink(path)

    def test_load_and_hash(self):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name

        try:
            # Create a small test image
            img = Image.new("RGB", (100, 100), color="red")
            img.save(path)

            arr, info = ImageService.load_image(path)
            assert isinstance(arr, np.ndarray)
            assert arr.shape == (100, 100, 3)
            assert info["width"] == 100
            assert info["height"] == 100
            assert info["format"] == "png"

            h = ImageService.hash_image(arr)
            assert len(h) == 64  # SHA256 hex
        finally:
            os.unlink(path)

    def test_jpg_support(self):
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            path = f.name
        try:
            img = Image.new("RGB", (50, 50), color="blue")
            img.save(path, quality=95)
            arr, info = ImageService.load_image(path)
            assert arr.shape == (50, 50, 3)
        finally:
            os.unlink(path)
