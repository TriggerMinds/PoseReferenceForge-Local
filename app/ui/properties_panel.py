"""Properties panel connected to Viewport3D selection and pose editing."""
from PySide6 import QtWidgets, QtCore
from typing import Optional

from app.domain.models import Pose3D


class PropertiesPanel(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self._pose3d: Optional[Pose3D] = None
        self._selected_joint: Optional[str] = None
        self._viewport_ref = None

        layout = QtWidgets.QVBoxLayout(self)

        grp_joint = QtWidgets.QGroupBox("Selected Joint")
        joint_layout = QtWidgets.QFormLayout(grp_joint)
        self.lbl_joint_id = QtWidgets.QLabel("None")
        self.lbl_state = QtWidgets.QLabel("—")
        self.lbl_confidence = QtWidgets.QLabel("—")
        self.lbl_position = QtWidgets.QLabel("—")
        self.lbl_depth = QtWidgets.QLabel("—")
        self.lbl_locked = QtWidgets.QLabel("No")
        joint_layout.addRow("Joint:", self.lbl_joint_id)
        joint_layout.addRow("State:", self.lbl_state)
        joint_layout.addRow("Confidence:", self.lbl_confidence)
        joint_layout.addRow("Position:", self.lbl_position)
        joint_layout.addRow("Depth (Z):", self.lbl_depth)
        joint_layout.addRow("Locked:", self.lbl_locked)

        self.btn_lock = QtWidgets.QPushButton("Lock Joint / Unlock Joint")
        self.btn_lock.clicked.connect(self._on_toggle_lock)
        joint_layout.addRow(self.btn_lock)

        self.btn_move_joint = QtWidgets.QPushButton("Move Joint (click + drag in viewport)")
        self.btn_move_joint.setEnabled(False)
        joint_layout.addRow(self.btn_move_joint)

        self.btn_adjust_depth = QtWidgets.QPushButton("Adjust Depth (scroll wheel)")
        self.btn_adjust_depth.setEnabled(False)
        joint_layout.addRow(self.btn_adjust_depth)

        self.btn_reset = QtWidgets.QPushButton("Reset Selected Joint")
        self.btn_reset.clicked.connect(self._on_reset_joint)
        joint_layout.addRow(self.btn_reset)

        self.btn_reset_pose = QtWidgets.QPushButton("Reset All Joints")
        self.btn_reset_pose.clicked.connect(self._on_reset_pose)
        joint_layout.addRow(self.btn_reset_pose)

        layout.addWidget(grp_joint)

        grp_depth = QtWidgets.QGroupBox("Adjust Depth (Z)")
        depth_layout = QtWidgets.QVBoxLayout(grp_depth)
        self.depth_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.depth_slider.setRange(-200, 200)
        self.depth_slider.setValue(0)
        self.depth_slider.valueChanged.connect(self._on_depth_change)
        depth_layout.addWidget(QtWidgets.QLabel("← Closer    Farther →"))
        depth_layout.addWidget(self.depth_slider)
        layout.addWidget(grp_depth)

        grp_edit = QtWidgets.QGroupBox("How to Edit")
        edit_layout = QtWidgets.QVBoxLayout(grp_edit)
        edit_layout.addWidget(QtWidgets.QLabel("• Click a joint to select it"))
        edit_layout.addWidget(QtWidgets.QLabel("• Left-drag selected joint to move it"))
        edit_layout.addWidget(QtWidgets.QLabel("• Scroll wheel to adjust depth (Z)"))
        edit_layout.addWidget(QtWidgets.QLabel("• Right-drag hand/foot for IK positioning"))
        edit_layout.addWidget(QtWidgets.QLabel("• Ctrl+Z / Ctrl+Shift+Z for undo/redo"))
        layout.addWidget(grp_edit)

        grp_undo = QtWidgets.QGroupBox("History")
        undo_layout = QtWidgets.QHBoxLayout(grp_undo)
        self.btn_undo = QtWidgets.QPushButton("Undo (Ctrl+Z)")
        self.btn_undo.clicked.connect(self._on_undo)
        undo_layout.addWidget(self.btn_undo)
        self.btn_redo = QtWidgets.QPushButton("Redo (Ctrl+Shift+Z)")
        self.btn_redo.clicked.connect(self._on_redo)
        undo_layout.addWidget(self.btn_redo)
        layout.addWidget(grp_undo)

        grp_warnings = QtWidgets.QGroupBox("Anatomical Warnings")
        warnings_layout = QtWidgets.QVBoxLayout(grp_warnings)
        self.warnings_list = QtWidgets.QListWidget()
        warnings_layout.addWidget(self.warnings_list)
        layout.addWidget(grp_warnings)

        layout.addStretch()

    def set_pose(self, pose: Pose3D):
        self._pose3d = pose

    def set_viewport(self, viewport):
        self._viewport_ref = viewport

    def set_joint_selection(self, joint_id: Optional[str]):
        self._selected_joint = joint_id
        if joint_id is None:
            self.lbl_joint_id.setText("None (click a joint)")
            self.lbl_state.setText("—")
            self.lbl_confidence.setText("—")
            self.lbl_position.setText("—")
            self.lbl_depth.setText("—")
            self.lbl_locked.setText("—")
            self.depth_slider.setValue(0)
            return

        j = self._pose3d.joints.get(joint_id) if self._pose3d else None
        if j:
            self.lbl_joint_id.setText(joint_id)
            self.lbl_state.setText(j.state.value)
            self.lbl_confidence.setText(f"{j.confidence:.3f}")
            self.lbl_position.setText(f"({j.x:.2f}, {j.y:.2f}, {j.z:.2f})")
            self.lbl_depth.setText(f"{j.z:.4f}")
            self.lbl_locked.setText("Yes" if j.locked else "No")
            self.depth_slider.setValue(int(j.z * 100))

    def _on_toggle_lock(self):
        if self._selected_joint and self._pose3d:
            j = self._pose3d.joints.get(self._selected_joint)
            if j:
                j.locked = not j.locked
                self.set_joint_selection(self._selected_joint)
                if self._viewport_ref:
                    self._viewport_ref.update()

    def _on_reset_joint(self):
        if self._selected_joint and self._pose3d:
            j = self._pose3d.joints.get(self._selected_joint)
            if j:
                j.z = 0.0
                j.state = type(j.state).INFERRED
                self.set_joint_selection(self._selected_joint)
                if self._viewport_ref:
                    self._viewport_ref.update()

    def _on_reset_pose(self):
        reply = QtWidgets.QMessageBox.question(
            self, "Reset Pose",
            "Reset all joint positions to zero?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return
        if self._pose3d:
            for j in self._pose3d.joints.values():
                j.x = 0.0
                j.y = 0.0
                j.z = 0.0
                j.locked = False
                j.state = type(j.state).DETECTED_LOW_CONFIDENCE
            if self._viewport_ref:
                self._viewport_ref.update()

    def _on_depth_change(self, value: int):
        if self._selected_joint and self._pose3d:
            j = self._pose3d.joints.get(self._selected_joint)
            if j and not j.locked:
                j.z = value / 100.0
                self.lbl_depth.setText(f"{j.z:.4f}")
                j.state = type(j.state).MANUALLY_CORRECTED
                if self._viewport_ref:
                    self._viewport_ref.update()

    def _set_edit_mode(self, mode: str):
        self.btn_rotate_mode.setChecked(mode == "rotate")
        self.btn_ik_mode.setChecked(mode == "ik")
        if self._viewport_ref:
            self._viewport_ref.set_edit_mode(mode)

    def _on_undo(self):
        if self._viewport_ref:
            stack = self._viewport_ref.get_undo_stack()
            stack.undo(self._pose3d)
            self._viewport_ref.update()

    def _on_redo(self):
        if self._viewport_ref:
            stack = self._viewport_ref.get_undo_stack()
            stack.redo(self._pose3d)
            self._viewport_ref.update()

    def add_warning(self, msg: str):
        self.warnings_list.addItem(msg)

    def clear_warnings(self):
        self.warnings_list.clear()

    def update_warnings(self):
        self.clear_warnings()
        if not self._pose3d:
            return
        joints = self._pose3d.joints

        # Check inverted knees
        for side in ("left", "right"):
            hip = joints.get(f"{side}_hip")
            knee = joints.get(f"{side}_knee")
            ankle = joints.get(f"{side}_ankle")
            if hip and knee and ankle:
                knee_angle = (knee.y - hip.y) * (ankle.y - knee.y)
                if knee_angle < 0:
                    self.add_warning(f"Inverted {side} knee")

        # Check hyperextended elbows
        for side in ("left", "right"):
            shoulder = joints.get(f"{side}_shoulder")
            elbow = joints.get(f"{side}_elbow")
            wrist = joints.get(f"{side}_wrist")
            if shoulder and elbow and wrist:
                elbow_ext = (wrist.x - elbow.x) * (shoulder.x - elbow.x)
                if elbow_ext > 0:
                    self.add_warning(f"Hyperextended {side} elbow")

        # Check excessive depth
        for jid, j in joints.items():
            if abs(j.z) > 5.0:
                self.add_warning(f"Extreme depth: {jid} (z={j.z:.2f})")
