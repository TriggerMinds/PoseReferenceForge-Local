from PySide6 import QtCore
from typing import Optional

from app.domain.models import Pose3D, Pose2D
from app.exporters.export_request import ExportRequest
from app.exporters.export_service import ExportService
from app.rendering.blender_renderer import BlenderRenderer


class ExportWorker(QtCore.QThread):
    finished = QtCore.Signal(dict)
    error = QtCore.Signal(str)
    progress = QtCore.Signal(str)

    def __init__(self, pose3d: Pose3D, pose2d: Optional[Pose2D], request: ExportRequest, project_data: dict):
        super().__init__()
        self._pose3d = pose3d
        self._pose2d = pose2d
        self._request = request
        self._project_data = project_data
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            if self._cancelled:
                return

            renderer = BlenderRenderer()
            if not renderer.is_available():
                self.error.emit("Blender not found. Configure Blender path in Settings.")
                return

            self.progress.emit("Running preflight checks...")
            service = ExportService(renderer)
            preflight = service.run_preflight(self._pose2d, self._pose3d, self._request)
            if not preflight.all_passed:
                critical = [c for c in preflight.checks if not c.passed and c.severity == "critical"]
                if critical:
                    msgs = "; ".join(c.message for c in critical)
                    self.error.emit(f"Preflight failed: {msgs}")
                    return

            if self._cancelled:
                return

            self.progress.emit(f"Rendering {self._request.width}x{self._request.height}...")

            result = service.export(
                pose3d=self._pose3d,
                pose2d=self._pose2d,
                request=self._request,
                project_data=self._project_data,
            )

            if self._cancelled:
                return

            self.progress.emit("Validating output...")
            validation_errors = service.validate_output(
                result["output_path"],
                result["width"],
                result["height"],
                result["transparent"],
            )
            if validation_errors:
                result["validation_errors"] = validation_errors

            self.finished.emit(result)

        except Exception as e:
            self.error.emit(str(e))
