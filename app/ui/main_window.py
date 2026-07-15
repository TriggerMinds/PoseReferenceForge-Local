from PySide6 import QtWidgets, QtCore, QtGui
from app.config.settings import Settings
from app.ui.source_panel import SourcePanel
from app.ui.viewport_3d import Viewport3D
from app.ui.properties_panel import PropertiesPanel
from app.ui.dialogs import NewProjectDialog, SettingsDialog


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PoseReferenceForge Local")
        self.resize(1600, 1000)
        self.settings = Settings.get()

        self._current_project_path = None
        self._current_data = None

        self._setup_actions()
        self._setup_menu_bar()
        self._setup_toolbar()
        self._setup_central_widget()
        self._setup_status_bar()

    def _setup_actions(self):
        self.act_new = QtGui.QAction("&New Project", self)
        self.act_new.setShortcut(QtGui.QKeySequence.New)
        self.act_new.triggered.connect(self._on_new_project)

        self.act_open = QtGui.QAction("&Open...", self)
        self.act_open.setShortcut(QtGui.QKeySequence.Open)
        self.act_open.triggered.connect(self._on_open_project)

        self.act_save = QtGui.QAction("&Save", self)
        self.act_save.setShortcut(QtGui.QKeySequence.Save)
        self.act_save.triggered.connect(self._on_save)

        self.act_save_as = QtGui.QAction("Save &As...", self)
        self.act_save_as.setShortcut(QtGui.QKeySequence("Ctrl+Shift+S"))
        self.act_save_as.triggered.connect(self._on_save_as)

        self.act_import = QtGui.QAction("&Import Image...", self)
        self.act_import.setShortcut(QtGui.QKeySequence("Ctrl+I"))
        self.act_import.triggered.connect(self._on_import_image)

        self.act_detect = QtGui.QAction("&Detect Pose", self)
        self.act_detect.setShortcut(QtGui.QKeySequence("Ctrl+D"))
        self.act_detect.triggered.connect(self._on_detect_pose)

        self.act_gen3d = QtGui.QAction("Generate &3D Pose", self)
        self.act_gen3d.setShortcut(QtGui.QKeySequence("Ctrl+G"))
        self.act_gen3d.triggered.connect(self._on_generate_3d)

        self.act_export = QtGui.QAction("&Export Reference...", self)
        self.act_export.setShortcut(QtGui.QKeySequence("Ctrl+E"))
        self.act_export.triggered.connect(self._on_export)

        self.act_settings = QtGui.QAction("&Settings...", self)
        self.act_settings.triggered.connect(self._on_settings)

    def _setup_menu_bar(self):
        mb = self.menuBar()
        file_menu = mb.addMenu("&File")
        file_menu.addAction(self.act_new)
        file_menu.addAction(self.act_open)
        file_menu.addSeparator()
        file_menu.addAction(self.act_save)
        file_menu.addAction(self.act_save_as)

        process_menu = mb.addMenu("&Process")
        process_menu.addAction(self.act_import)
        process_menu.addAction(self.act_detect)
        process_menu.addAction(self.act_gen3d)

        export_menu = mb.addMenu("&Export")
        export_menu.addAction(self.act_export)

        tools_menu = mb.addMenu("&Tools")
        tools_menu.addAction(self.act_settings)

    def _setup_toolbar(self):
        tb = self.addToolBar("Main")
        tb.setMovable(False)
        tb.addAction(self.act_new)
        tb.addAction(self.act_open)
        tb.addAction(self.act_save)
        tb.addSeparator()
        tb.addAction(self.act_import)
        tb.addAction(self.act_detect)
        tb.addAction(self.act_gen3d)
        tb.addSeparator()
        tb.addAction(self.act_export)

    def _setup_central_widget(self):
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        self.source_panel = SourcePanel()
        splitter.addWidget(self.source_panel)

        self.viewport_3d = Viewport3D()
        splitter.addWidget(self.viewport_3d)

        self.properties_panel = PropertiesPanel()
        splitter.addWidget(self.properties_panel)

        splitter.setSizes([500, 700, 350])
        self.setCentralWidget(splitter)

    def _setup_status_bar(self):
        self.status_bar = QtWidgets.QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QtWidgets.QLabel("Ready")
        self.status_bar.addPermanentWidget(self.status_label)

    def set_status(self, msg: str):
        self.status_label.setText(msg)
        QtWidgets.QApplication.processEvents()

    def _on_new_project(self):
        dialog = NewProjectDialog(self)
        if dialog.exec():
            name = dialog.project_name()
            self._current_data = {
                "project_name": name,
                "application_version": "1.0.0-dev",
                "schema_version": "1.0",
            }
            self._current_project_path = None
            self.setWindowTitle(f"PoseReferenceForge Local - {name}")
            self.set_status(f"New project: {name}")

    def _on_open_project(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open Project", str(self.settings.projects_dir),
            "PoseReferenceForge Project (*.prf.json);;All Files (*.*)"
        )
        if path:
            from app.persistence.project_repository import ProjectRepository
            repo = ProjectRepository()
            self._current_data = repo.load_project(path)
            self._current_project_path = path
            name = self._current_data.get("project_name", "Untitled")
            self.setWindowTitle(f"PoseReferenceForge Local - {name}")
            self.set_status(f"Opened: {path}")

            # Restore 2D data
            pose2d_data = self._current_data.get("pose2d", {})
            if pose2d_data:
                pose2d = repo.deserialize_pose2d(pose2d_data)
                self.source_panel.set_pose2d(pose2d)

            # Restore source image
            src_path = self._current_data.get("source_path", "")
            if src_path and os.path.exists(src_path):
                from app.services.image_service import ImageService
                img, info = ImageService.load_image(src_path)
                self.source_panel.set_image(img)
                self._current_data["image_info"] = info

    def _on_save(self):
        if self._current_project_path:
            self._do_save(self._current_project_path)
        else:
            self._on_save_as()

    def _on_save_as(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save Project As", str(self.settings.projects_dir),
            "PoseReferenceForge Project (*.prf.json);;All Files (*.*)"
        )
        if path:
            self._do_save(path)

    def _do_save(self, path: str):
        from app.persistence.project_repository import ProjectRepository
        if self._current_data is None:
            self._current_data = {}
        self._current_data["updated_at"] = QtCore.QDateTime.currentDateTime().toString(QtCore.Qt.ISODate)

        repo = ProjectRepository()
        # Save 2D data
        pose2d = self.source_panel.get_pose2d()
        if pose2d:
            self._current_data["pose2d"] = repo.serialize_pose2d(pose2d)

        repo.save_project(path, self._current_data)
        self._current_project_path = path
        name = self._current_data.get("project_name", "Untitled")
        self.setWindowTitle(f"PoseReferenceForge Local - {name}")
        self.set_status(f"Saved: {path}")

    def _on_import_image(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Import Image", "",
            "Images (*.jpg *.jpeg *.png *.webp);;All Files (*.*)"
        )
        if path:
            try:
                from app.services.image_service import ImageService
                img, info = ImageService.load_image(path)
                self.source_panel.set_image(img)
                if self._current_data is None:
                    self._current_data = {}
                self._current_data["source_path"] = path
                self._current_data["image_info"] = info
                self._current_data["image_hash"] = ImageService.hash_image(img)
                self.set_status(f"Imported: {path}")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Import Error", str(e))

    def _on_detect_pose(self):
        if self.source_panel.image is None:
            QtWidgets.QMessageBox.warning(self, "No Image", "Import an image first.")
            return
        self.set_status("Detecting pose...")
        QtWidgets.QApplication.processEvents()

        try:
            from app.pose2d.detection_pipeline import run_detection
            result = run_detection(self.source_panel.image)
            self.source_panel.set_pose2d(result.pose2d)
            self.source_panel.set_persons(result.persons)
            if self._current_data:
                self._current_data["last_detection"] = {
                    "detector": result.detector_name,
                    "persons": [{"id": p.person_id, "conf": p.confidence} for p in result.persons],
                }
            n_joints = len([j for j in result.pose2d.joints.values() if j.detected])
            self.set_status(f"Detected {n_joints} joints ({len(result.persons)} person(s))")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Detection Error", str(e))
            self.set_status("Detection failed")

    def _on_generate_3d(self):
        pose2d = self.source_panel.get_pose2d()
        if pose2d is None or not pose2d.joints:
            QtWidgets.QMessageBox.warning(self, "No Pose", "Run pose detection first.")
            return
        self.set_status("Generating 3D pose...")
        QtWidgets.QApplication.processEvents()

        try:
            from app.pose3d.lifting_pipeline import lift_to_3d
            pose3d = lift_to_3d(pose2d)
            self.viewport_3d.set_pose3d(pose3d)
            if self._current_data is not None:
                from app.persistence.project_repository import ProjectRepository
                self._current_data["pose3d"] = ProjectRepository.serialize_pose3d(pose3d)
            self.set_status(f"3D pose generated ({len(pose3d.joints)} joints)")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "3D Generation Error", str(e))
            self.set_status("3D generation failed")

    def _on_export(self):
        self.set_status("Exporting reference...")
        QtWidgets.QApplication.processEvents()
        from app.ui.dialogs import ExportDialog
        dialog = ExportDialog(self._current_data, self)
        dialog.exec()

    def _on_settings(self):
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec():
            self.set_status("Settings updated")


import os
