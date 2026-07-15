import os
from PySide6 import QtWidgets, QtCore, QtGui
from pathlib import Path
from app.config.settings import Settings
from app.domain.models import Pose3D
from app.ui.source_panel import SourcePanel
from app.ui.viewport_3d import Viewport3D
from app.ui.properties_panel import PropertiesPanel
from app.ui.camera_match_panel import CameraMatchPanel
from app.ui.dialogs import NewProjectDialog, SettingsDialog, ExportDialog
from app.ui.pose_library_dialog import PoseLibraryDialog
from app.exporters.export_request import OverwritePolicy, PackType
from app.workers.export_worker import ExportWorker
from app.exporters.pack_orchestrator import PackOrchestrator
from app.rendering.blender_renderer import BlenderRenderer


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PoseReferenceForge Local")
        self.resize(1600, 1000)
        self.settings = Settings.get()

        self._current_project_path = None
        self._current_data = None
        self._restored_camera = None
        self._export_in_progress = False

        self._setup_actions()
        self._setup_menu_bar()
        self._setup_toolbar()
        self._setup_central_widget()
        self._setup_status_bar()
        self._ensure_export_dir()

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

        self.act_camera = QtGui.QAction("&Camera Match...", self)
        self.act_camera.setShortcut(QtGui.QKeySequence("Ctrl+M"))
        self.act_camera.triggered.connect(self._on_camera_match)

        self.act_fit_pose = QtGui.QAction("&Fit 3D Pose", self)
        self.act_fit_pose.setShortcut(QtGui.QKeySequence("Ctrl+F"))
        self.act_fit_pose.triggered.connect(self._on_fit_pose)

        self.act_export = QtGui.QAction("&Export Reference...", self)
        self.act_export.setShortcut(QtGui.QKeySequence("Ctrl+E"))
        self.act_export.triggered.connect(self._on_export)

        self.act_quick_export = QtGui.QAction("&Quick Export Pose Reference", self)
        self.act_quick_export.setShortcut(QtGui.QKeySequence("Ctrl+Shift+E"))
        self.act_quick_export.triggered.connect(self._on_quick_export)

        self.act_library = QtGui.QAction("&Pose Library...", self)
        self.act_library.setShortcut(QtGui.QKeySequence("Ctrl+L"))
        self.act_library.triggered.connect(self._on_library)

        self.act_save_preset = QtGui.QAction("Save Pose &Preset...", self)
        self.act_save_preset.triggered.connect(self._on_save_preset)

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
        process_menu.addAction(self.act_fit_pose)
        process_menu.addAction(self.act_camera)

        export_menu = mb.addMenu("&Export")
        export_menu.addAction(self.act_save_preset)
        export_menu.addAction(self.act_export)

        export_menu.addSeparator()
        export_menu.addAction(self.act_quick_export)

        tools_menu = mb.addMenu("&Tools")
        tools_menu.addAction(self.act_library)
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
        tb.addAction(self.act_fit_pose)
        tb.addAction(self.act_camera)
        tb.addSeparator()
        tb.addAction(self.act_library)
        tb.addSeparator()
        tb.addAction(self.act_quick_export)
        tb.addAction(self.act_export)

    def _setup_central_widget(self):
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        self.source_panel = SourcePanel()
        splitter.addWidget(self.source_panel)

        self.viewport_3d = Viewport3D()
        splitter.addWidget(self.viewport_3d)

        self.properties_panel = PropertiesPanel()
        splitter.addWidget(self.properties_panel)

        # Wire viewport signals to properties panel
        self.properties_panel.set_viewport(self.viewport_3d)
        self.viewport_3d.joint_selected.connect(self._on_joint_selected)
        self.viewport_3d.pose_edited.connect(self._on_pose_edited)

        splitter.setSizes([500, 700, 350])
        self.setCentralWidget(splitter)

    def _setup_status_bar(self):
        self.status_bar = QtWidgets.QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QtWidgets.QLabel("Ready")
        self.status_bar.addPermanentWidget(self.status_label)

    def _ensure_export_dir(self):
        from pathlib import Path
        export_dir = self.settings.get_val("export_dir", str(Path.home() / "PoseReferenceForge" / "exports"))
        Path(export_dir).mkdir(parents=True, exist_ok=True)

    def closeEvent(self, event):
        if self._export_in_progress:
            QtWidgets.QMessageBox.information(self, "Export Active",
                "An export is currently in progress.\n"
                "Please wait for it to complete before closing the application.")
            event.ignore()
            return
        event.accept()

    def _toggle_export_actions(self, enabled: bool):
        for act in [self.act_export, self.act_quick_export, self.act_save, self.act_detect,
                     self.act_gen3d, self.act_fit_pose, self.act_camera]:
            act.setEnabled(enabled)

    def set_status(self, msg: str):
        self.status_label.setText(msg)
        QtWidgets.QApplication.processEvents()

    def _on_joint_selected(self, joint_id: str):
        self.properties_panel.set_joint_selection(joint_id)
        if joint_id:
            self.set_status(f"Selected: {joint_id}")

    def _on_pose_edited(self):
        self.properties_panel.update_warnings()
        if self.viewport_3d.get_pose3d() and self._current_data is not None:
            from app.persistence.project_repository import ProjectRepository
            pose3d = self.viewport_3d.get_pose3d()
            self._current_data["pose3d"] = ProjectRepository.serialize_pose3d(pose3d)
        self.set_status("Pose edited")

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

            # Restore 3D pose
            pose3d_data = self._current_data.get("pose3d", {})
            if pose3d_data:
                pose3d = repo.deserialize_pose3d(pose3d_data)
                self.viewport_3d.set_pose3d(pose3d)
                self.properties_panel.set_pose(pose3d)

            # Restore source image
            src_path = self._current_data.get("source_path", "")
            if src_path and os.path.exists(src_path):
                from app.services.image_service import ImageService
                img, info = ImageService.load_image(src_path)
                self.source_panel.set_image(img)
                self._current_data["image_info"] = info

            # Restore camera match
            camera_match = self._current_data.get("camera_match", {})
            if camera_match:
                self._restored_camera = camera_match

            self.set_status(f"Opened: {name} — 2D+3D restored")

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

        pipeline = {"initializer": "", "fitter": "", "fit_attempted": False,
                     "fit_succeeded": False, "fallback_used": False,
                     "initial_error": 0, "final_error": 0}

        try:
            from app.pose3d.lifting_pipeline import lift_to_3d
            from app.optimization.pose_fitter import ScipyPoseFitter
            pose3d = lift_to_3d(pose2d)
            pipeline["initializer"] = "lift_to_3d_heuristic"

            # Auto-run fitter
            pipeline["fit_attempted"] = True
            try:
                fitter = ScipyPoseFitter()
                optimized, info = fitter.fit(pose2d, pose3d)
                pose3d = optimized
                pipeline["fitter"] = "ScipyPoseFitter"
                pipeline["fit_succeeded"] = bool(info.get("success", False))
                pipeline["initial_error"] = float(info.get("initial_error", 0))
                pipeline["final_error"] = float(info.get("final_error", 0))
                pipeline["fallback_used"] = not pipeline["fit_succeeded"]
            except Exception as fit_err:
                pipeline["fitter"] = f"ScipyPoseFitter_FAILED_{fit_err}"
                pipeline["fit_succeeded"] = False
                pipeline["fallback_used"] = True
                QtWidgets.QMessageBox.warning(self, "Fitting Warning",
                    f"3D fitting failed: {fit_err}\n\nUsing heuristic pose as fallback.")

            self.viewport_3d.set_pose3d(pose3d)
            self.properties_panel.set_pose(pose3d)
            if self._current_data is not None:
                from app.persistence.project_repository import ProjectRepository
                self._current_data["pose3d"] = ProjectRepository.serialize_pose3d(pose3d)
                self._current_data["pose_pipeline"] = pipeline

            fitted = "fitted" if pipeline["fit_succeeded"] else "fallback"
            self.set_status(f"3D pose generated and {fitted} ({len(pose3d.joints)} joints)")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "3D Generation Error", str(e))
            self.set_status("3D generation failed")

    def _on_camera_match(self):
        pose3d = self.viewport_3d.get_pose3d()
        pose2d = self.source_panel.get_pose2d()
        if pose3d is None:
            QtWidgets.QMessageBox.warning(self, "No 3D Pose", "Generate a 3D pose first.")
            return

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Camera Match")
        dialog.resize(1200, 800)

        panel = CameraMatchPanel()
        img = self.source_panel.image
        panel.set_data(pose2d, pose3d, img)

        layout = QtWidgets.QVBoxLayout(dialog)
        layout.addWidget(panel)

        def _save_camera_params(params_source):
            if self._current_data is not None:
                p = {
                    "azimuth": params_source.get("azimuth", 0),
                    "elevation": params_source.get("elevation", 15),
                    "roll": params_source.get("roll", 0),
                    "focal_length": params_source.get("focal_length", 1500),
                    "distance": params_source.get("distance", 2.5),
                    "tx": params_source.get("tx", 0),
                    "ty": params_source.get("ty", 0),
                    "scale": params_source.get("scale", 1.0),
                }
                self._current_data["camera_match"] = p

        def on_camera_update(params):
            _save_camera_params(params)

        def on_close():
            _save_camera_params(panel._params)
            dialog.accept()

        btn_close = QtWidgets.QPushButton("Done")
        btn_close.clicked.connect(on_close)
        layout.addWidget(btn_close)
        dialog.exec()

    def _on_fit_pose(self):
        pose3d = self.viewport_3d.get_pose3d()
        pose2d = self.source_panel.get_pose2d()
        if pose3d is None or pose2d is None:
            QtWidgets.QMessageBox.warning(self, "No Pose", "Generate a 3D pose first.")
            return

        self.set_status("Refitting 3D pose...")
        QtWidgets.QApplication.processEvents()

        try:
            from app.optimization.pose_fitter import ScipyPoseFitter
            fitter = ScipyPoseFitter()
            optimized, info = fitter.fit(pose2d, pose3d)
            self.viewport_3d.set_pose3d(optimized)
            self.properties_panel.set_pose(optimized)
            if self._current_data is not None:
                from app.persistence.project_repository import ProjectRepository
                self._current_data["pose3d"] = ProjectRepository.serialize_pose3d(optimized)
                self._current_data["pose_pipeline"] = {
                    "initializer": "lift_to_3d_heuristic",
                    "fitter": "ScipyPoseFitter",
                    "fit_attempted": True,
                    "fit_succeeded": bool(info.get("success", False)),
                    "fallback_used": False,
                    "initial_error": float(info.get("initial_error", 0)),
                    "final_error": float(info.get("final_error", 0)),
                }
            initial = info.get("initial_error", 0)
            final = info.get("final_error", 0)
            self.set_status(
                f"Pose refitted: reprojection {initial:.1f} → {final:.1f} ({len(optimized.joints)} joints)"
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Fitting Error", str(e))
            self.set_status("Fitting failed")

    def _get_pipeline_status(self) -> dict:
        pipe = (self._current_data or {}).get("pose_pipeline", {})
        return {
            "has_pose2d": self.source_panel.get_pose2d() is not None,
            "has_pose3d": self.viewport_3d.get_pose3d() is not None,
            "fit_attempted": pipe.get("fit_attempted", False),
            "fit_succeeded": pipe.get("fit_succeeded", False),
            "fallback_used": pipe.get("fallback_used", False),
            "camera_matched": "camera_match" in (self._current_data or {}),
        }

    def _check_export_readiness(self, status: dict) -> list[str]:
        warnings = []
        if not status["has_pose3d"]:
            warnings.append("No 3D pose. Run Generate 3D Pose first.")
            return warnings
        if not status["fit_attempted"]:
            warnings.append("3D fitting not performed. Run Generate 3D Pose (auto-fits) or Refit 3D Pose.")
        elif not status["fit_succeeded"]:
            warnings.append("3D fitting failed. Export will use emergency heuristic depth (fallback).")
        if not status["camera_matched"]:
            warnings.append("Camera not matched. Using default camera angles.")
        return warnings

    def _on_quick_export(self):
        pose3d = self.viewport_3d.get_pose3d()
        if pose3d is None:
            QtWidgets.QMessageBox.warning(self, "No 3D Pose", "Generate a 3D pose first.")
            return

        status = self._get_pipeline_status()
        warnings = self._check_export_readiness(status)

        # Auto-run fitting if not attempted
        if not status["fit_attempted"] and status["has_pose2d"]:
            self.set_status("Fitting pose before export...")
            QtWidgets.QApplication.processEvents()
            try:
                from app.optimization.pose_fitter import ScipyPoseFitter
                fitter = ScipyPoseFitter()
                pose2d = self.source_panel.get_pose2d()
                optimized, info = fitter.fit(pose2d, pose3d)
                self.viewport_3d.set_pose3d(optimized)
                self.properties_panel.set_pose(optimized)
                pose3d = optimized
                if self._current_data is not None:
                    from app.persistence.project_repository import ProjectRepository
                    self._current_data["pose3d"] = ProjectRepository.serialize_pose3d(optimized)
                    self._current_data["pose_pipeline"] = {
                        "initializer": "auto_fit_before_export",
                        "fitter": "ScipyPoseFitter",
                        "fit_attempted": True,
                        "fit_succeeded": bool(info.get("success", False)),
                        "fallback_used": not bool(info.get("success", False)),
                        "initial_error": float(info.get("initial_error", 0)),
                        "final_error": float(info.get("final_error", 0)),
                    }
                warnings = self._check_export_readiness(self._get_pipeline_status())
            except Exception as e:
                warnings.append(f"Auto-fit failed: {e}")

        # Show fallback warning
        if status["fallback_used"]:
            reply = QtWidgets.QMessageBox.warning(self, "Fallback Pose",
                "3D fitting failed. This export uses the emergency heuristic pose "
                "and may contain incorrect depth.\n\nExport anyway?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            )
            if reply != QtWidgets.QMessageBox.Yes:
                return

        # Show review warnings
        if warnings:
            msg = "Review before export:\n\n" + "\n".join(f"• {w}" for w in warnings)
            reply = QtWidgets.QMessageBox.information(
                self, "Export Review", msg,
                QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel,
            )
            if reply != QtWidgets.QMessageBox.Ok:
                return

        settings = Settings.get()
        export_dir = settings.get_val("export_dir", str(Path.home() / "PoseReferenceForge" / "exports"))
        import datetime
        default_name = f"pose_reference_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Quick Export Pose Reference",
            str(Path(export_dir) / default_name),
            "PNG (*.png);;All Files (*.*)"
        )
        if not path:
            return

        if Path(path).exists():
            reply = QtWidgets.QMessageBox.question(
                self, "File Exists", "Overwrite existing file?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            )
            if reply != QtWidgets.QMessageBox.Yes:
                return

        camera = (self._current_data or {}).get("camera_match", {})
        from app.exporters.export_request import ExportRequest, PackType, OverwritePolicy
        from app.workers.export_worker import ExportWorker

        img_info = (self._current_data or {}).get("image_info", {})
        request = ExportRequest(
            profile_key="source_matched_clean", image_format="PNG",
            width=1536, height=2048, jpeg_quality=95,
            transparent=False, output_path=str(path),
            pack_type=PackType.NONE, overwrite=OverwritePolicy.OVERWRITE,
            camera_azimuth=camera.get("azimuth", 0),
            camera_elevation=camera.get("elevation", 15),
            camera_roll=camera.get("roll", 0),
            camera_distance=camera.get("distance", 0),
            camera_focal_length=camera.get("focal_length", 1500),
            camera_shift_x=camera.get("tx", 0),
            camera_shift_y=camera.get("ty", 0),
            source_width=img_info.get("width", 0),
            source_height=img_info.get("height", 0),
        )

        pose2d = self.source_panel.get_pose2d()
        self._export_worker = ExportWorker(
            pose3d=pose3d, pose2d=pose2d, request=request,
            project_data=self._current_data or {},
        )
        self._export_worker.progress.connect(self._on_export_progress)
        self._export_worker.finished.connect(self._on_export_finished)
        self._export_worker.error.connect(self._on_export_error)
        self._export_worker.start()
        self._export_in_progress = True
        self._toggle_export_actions(False)
        self.set_status("Quick export starting...")

    def _on_export(self):
        pose3d = self.viewport_3d.get_pose3d()
        if pose3d is None:
            QtWidgets.QMessageBox.warning(self, "No 3D Pose", "Generate a 3D pose first.")
            return

        dialog = ExportDialog(self._current_data, self)
        if not dialog.exec():
            return

        request = dialog.get_request()
        if request is None:
            return

        # Handle pack exports directly via PackOrchestrator
        if request.pack_type != PackType.NONE:
            self._run_pack_export(pose3d, request)
            return

        # Handle overwrite
        output_path = Path(request.output_path)
        if output_path.exists():
            reply = QtWidgets.QMessageBox.question(
                self, "File Exists",
                f"Overwrite {output_path.name}?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel,
            )
            if reply == QtWidgets.QMessageBox.No:
                request.overwrite = OverwritePolicy.NUMBERED
            elif reply == QtWidgets.QMessageBox.Cancel:
                return
            else:
                request.overwrite = OverwritePolicy.OVERWRITE

        pose2d = self.source_panel.get_pose2d()

        img_info = (self._current_data or {}).get("image_info", {})
        request.source_width = img_info.get("width", 0)
        request.source_height = img_info.get("height", 0)

        self._export_worker = ExportWorker(
            pose3d=pose3d,
            pose2d=pose2d,
            request=request,
            project_data=self._current_data or {},
        )
        self._export_worker.progress.connect(self._on_export_progress)
        self._export_worker.finished.connect(self._on_export_finished)
        self._export_worker.error.connect(self._on_export_error)
        self._export_worker.start()

        self.set_status("Export starting...")

    def _run_pack_export(self, pose3d, request):
        from app.library.pose_library import PoseLibrary
        import datetime

        renderer = BlenderRenderer()
        if not renderer.is_available():
            QtWidgets.QMessageBox.critical(self, "Export Error", "Blender not found.")
            return

        orchestrator = PackOrchestrator(renderer)
        pose2d = self.source_panel.get_pose2d()
        project_data = self._current_data or {}
        camera = project_data.get("camera_match", {})

        base_dir = str(Path(request.output_path).parent)
        pack_name = f"Pose_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        pack_dir = os.path.join(base_dir, pack_name)

        try:
            self.set_status("Generating reference pack...")
            QtWidgets.QApplication.processEvents()

            if request.pack_type == PackType.ONE_IMAGE:
                paths = orchestrator.export_one_image(
                    pose3d, pose2d, project_data, pack_dir, 1, camera)
            elif request.pack_type == PackType.TWO_IMAGE:
                paths = orchestrator.export_two_image(
                    pose3d, pose2d, project_data, pack_dir, 1, camera)
            elif request.pack_type == PackType.THREE_IMAGE:
                paths = orchestrator.export_three_image(
                    pose3d, pose2d, project_data, pack_dir, 1, camera)
            elif request.pack_type == PackType.FULL:
                paths = orchestrator.export_full(
                    pose3d, pose2d, project_data, pack_dir, 1, camera)
            else:
                return

            self.set_status(f"Pack exported: {pack_dir} ({len(paths)} files)")
            QtWidgets.QMessageBox.information(
                self, "Pack Export Complete",
                f"Reference pack saved to:\n{pack_dir}\n\n{len(paths)} files generated.",
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Pack Export Error", str(e))
            self.set_status("Pack export failed")

    def _on_export_progress(self, msg: str):
        self.set_status(msg)

    def _on_export_finished(self, result: dict):
        self._export_in_progress = False
        self._toggle_export_actions(True)
        path = result.get("output_path", "?")
        size_kb = result.get("file_size", 0) / 1024
        validation = result.get("validation_errors")
        msg = f"Exported: {path} ({size_kb:.0f} KB)"
        if validation:
            msg += f" | Warnings: {'; '.join(validation)}"
        self.set_status(msg)

        detail_lines = [
            f"Output: {path}",
            f"Size: {size_kb:.0f} KB",
            f"Dimensions: {result.get('width')}x{result.get('height')}",
            f"Format: {result.get('format')}",
            f"SHA-256: {result.get('checksum', '')[:16]}...",
            f"Manifest: {result.get('manifest_path', 'N/A')}",
        ]
        if validation:
            detail_lines.append(f"Validation warnings: {'; '.join(validation)}")

        QtWidgets.QMessageBox.information(
            self, "Export Complete",
            "\n".join(detail_lines),
        )

    def _on_export_error(self, msg: str):
        self._export_in_progress = False
        self._toggle_export_actions(True)
        self.set_status(f"Export failed: {msg}")
        QtWidgets.QMessageBox.critical(self, "Export Error", msg)

    def _on_library(self):
        pose3d = self.viewport_3d.get_pose3d()
        dialog = PoseLibraryDialog(self)
        dialog.pose_selected.connect(self._on_library_pose_selected)
        dialog.exec()

    def _on_library_pose_selected(self, pose_id: str, pose3d: Pose3D):
        self.viewport_3d.set_pose3d(pose3d)
        self.properties_panel.set_pose(pose3d)
        if self._current_data is not None:
            from app.persistence.project_repository import ProjectRepository
            self._current_data["pose3d"] = ProjectRepository.serialize_pose3d(pose3d)
        self.set_status(f"Loaded pose from library: {pose_id[:8]}...")

    def _on_save_preset(self):
        pose3d = self.viewport_3d.get_pose3d()
        if pose3d is None:
            QtWidgets.QMessageBox.warning(self, "No Pose", "Generate a 3D pose first.")
            return
        from app.library.pose_library import PoseLibrary
        lib = PoseLibrary()
        name, ok = QtWidgets.QInputDialog.getText(self, "Save Pose Preset", "Preset name:")
        if not ok or not name.strip():
            return
        pose_id = lib.save(name=name.strip(), pose3d=pose3d)
        self.set_status(f"Preset saved: {name}")

    def _on_settings(self):
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec():
            self.set_status("Settings updated")
