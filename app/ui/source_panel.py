from PySide6 import QtWidgets, QtCore, QtGui
import numpy as np
from typing import Optional

from app.domain.models import Pose2D, Person, SKELETON_CONNECTIONS


class SourcePanel(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self._image: Optional[np.ndarray] = None
        self._pose2d: Optional[Pose2D] = None
        self._persons: list[Person] = []
        self._show_skeleton = True
        self._skeleton_opacity = 0.7
        self._zoom = 1.0
        self._pan = QtCore.QPointF(0, 0)
        self._dragging_joint = None
        self._drag_offset = QtCore.QPointF(0, 0)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        toolbar = QtWidgets.QHBoxLayout()
        toolbar.addWidget(QtWidgets.QLabel("Source Image"))
        toolbar.addStretch()
        self.btn_toggle_skeleton = QtWidgets.QPushButton("Skeleton")
        self.btn_toggle_skeleton.setCheckable(True)
        self.btn_toggle_skeleton.setChecked(True)
        self.btn_toggle_skeleton.clicked.connect(self._toggle_skeleton)
        toolbar.addWidget(self.btn_toggle_skeleton)

        self.btn_fit = QtWidgets.QPushButton("Fit")
        self.btn_fit.clicked.connect(self._fit_image)
        toolbar.addWidget(self.btn_fit)

        layout.addLayout(toolbar)

        self.image_label = QtWidgets.QLabel()
        self.image_label.setAlignment(QtCore.Qt.AlignCenter)
        self.image_label.setMinimumSize(400, 300)
        self.image_label.setStyleSheet("background-color: #1a1a1a; border: 1px solid #333;")
        self.image_label.setMouseTracking(True)
        self.image_label.mousePressEvent = self._on_mouse_press
        self.image_label.mouseMoveEvent = self._on_mouse_move
        self.image_label.mouseReleaseEvent = self._on_mouse_release
        self.image_label.wheelEvent = self._on_wheel

        scroll = QtWidgets.QScrollArea()
        scroll.setWidget(self.image_label)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

    @property
    def image(self) -> Optional[np.ndarray]:
        return self._image

    def set_image(self, img: np.ndarray):
        self._image = img
        self._fit_image()
        self._render()

    def set_pose2d(self, pose: Pose2D):
        self._pose2d = pose
        self._render()

    def set_persons(self, persons: list[Person]):
        self._persons = persons
        self._render()

    def get_pose2d(self) -> Optional[Pose2D]:
        return self._pose2d

    def _toggle_skeleton(self):
        self._show_skeleton = self.btn_toggle_skeleton.isChecked()
        self._render()

    def _fit_image(self):
        self._zoom = 1.0
        self._pan = QtCore.QPointF(0, 0)
        self._render()

    def _render(self):
        if self._image is None:
            pixmap = QtGui.QPixmap(400, 300)
            pixmap.fill(QtGui.QColor("#1a1a1a"))
            self.image_label.setPixmap(pixmap)
            return

        h, w = self._image.shape[:2]
        disp_w = int(w * self._zoom)
        disp_h = int(h * self._zoom)

        # Convert to QImage
        if self._image.shape[2] == 3:
            qimg = QtGui.QImage(self._image.data, w, h, 3 * w, QtGui.QImage.Format_RGB888)
        else:
            qimg = QtGui.QImage(self._image.data, w, h, w, QtGui.QImage.Format_Grayscale8)

        pixmap = QtGui.QPixmap.fromImage(qimg)

        # Draw skeleton overlay
        if self._show_skeleton and self._pose2d:
            painter = QtGui.QPainter(pixmap)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            self._draw_skeleton(painter, w, h)
            painter.end()

        scaled = pixmap.scaled(disp_w, disp_h, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled)
        self.image_label.resize(scaled.size())

    def _draw_skeleton(self, painter: QtGui.QPainter, img_w: int, img_h: int):
        joints = self._pose2d.joints if self._pose2d else {}
        if not joints:
            return

        # Draw connections
        pen = QtGui.QPen(QtGui.QColor(255, 100, 100, int(255 * self._skeleton_opacity)), 2)
        painter.setPen(pen)

        for j1, j2 in SKELETON_CONNECTIONS:
            p1 = joints.get(j1)
            p2 = joints.get(j2)
            if p1 and p2 and p1.detected and p2.detected:
                painter.drawLine(int(p1.x), int(p1.y), int(p2.x), int(p2.y))

        # Draw joints
        for jid, joint in joints.items():
            if not joint.detected and not joint.inferred:
                continue
            color = QtGui.QColor(100, 255, 100) if joint.state.value.startswith("DETECTED") else (
                QtGui.QColor(255, 255, 100) if joint.inferred else QtGui.QColor(100, 200, 255)
            )
            painter.setBrush(QtGui.QBrush(color))
            if joint.locked:
                painter.setPen(QtGui.QPen(QtGui.QColor(0, 255, 255), 2))
            else:
                painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255), 1))

            radius = 5 if joint.detected else 3
            painter.drawEllipse(int(joint.x - radius), int(joint.y - radius), radius * 2, radius * 2)

    def _on_mouse_press(self, event: QtGui.QMouseEvent):
        if self._pose2d is None:
            return
        # Check if clicking on a joint
        for jid, joint in self._pose2d.joints.items():
            dx = event.position().x() - joint.x
            dy = event.position().y() - joint.y
            if (dx * dx + dy * dy) < 100:
                self._dragging_joint = jid
                self._drag_offset = QtCore.QPointF(dx, dy)
                break

    def _on_mouse_move(self, event: QtGui.QMouseEvent):
        if self._dragging_joint and self._pose2d:
            joint = self._pose2d.joints.get(self._dragging_joint)
            if joint:
                joint.x = float(event.position().x() - self._drag_offset.x())
                joint.y = float(event.position().y() - self._drag_offset.y())
                self._render()

    def _on_mouse_release(self, event: QtGui.QMouseEvent):
        if self._dragging_joint:
            self._dragging_joint = None

    def _on_wheel(self, event: QtGui.QWheelEvent):
        delta = event.angleDelta().y()
        factor = 1.1 if delta > 0 else 0.9
        self._zoom *= factor
        self._zoom = max(0.1, min(10.0, self._zoom))
        self._render()
