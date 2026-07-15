import subprocess
import json
import tempfile
import os
from pathlib import Path
from typing import Optional

from app.config.settings import Settings
from app.exporters.render_profiles import RenderConfig, RenderProfile


class BlenderRenderer:
    def __init__(self):
        self.settings = Settings.get()
        self._blender_path = ""

    @property
    def blender_path(self) -> str:
        if self._blender_path:
            return self._blender_path
        path = self.settings.blender_path
        if path and os.path.exists(path):
            self._blender_path = path
            return path
        return ""

    @blender_path.setter
    def blender_path(self, path: str):
        self._blender_path = path

    def is_available(self) -> bool:
        return bool(self.blender_path)

    def render(
        self,
        pose3d_data: dict,
        camera_data: dict,
        config: RenderConfig,
        output_path: str,
        timeout: int = 120,
    ) -> tuple[bool, str]:
        """
        Render a mannequin pose using Blender as a subprocess.

        Returns (success, log_output).
        """
        if not self.is_available():
            return False, "Blender not found"

        # Generate Blender Python script
        script = self._generate_blender_script(
            pose3d_data, camera_data, config, output_path
        )

        # Write to temp file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            script_path = f.name
            f.write(script)

        try:
            result = subprocess.run(
                [
                    self.blender_path,
                    "--background",
                    "--python", script_path,
                    "--render-frame", "1",
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if result.returncode == 0:
                return True, result.stdout
            return False, result.stderr
        except subprocess.TimeoutExpired:
            return False, "Render timed out"
        except Exception as e:
            return False, str(e)
        finally:
            try:
                os.unlink(script_path)
            except Exception:
                pass

    def render_with_script(
        self,
        pose_json_path: str,
        output_path: str,
        width: int = 1536,
        height: int = 2048,
        bg_color: tuple = (0.94, 0.94, 0.94),
        transparent: bool = False,
        azimuth: float = 0,
        elevation: float = 15,
        distance: float = 2.5,
    ) -> tuple[bool, str]:
        script_path = Path(__file__).parent.parent.parent / "blender" / "scripts" / "render_mannequin.py"
        if not script_path.exists():
            return False, f"Script not found: {script_path}"

        cmd = [
            self.blender_path,
            "--background",
            "--python", str(script_path),
            "--",
            "--pose_json", pose_json_path,
            "--output", output_path,
            "--width", str(width),
            "--height", str(height),
            "--background_r", str(bg_color[0]),
            "--background_g", str(bg_color[1]),
            "--background_b", str(bg_color[2]),
            "--transparent", "1" if transparent else "0",
            "--azimuth", str(azimuth),
            "--elevation", str(elevation),
            "--distance", str(distance),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                return True, result.stdout
            return False, result.stderr
        except subprocess.TimeoutExpired:
            return False, "Render timed out (300s)"
        except Exception as e:
            return False, str(e)
