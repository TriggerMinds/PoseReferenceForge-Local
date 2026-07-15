import subprocess, os
from pathlib import Path
from app.config.settings import Settings
from app.exporters.render_profiles import RenderConfig, RenderProfile


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
        azimuth: float = 0,
        elevation: float = 15,
        distance: float = 0,
        roll: float = 0,
        focal_px: float = 1500,
        source_w: int = 0,
        source_h: int = 0,
        shift_x: float = 0,
        shift_y: float = 0,
    ) -> tuple[bool, str]:
        script_path = Path(__file__).parent.parent.parent / "blender" / "scripts" / "render_mannequin.py"
        if not script_path.exists():
            return False, f"Script not found: {script_path}"
        blender_exe = self.blender_path
        if not blender_exe:
            return False, "Blender not found"

        is_jpeg = config.format.upper() in ("JPEG", "JPG")
        profile_key = config.profile.value if hasattr(config.profile, "value") else str(config.profile)

        cmd = [
            blender_exe, "--background", "--python", str(script_path), "--",
            "--pose_json", pose_json_path.replace("\\", "/"),
            "--output", output_path.replace("\\", "/"),
            "--width", str(config.width),
            "--height", str(config.height),
            "--background_r", str(config.background_color[0] / 255),
            "--background_g", str(config.background_color[1] / 255),
            "--background_b", str(config.background_color[2] / 255),
            "--transparent", "1" if config.transparent else "0",
            "--jpeg", "1" if is_jpeg else "0",
            "--quality", str(config.jpeg_quality),
            "--azimuth", str(azimuth),
            "--elevation", str(elevation),
            "--distance", str(distance),
            "--roll", str(roll),
            "--focal", str(focal_px),
            "--source_w", str(source_w),
            "--source_h", str(source_h),
            "--shift_x", str(shift_x),
            "--shift_y", str(shift_y),
            "--profile", profile_key,
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
