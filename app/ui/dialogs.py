from PySide6 import QtWidgets, QtCore
from pathlib import Path

from app.exporters.export_request import ExportRequest, PackType, OverwritePolicy
from app.config.settings import Settings


class NewProjectDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Project")
        self.setMinimumWidth(400)
        layout = QtWidgets.QFormLayout(self)

        self.edit_name = QtWidgets.QLineEdit()
        self.edit_name.setPlaceholderText("My Pose Project")
        layout.addRow("Project Name:", self.edit_name)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def project_name(self) -> str:
        return self.edit_name.text().strip() or "Untitled"


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        self._settings = settings

        layout = QtWidgets.QVBoxLayout(self)

        tabs = QtWidgets.QTabWidget()
        layout.addWidget(tabs)

        general_tab = QtWidgets.QWidget()
        general_layout = QtWidgets.QFormLayout(general_tab)

        self.edit_blender = QtWidgets.QLineEdit(settings.blender_path)
        self.btn_browse_blender = QtWidgets.QPushButton("Browse...")
        self.btn_browse_blender.clicked.connect(self._browse_blender)
        blender_row = QtWidgets.QHBoxLayout()
        blender_row.addWidget(self.edit_blender)
        blender_row.addWidget(self.btn_browse_blender)
        general_layout.addRow("Blender Path:", blender_row)

        self.edit_projects_dir = QtWidgets.QLineEdit(settings.get_val("projects_dir", ""))
        general_layout.addRow("Projects Directory:", self.edit_projects_dir)

        self.edit_export_dir = QtWidgets.QLineEdit(settings.get_val("export_dir", ""))
        general_layout.addRow("Export Directory:", self.edit_export_dir)

        self.cb_gpu = QtWidgets.QCheckBox("Enable GPU acceleration")
        self.cb_gpu.setChecked(settings.get_val("gpu_enabled", True))
        general_layout.addRow("", self.cb_gpu)

        tabs.addTab(general_tab, "General")

        about_tab = QtWidgets.QWidget()
        about_layout = QtWidgets.QVBoxLayout(about_tab)
        about_layout.addWidget(QtWidgets.QLabel("PoseReferenceForge Local v1.0.0-dev"))
        about_layout.addWidget(QtWidgets.QLabel("Build: 2026-07-15"))
        about_layout.addStretch()
        tabs.addTab(about_tab, "About")

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_blender(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select Blender Executable", "",
            "blender.exe (blender.exe);;All Files (*.*)"
        )
        if path:
            self.edit_blender.setText(path)

    def _on_save(self):
        self._settings.set("gpu_enabled", self.cb_gpu.isChecked())
        self._settings.set("projects_dir", self.edit_projects_dir.text())
        self._settings.set("export_dir", self.edit_export_dir.text())
        if self.edit_blender.text():
            self._settings.set("blender_path", self.edit_blender.text())
        self.accept()


_PROFILE_KEYS = {
    "Source-Matched Clean": "source_matched_clean",
    "Transparent PNG": "transparent",
    "Depth-Readable": "depth_readable",
    "Silhouette": "silhouette",
    "Structural": "structural",
    "Multi-View": "multi_view",
}

_RESOLUTION_MAP = {
    "1536 x 2048 (portrait)": (1536, 2048),
    "1024 x 1536 (portrait)": (1024, 1536),
    "2048 x 3072 (portrait)": (2048, 3072),
    "2048 x 1536 (landscape)": (2048, 1536),
    "1024 x 1024 (square)": (1024, 1024),
    "2048 x 2048 (square)": (2048, 2048),
}

_FORMAT_MAP = {
    "PNG": ("PNG", False, 95),
    "JPG (90% quality)": ("JPEG", False, 90),
    "JPG (95% quality)": ("JPEG", False, 95),
    "JPG (80% quality)": ("JPEG", False, 80),
}


class ExportDialog(QtWidgets.QDialog):
    def __init__(self, project_data: dict | None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Reference")
        self.setMinimumWidth(650)

        self._project_data = project_data or {}
        self._settings = Settings.get()
        self._request: ExportRequest | None = None

        layout = QtWidgets.QVBoxLayout(self)

        form = QtWidgets.QFormLayout()

        self.cb_profile = QtWidgets.QComboBox()
        self.cb_profile.addItems(list(_PROFILE_KEYS.keys()))
        form.addRow("Profile:", self.cb_profile)

        self.cb_format = QtWidgets.QComboBox()
        self.cb_format.addItems(list(_FORMAT_MAP.keys()))
        form.addRow("Format:", self.cb_format)

        self.cb_resolution = QtWidgets.QComboBox()
        self.cb_resolution.addItems(list(_RESOLUTION_MAP.keys()))
        form.addRow("Resolution:", self.cb_resolution)

        self.edit_output = QtWidgets.QLineEdit()
        default_export_dir = self._settings.get_val("export_dir", str(Path.home() / "PoseReferenceForge" / "exports"))
        self.edit_output.setText(str(Path(default_export_dir) / "pose_reference.png"))
        self.btn_browse_output = QtWidgets.QPushButton("Browse...")
        self.btn_browse_output.clicked.connect(self._browse_output)
        output_row = QtWidgets.QHBoxLayout()
        output_row.addWidget(self.edit_output)
        output_row.addWidget(self.btn_browse_output)
        form.addRow("Output:", output_row)

        layout.addLayout(form)

        pack_group = QtWidgets.QGroupBox("AI Reference Pack")
        pack_layout = QtWidgets.QVBoxLayout(pack_group)

        self.cb_pack_1img = QtWidgets.QCheckBox("1-Image Pack (pose primary only)")
        pack_layout.addWidget(self.cb_pack_1img)

        self.cb_pack_2img = QtWidgets.QCheckBox("2-Image Pack (pose primary + depth support)")
        pack_layout.addWidget(self.cb_pack_2img)

        self.cb_pack_3img = QtWidgets.QCheckBox("3-Image Pack (pose primary + depth + structural)")
        pack_layout.addWidget(self.cb_pack_3img)

        self.cb_pack_full = QtWidgets.QCheckBox("Full Reference Pack (all views + data)")
        pack_layout.addWidget(self.cb_pack_full)

        layout.addWidget(pack_group)

        buttons = QtWidgets.QDialogButtonBox()
        btn_export = buttons.addButton("Export", QtWidgets.QDialogButtonBox.AcceptRole)
        btn_cancel = buttons.addButton("Cancel", QtWidgets.QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_output(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save Export", self.edit_output.text(),
            "Images (*.png *.jpg *.jpeg);;PNG (*.png);;JPEG (*.jpg *.jpeg);;All Files (*.*)"
        )
        if path:
            self.edit_output.setText(path)

    def _on_accept(self):
        profile_text = self.cb_profile.currentText()
        format_text = self.cb_format.currentText()
        resolution_text = self.cb_resolution.currentText()

        profile_key = _PROFILE_KEYS.get(profile_text, "source_matched_clean")
        fmt, is_jpeg, quality = _FORMAT_MAP.get(format_text, ("PNG", False, 95))
        width, height = _RESOLUTION_MAP.get(resolution_text, (1536, 2048))

        is_transparent = profile_key == "transparent" or (fmt == "PNG" and profile_key == "transparent")

        output_path = self.edit_output.text().strip()
        if not output_path:
            QtWidgets.QMessageBox.warning(self, "Output Path", "Please specify an output path.")
            return

        if fmt == "JPEG" and not output_path.lower().endswith((".jpg", ".jpeg")):
            output_path = str(Path(output_path).with_suffix(".jpg"))
        elif fmt == "PNG" and not output_path.lower().endswith(".png"):
            output_path = str(Path(output_path).with_suffix(".png"))

        pack_type = PackType.NONE
        if self.cb_pack_full.isChecked():
            pack_type = PackType.FULL
        elif self.cb_pack_3img.isChecked():
            pack_type = PackType.THREE_IMAGE
        elif self.cb_pack_2img.isChecked():
            pack_type = PackType.TWO_IMAGE
        elif self.cb_pack_1img.isChecked():
            pack_type = PackType.ONE_IMAGE

        camera_match = self._project_data.get("camera_match", {})
        self._request = ExportRequest(
            profile_key=profile_key,
            image_format=fmt,
            width=width,
            height=height,
            jpeg_quality=quality,
            transparent=is_transparent,
            output_path=output_path,
            pack_type=pack_type,
            camera_azimuth=camera_match.get("azimuth", 0.0),
            camera_elevation=camera_match.get("elevation", 15.0),
            camera_roll=camera_match.get("roll", 0.0),
            camera_focal_length=camera_match.get("focal_length", 1500.0),
        )
        self.accept()

    def get_request(self) -> ExportRequest | None:
        return self._request
