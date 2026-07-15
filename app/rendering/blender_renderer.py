import subprocess
import os
from pathlib import Path

from app.config.settings import Settings
from app.exporters.render_profiles import RenderConfig


class BlenderRenderer:
    def __init__(self):
        self.settings = Settings.get()
        self._blender_path = ""
        self._explicit_path = False

    @property
    def blender_path(self) -> str:
        if self._explicit_path:
            if self._blender_path and os.path.exists(self._blender_path):
                return self._blender_path
            return ""
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
        self._explicit_path = True

    def is_available(self) -> bool:
        return bool(self.blender_path)

    def render_from_config(
        self,
        pose_json_path: str,
        output_path: str,
        config: RenderConfig,
        timeout: int = 300,
    ) -> tuple[bool, str]:
        script_path = Path(__file__).parent.parent.parent / "blender" / "scripts" / "render_mannequin.py"
        if not script_path.exists():
            return False, f"Script not found: {script_path}"
        blender_exe = self.blender_path
        if not blender_exe:
            return False, "Blender not found"

        is_jpeg = config.format.upper() == "JPEG" or config.format.upper() == "JPG"
        cmd = [
            blender_exe,
            "--background",
            "--python", str(script_path),
            "--",
            "--pose_json", pose_json_path,
            "--output", output_path,
            "--width", str(config.width),
            "--height", str(config.height),
            "--background_r", str(config.background_color[0]),
            "--background_g", str(config.background_color[1]),
            "--background_b", str(config.background_color[2]),
            "--transparent", "1" if config.transparent else "0",
            "--jpeg", "1" if is_jpeg else "0",
            "--quality", str(config.jpeg_quality),
            "--azimuth", "0",
            "--elevation", "15",
            "--distance", "2.5",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if result.returncode == 0:
                return True, result.stdout
            stderr = result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr
            return False, stderr
        except subprocess.TimeoutExpired:
            return False, "Render timed out (300s)"
        except Exception as e:
            return False, str(e)
