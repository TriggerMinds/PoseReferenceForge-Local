"""Pose Library UI with search, favorites, and management."""
from PySide6 import QtWidgets, QtCore, QtGui
from pathlib import Path
from typing import Optional

from app.library.pose_library import PoseLibrary
from app.domain.models import Pose3D
from app.config.settings import Settings


class PoseLibraryDialog(QtWidgets.QDialog):
    pose_selected = QtCore.Signal(str, object)  # pose_id, pose3d

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pose Library")
        self.resize(800, 600)
        self._lib = PoseLibrary()
        self._current_pose_id: Optional[str] = None

        layout = QtWidgets.QVBoxLayout(self)

        # Toolbar
        toolbar = QtWidgets.QHBoxLayout()
        self.edit_search = QtWidgets.QLineEdit()
        self.edit_search.setPlaceholderText("Search poses...")
        self.edit_search.textChanged.connect(self._on_search)
        toolbar.addWidget(self.edit_search)

        self.btn_save = QtWidgets.QPushButton("Save Current Pose")
        self.btn_save.clicked.connect(self._on_save)
        toolbar.addWidget(self.btn_save)

        self.btn_import = QtWidgets.QPushButton("Import")
        self.btn_import.clicked.connect(self._on_import)
        toolbar.addWidget(self.btn_import)

        layout.addLayout(toolbar)

        # Pose list
        self.pose_list = QtWidgets.QListWidget()
        self.pose_list.setIconSize(QtCore.QSize(48, 64))
        self.pose_list.setSpacing(2)
        self.pose_list.itemDoubleClicked.connect(self._on_load)
        self.pose_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.pose_list.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self.pose_list)

        # Action buttons
        actions = QtWidgets.QHBoxLayout()
        self.btn_load = QtWidgets.QPushButton("Load Selected")
        self.btn_load.clicked.connect(self._on_load)
        actions.addWidget(self.btn_load)

        self.btn_delete = QtWidgets.QPushButton("Delete")
        self.btn_delete.clicked.connect(self._on_delete)
        actions.addWidget(self.btn_delete)

        self.btn_export = QtWidgets.QPushButton("Export...")
        self.btn_export.clicked.connect(self._on_export)
        actions.addWidget(self.btn_export)

        self.btn_refresh = QtWidgets.QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self._refresh_list)
        actions.addWidget(self.btn_refresh)

        layout.addLayout(actions)

        self._refresh_list()

    def _refresh_list(self, query: str = ""):
        self.pose_list.clear()
        entries = self._lib.search(query) if query else self._lib.list_all()
        for entry in entries:
            name = entry["name"]
            if entry["favorite"]:
                name = f"★ {name}"
            if entry["manually_corrected"]:
                name = f"{name} ✎"
            info = (
                f"  {entry['tags'] or ''}"
                f"  {entry['orientation'] or ''}"
                f"  {entry['created'][:10]}"
            )
            item = QtWidgets.QListWidgetItem(f"{name}\n{info.strip()}")
            item.setData(QtCore.Qt.UserRole, entry["id"])
            item.setToolTip(
                f"Created: {entry['created']}\n"
                f"Modified: {entry['modified']}\n"
                f"Tags: {entry['tags'] or '(none)'}\n"
                f"Hands visible: {'Yes' if entry['hands_visible'] else 'No'}\n"
                f"Feet visible: {'Yes' if entry['feet_visible'] else 'No'}"
            )
            self.pose_list.addItem(item)

    def _on_search(self, text: str):
        self._refresh_list(text.strip())

    def _on_save(self):
        name, ok = QtWidgets.QInputDialog.getText(
            self, "Save Pose Preset", "Pose name:"
        )
        if not ok or not name.strip():
            return
        tags, ok = QtWidgets.QInputDialog.getText(
            self, "Tags (optional)", "Comma-separated tags:"
        )
        tags = tags.strip() if ok else ""
        pose3d = self._get_current_pose()
        if pose3d is None:
            QtWidgets.QMessageBox.warning(self, "No Pose", "No 3D pose to save.")
            return
        pose_id = self._lib.save(name=name.strip(), pose3d=pose3d, tags=tags)
        self._refresh_list()
        QtWidgets.QMessageBox.information(
            self, "Saved", f"Pose '{name}' saved (ID: {pose_id[:8]}...)"
        )

    def _on_load(self):
        item = self.pose_list.currentItem()
        if item is None:
            return
        pose_id = item.data(QtCore.Qt.UserRole)
        if pose_id:
            pose3d = self._lib.load(pose_id)
            if pose3d:
                self.pose_selected.emit(pose_id, pose3d)
                self.accept()

    def _on_delete(self):
        item = self.pose_list.currentItem()
        if item is None:
            return
        pose_id = item.data(QtCore.Qt.UserRole)
        entry = next((e for e in self._lib.list_all() if e["id"] == pose_id), None)
        name = entry["name"] if entry else pose_id[:8]
        reply = QtWidgets.QMessageBox.question(
            self, "Delete Pose", f"Delete '{name}'?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if reply == QtWidgets.QMessageBox.Yes:
            self._lib.delete(pose_id)
            self._refresh_list()

    def _on_export(self):
        item = self.pose_list.currentItem()
        if item is None:
            return
        pose_id = item.data(QtCore.Qt.UserRole)
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Pose", "", "Pose JSON (*.pose.json);;All Files (*.*)"
        )
        if path:
            try:
                self._lib.export_pose(pose_id, path)
                QtWidgets.QMessageBox.information(self, "Exported", f"Pose saved to {path}")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", str(e))

    def _on_import(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Import Pose", "", "Pose JSON (*.pose.json);;All Files (*.*)"
        )
        if path:
            try:
                pose_id = self._lib.import_pose(path)
                self._refresh_list()
                QtWidgets.QMessageBox.information(
                    self, "Imported", f"Pose imported (ID: {pose_id[:8]}...)"
                )
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", str(e))

    def _on_context_menu(self, pos):
        item = self.pose_list.itemAt(pos)
        if item is None:
            return
        pose_id = item.data(QtCore.Qt.UserRole)
        menu = QtWidgets.QMenu()
        act_rename = menu.addAction("Rename")
        act_duplicate = menu.addAction("Duplicate")
        act_favorite = menu.addAction("Toggle Favorite")
        act = menu.exec(self.pose_list.mapToGlobal(pos))
        if act == act_rename:
            new_name, ok = QtWidgets.QInputDialog.getText(
                self, "Rename", "New name:"
            )
            if ok and new_name.strip():
                self._lib.rename(pose_id, new_name.strip())
                self._refresh_list()
        elif act == act_duplicate:
            self._lib.duplicate(pose_id)
            self._refresh_list()
        elif act == act_favorite:
            self._lib.toggle_favorite(pose_id)
            self._refresh_list()

    def _get_current_pose(self) -> Optional[Pose3D]:
        parent = self.parent()
        if parent and hasattr(parent, "viewport_3d"):
            return parent.viewport_3d.get_pose3d()
        return None
