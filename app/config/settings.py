import json
import os
from pathlib import Path


class Settings:
    _instance = None

    def __init__(self):
        self._data = {}
        self._config_dir = Path.home() / ".posereferenceforge"
        self._config_file = self._config_dir / "settings.json"
        self._load()

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = Settings()
        return cls._instance

    def _load(self):
        self._config_dir.mkdir(parents=True, exist_ok=True)
        if self._config_file.exists():
            try:
                with open(self._config_file) as f:
                    self._data = json.load(f)
            except Exception:
                self._data = self._defaults()
        else:
            self._data = self._defaults()
            self._save()

    def _save(self):
        with open(self._config_file, "w") as f:
            json.dump(self._data, f, indent=2)

    def _defaults(self) -> dict:
        return {
            "blender_path": "",
            "models_dir": str(Path.cwd() / "models"),
            "projects_dir": str(Path.home() / "PoseReferenceForge" / "projects"),
            "cache_dir": str(Path.home() / "PoseReferenceForge" / "cache"),
            "export_dir": str(Path.home() / "PoseReferenceForge" / "exports"),
            "library_db": str(Path.home() / "PoseReferenceForge" / "library.db"),
            "recent_projects": [],
            "recent_images": [],
            "default_model": "yolov8n-pose.pt",
            "gpu_enabled": True,
            "gpu_device": "cuda:0",
            "language": "en",
            "theme": "dark",
            "max_recent": 10,
        }

    def get_val(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value):
        self._data[key] = value
        self._save()

    @property
    def blender_path(self) -> str:
        path = self._data.get("blender_path", "")
        if path and os.path.exists(path):
            return path
        # Auto-detect common paths
        candidates = [
            "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe",
            "C:\\Program Files\\Blender Foundation\\Blender 4.2\\blender.exe",
            "C:\\Program Files\\Blender Foundation\\Blender 4.1\\blender.exe",
            "C:\\Program Files\\Blender Foundation\\Blender\\blender.exe",
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        return ""

    @property
    def models_dir(self) -> Path:
        return Path(self._data.get("models_dir", str(Path.cwd() / "models")))

    @property
    def projects_dir(self) -> Path:
        return Path(self._data.get("projects_dir", str(Path.home() / "PoseReferenceForge" / "projects")))

    @property
    def cache_dir(self) -> Path:
        return Path(self._data.get("cache_dir", str(Path.home() / "PoseReferenceForge" / "cache")))
