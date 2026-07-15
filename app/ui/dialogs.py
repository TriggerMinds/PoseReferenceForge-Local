from PySide6 import QtWidgets, QtCore


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

        # General tab
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

        # About tab
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


class ExportDialog(QtWidgets.QDialog):
    def __init__(self, project_data: dict | None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Reference")
        self.setMinimumWidth(600)

        layout = QtWidgets.QVBoxLayout(self)

        # Export profile selection
        form = QtWidgets.QFormLayout()

        self.cb_profile = QtWidgets.QComboBox()
        self.cb_profile.addItems([
            "Source-Matched Clean",
            "Transparent PNG",
            "Depth-Readable",
            "Silhouette",
            "Structural",
            "Multi-View",
        ])
        form.addRow("Profile:", self.cb_profile)

        self.cb_format = QtWidgets.QComboBox()
        self.cb_format.addItems(["PNG", "JPG (90% quality)", "JPG (95% quality)", "JPG (80% quality)"])
        form.addRow("Format:", self.cb_format)

        self.cb_resolution = QtWidgets.QComboBox()
        self.cb_resolution.addItems([
            "1536 x 2048 (portrait)",
            "1024 x 1536 (portrait)",
            "2048 x 3072 (portrait)",
            "2048 x 1536 (landscape)",
            "1024 x 1024 (square)",
            "2048 x 2048 (square)",
        ])
        form.addRow("Resolution:", self.cb_resolution)

        layout.addLayout(form)

        # Pack options
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

        # Buttons
        buttons = QtWidgets.QDialogButtonBox()
        btn_export = buttons.addButton("Export", QtWidgets.QDialogButtonBox.AcceptRole)
        btn_cancel = buttons.addButton("Cancel", QtWidgets.QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
