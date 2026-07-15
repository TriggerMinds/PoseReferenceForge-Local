"""Camera Match workspace: overlay projected mannequin on source image."""
from PySide6 import QtWidgets, QtCore, QtGui
import numpy as np
from typing import Optional

from app.domain.models import Pose2D, Pose3D
from app.optimization.reprojection import (
    evaluate_reprojection, compute_reprojection_error,
    build_camera_matrix, project_points,
)


class CameraMatchPanel(QtWidgets.QWidget):
    camera_changed = QtCore.Signal(dict)

    def __init__(self):
        super().__init__()
        self._source_image: Optional[np.ndarray] = None
        self._pose2d: Optional[Pose2D] = None
        self._pose3d: Optional[Pose3D] = None

        self._params = {
            "azimuth": 0.0, "elevation": 15.0, "roll": 0.0,
            "focal_length": 1500.0, "scale": 1.0,
            "tx": 0.0, "ty": 0.0, "tz": 0.0,
            "source_opacity": 0.5, "projection_opacity": 0.8,
        }
        self._locked = False

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)

        # Toolbar
        toolbar = QtWidgets.QHBoxLayout()
        toolbar.addWidget(QtWidgets.QLabel("Camera Match"))
        toolbar.addStretch()

        self.btn_auto_fit = QtWidgets.QPushButton("Auto Fit")
        self.btn_auto_fit.clicked.connect(self._auto_fit)
        toolbar.addWidget(self.btn_auto_fit)

        self.btn_reset = QtWidgets.QPushButton("Reset")
        self.btn_reset.clicked.connect(self._reset_camera)
        toolbar.addWidget(self.btn_reset)

        self.btn_lock = QtWidgets.QPushButton("Lock Camera")
        self.btn_lock.setCheckable(True)
        self.btn_lock.clicked.connect(self._toggle_lock)
        toolbar.addWidget(self.btn_lock)

        layout.addLayout(toolbar)

        # View area
        self.image_label = QtWidgets.QLabel()
        self.image_label.setAlignment(QtCore.Qt.AlignCenter)
        self.image_label.setMinimumSize(400, 400)
        self.image_label.setStyleSheet("background-color: #1a1a1a; border: 1px solid #333;")
        self.image_label.mousePressEvent = self._on_mouse_press
        self.image_label.mouseMoveEvent = self._on_mouse_move
        self.image_label.mouseReleaseEvent = self._on_mouse_release
        self.image_label.wheelEvent = self._on_wheel
        layout.addWidget(self.image_label)

        # Camera controls
        controls = QtWidgets.QGroupBox("Camera Controls")
        ctrl_layout = QtWidgets.QGridLayout(controls)

        def make_slider(param, label, row, min_v, max_v, step=1):
            ctrl_layout.addWidget(QtWidgets.QLabel(label), row, 0)
            s = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            s.setRange(int(min_v / step), int(max_v / step))
            s.setValue(int(self._params[param] / step))
            s.valueChanged.connect(
                lambda v, p=param: self._on_slider(p, v * step)
            )
            ctrl_layout.addWidget(s, row, 1)
            vlabel = QtWidgets.QLabel(str(self._params[param]))
            setattr(self, f"_lbl_{param}", vlabel)
            ctrl_layout.addWidget(vlabel, row, 2)
            return s

        self._sl_az = make_slider("azimuth", "Azimuth", 0, -180, 180, 1)
        self._sl_el = make_slider("elevation", "Elevation", 1, -90, 90, 1)
        self._sl_roll = make_slider("roll", "Roll", 2, -45, 45, 1)
        self._sl_focal = make_slider("focal_length", "Focal L.", 3, 200, 5000, 10)
        self._sl_scale = make_slider("scale", "Scale", 4, 0.1, 5.0, 0.01)
        self._sl_tx = make_slider("tx", "X Offset", 5, -500, 500, 1)
        self._sl_ty = make_slider("ty", "Y Offset", 6, -500, 500, 1)

        # Opacity controls
        ctrl_layout.addWidget(QtWidgets.QLabel("Source Opacity"), 7, 0)
        self._sl_src_op = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self._sl_src_op.setRange(0, 100)
        self._sl_src_op.setValue(50)
        self._sl_src_op.valueChanged.connect(
            lambda v: self._on_slider("source_opacity", v / 100)
        )
        ctrl_layout.addWidget(self._sl_src_op, 7, 1)
        self._lbl_source_opacity = QtWidgets.QLabel("0.5")
        ctrl_layout.addWidget(self._lbl_source_opacity, 7, 2)

        ctrl_layout.addWidget(QtWidgets.QLabel("Proj. Opacity"), 8, 0)
        self._sl_proj_op = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self._sl_proj_op.setRange(0, 100)
        self._sl_proj_op.setValue(80)
        self._sl_proj_op.valueChanged.connect(
            lambda v: self._on_slider("projection_opacity", v / 100)
        )
        ctrl_layout.addWidget(self._sl_proj_op, 8, 1)
        self._lbl_projection_opacity = QtWidgets.QLabel("0.8")
        ctrl_layout.addWidget(self._lbl_projection_opacity, 8, 2)

        layout.addWidget(controls)

        # Status
        status_group = QtWidgets.QGroupBox("Alignment")
        status_layout = QtWidgets.QFormLayout(status_group)
        self._lbl_error = QtWidgets.QLabel("—")
        status_layout.addRow("Reprojection Error:", self._lbl_error)
        self._lbl_high_conf = QtWidgets.QLabel("—")
        status_layout.addRow("High-Conf Joints:", self._lbl_high_conf)
        self._lbl_inferred = QtWidgets.QLabel("—")
        status_layout.addRow("Inferred Joints:", self._lbl_inferred)
        self._lbl_depth_warn = QtWidgets.QLabel("—")
        status_layout.addRow("Depth Warnings:", self._lbl_depth_warn)
        layout.addWidget(status_group)

    def set_data(self, pose2d: Pose2D, pose3d: Pose3D, image: Optional[np.ndarray] = None):
        self._pose2d = pose2d
        self._pose3d = pose3d
        if image is not None:
            self._source_image = image
        self._render()

    def get_camera_params(self) -> dict:
        return dict(self._params)

    def _on_slider(self, param: str, value: float):
        if self._locked:
            return
        self._params[param] = value
        label = getattr(self, f"_lbl_{param}", None)
        if label:
            if param in ("source_opacity", "projection_opacity", "scale"):
                label.setText(f"{value:.2f}")
            else:
                label.setText(f"{value:.0f}")
        self._render()
        self.camera_changed.emit(self._params)

    def _toggle_lock(self):
        self._locked = self.btn_lock.isChecked()

    def _reset_camera(self):
        self._params = {
            "azimuth": 0.0, "elevation": 15.0, "roll": 0.0,
            "focal_length": 1500.0, "scale": 1.0,
            "tx": 0.0, "ty": 0.0, "tz": 0.0,
            "source_opacity": 0.5, "projection_opacity": 0.8,
        }
        self._sync_sliders()
        self._render()
        self.camera_changed.emit(self._params)

    def _auto_fit(self):
        if self._pose2d is None or self._pose3d is None:
            return

        # Simple auto-fit: estimate camera from visible 2D landmarks
        detected = {
            jid: j for jid, j in self._pose2d.joints.items()
            if j.detected and j.confidence > 0.3
        }
        if not detected:
            return

        # Estimate focal length from image size
        img_w = self._pose2d.image_width or 1000
        img_h = self._pose2d.image_height or 1000
        self._params["focal_length"] = max(img_w, img_h) * 1.2
        self._params["cx"] = img_w / 2
        self._params["cy"] = img_h / 2

        # Estimate azimuth from shoulder line
        ls = detected.get("left_shoulder")
        rs = detected.get("right_shoulder")
        if ls and rs:
            shoulder_w = abs(rs.x - ls.x)
            if shoulder_w < 30:
                nose = detected.get("nose")
                if nose and ls:
                    self._params["azimuth"] = 90 if nose.x > ls.x else -90
                else:
                    self._params["azimuth"] = 180
            else:
                self._params["azimuth"] = 0.0

        # Estimate elevation from head-to-pelvis ratio
        head = detected.get("head")
        pelvis = detected.get("pelvis")
        if head and pelvis:
            torso_ratio = abs(pelvis.y - head.y) / img_h
            self._params["elevation"] = 30.0 if torso_ratio < 0.2 else (
                -15.0 if torso_ratio > 0.5 else 10.0
            )

        self._sync_sliders()
        self._render()
        self.camera_changed.emit(self._params)

    def _sync_sliders(self):
        slider_map = [
            ("azimuth", self._sl_az, 1),
            ("elevation", self._sl_el, 1),
            ("roll", self._sl_roll, 1),
            ("focal_length", self._sl_focal, 10),
            ("scale", self._sl_scale, 0.01),
            ("tx", self._sl_tx, 1),
            ("ty", self._sl_ty, 1),
        ]
        for param, slider, step in slider_map:
            val = self._params[param]
            slider.blockSignals(True)
            slider.setValue(int(val / step))
            slider.blockSignals(False)
            label = getattr(self, f"_lbl_{param}", None)
            if label:
                if param == "scale":
                    label.setText(f"{val:.2f}")
                else:
                    label.setText(f"{val:.0f}")

    def _render(self):
        if self._pose2d is None or self._pose3d is None:
            return

        img_w = self._pose2d.image_width or 800
        img_h = self._pose2d.image_height or 800

        pixmap = QtGui.QPixmap(img_w, img_h)
        pixmap.fill(QtGui.QColor("#1a1a1a"))
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # Draw source image
        if self._source_image is not None:
            src_h, src_w = self._source_image.shape[:2]
            qimg = QtGui.QImage(
                self._source_image.data, src_w, src_h,
                3 * src_w, QtGui.QImage.Format_RGB888
            )
            src_pm = QtGui.QPixmap.fromImage(qimg).scaled(
                img_w, img_h, QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation
            )
            painter.setOpacity(self._params["source_opacity"])
            painter.drawPixmap(0, 0, src_pm)
            painter.setOpacity(1.0)

        # Draw projected skeleton
        painter.setOpacity(self._params["projection_opacity"])
        self._draw_projected_skeleton(painter, img_w, img_h)
        painter.setOpacity(1.0)

        painter.end()
        self.image_label.setPixmap(pixmap)
        self.image_label.resize(pixmap.size())

        # Update status
        self._update_status()

    def _draw_projected_skeleton(self, painter: QtGui.QPainter, img_w: int, img_h: int):
        if self._pose3d is None:
            return

        # Build camera params with image center
        cam_params = dict(self._params)
        cam_params["cx"] = img_w / 2
        cam_params["cy"] = img_h / 2
        camera = build_camera_matrix(cam_params)

        # Build 3D point array
        joint_order = list(self._pose3d.joints.keys())
        pts_3d = np.zeros((len(joint_order), 3))
        for i, jid in enumerate(joint_order):
            j = self._pose3d.joints[jid]
            pts_3d[i] = [j.x, j.y, j.z]

        proj = project_points(pts_3d, camera)

        # Draw bones
        skeleton_3d = [
            ("pelvis", "lower_spine"), ("lower_spine", "upper_spine"),
            ("upper_spine", "neck"), ("neck", "head"),
            ("neck", "left_shoulder"), ("neck", "right_shoulder"),
            ("left_shoulder", "left_elbow"), ("right_shoulder", "right_elbow"),
            ("left_elbow", "left_wrist"), ("right_elbow", "right_wrist"),
            ("pelvis", "left_hip"), ("pelvis", "right_hip"),
            ("left_hip", "left_knee"), ("right_hip", "right_knee"),
            ("left_knee", "left_ankle"), ("right_knee", "right_ankle"),
        ]

        pen = QtGui.QPen(QtGui.QColor(255, 200, 100, 200), 2)
        painter.setPen(pen)

        for j1, j2 in skeleton_3d:
            if j1 in joint_order and j2 in joint_order:
                i1 = joint_order.index(j1)
                i2 = joint_order.index(j2)
                p1 = proj[i1]
                p2 = proj[i2]
                if not (np.isnan(p1).any() or np.isnan(p2).any()):
                    painter.drawLine(int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1]))

        # Draw joints as circles
        for i, jid in enumerate(joint_order):
            p = proj[i]
            if np.isnan(p).any():
                continue

            j = self._pose3d.joints.get(jid)
            j2d = self._pose2d.get_joint(jid) if self._pose2d else None

            # Color by state
            if j and j.locked:
                color = QtGui.QColor(0, 255, 255)
            elif j2d and j2d.detected and j2d.confidence > 0.5:
                color = QtGui.QColor(100, 255, 100)
            elif j2d and j2d.inferred:
                color = QtGui.QColor(255, 255, 100)
            else:
                color = QtGui.QColor(200, 200, 200)

            painter.setBrush(QtGui.QBrush(color))
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255), 1))
            painter.drawEllipse(int(p[0] - 3), int(p[1] - 3), 6, 6)

        # Draw source joint markers (detected 2D joints)
        if self._pose2d:
            painter.setPen(QtGui.QPen(QtGui.QColor(100, 200, 255), 1))
            painter.setBrush(QtGui.QBrush())
            for jid, j in self._pose2d.joints.items():
                if j.detected:
                    painter.drawEllipse(int(j.x - 4), int(j.y - 4), 8, 8)

    def _update_status(self):
        if self._pose2d is None or self._pose3d is None:
            return

        cam_params = dict(self._params)
        cam_params["cx"] = (self._pose2d.image_width or 800) / 2
        cam_params["cy"] = (self._pose2d.image_height or 800) / 2

        result = evaluate_reprojection(self._pose2d, self._pose3d, cam_params)
        self._lbl_error.setText(f"{result['rme']:.2f} px")
        self._lbl_high_conf.setText(str(result["high_confidence_joints"]))
        self._lbl_inferred.setText(str(result["inferred_joints"]))

        depth_warnings = []
        for jid, j in self._pose3d.joints.items():
            if abs(j.z) > 5000:
                depth_warnings.append(jid)
        self._lbl_depth_warn.setText(
            ", ".join(depth_warnings[:5]) if depth_warnings else "None"
        )

    def _on_mouse_press(self, event: QtGui.QMouseEvent):
        self._drag_start = event.position()

    def _on_mouse_move(self, event: QtGui.QMouseEvent):
        if self._locked or not hasattr(self, "_drag_start"):
            return
        dx = event.position().x() - self._drag_start.x()
        dy = event.position().y() - self._drag_start.y()
        self._drag_start = event.position()

        if event.buttons() == QtCore.Qt.LeftButton:
            self._params["azimuth"] += dx * 0.5
            self._params["elevation"] = max(-90, min(90, self._params["elevation"] - dy * 0.5))
            self._sync_sliders()
            self._render()
        elif event.buttons() == QtCore.Qt.MiddleButton:
            self._params["tx"] += dx
            self._params["ty"] += dy
            self._sync_sliders()
            self._render()

    def _on_mouse_release(self, event: QtGui.QMouseEvent):
        if hasattr(self, "_drag_start"):
            del self._drag_start

    def _on_wheel(self, event: QtGui.QWheelEvent):
        if self._locked:
            return
        delta = event.angleDelta().y()
        self._params["focal_length"] *= (1.05 if delta > 0 else 0.95)
        self._params["focal_length"] = max(200, min(5000, self._params["focal_length"]))
        self._sync_sliders()
        self._render()
