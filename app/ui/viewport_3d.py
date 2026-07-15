from PySide6 import QtWidgets, QtCore, QtGui, QtOpenGL, QtOpenGLWidgets
import numpy as np
from typing import Optional

from app.domain.models import Pose3D


class Viewport3D(QtOpenGLWidgets.QOpenGLWidget):
    def __init__(self):
        super().__init__()
        self._pose3d: Optional[Pose3D] = None
        self._rotation = QtGui.QQuaternion.fromEulerAngles(0, 0, 0)
        self._translation = QtGui.QVector3D(0, 0, -5)
        self._zoom = 1.0
        self._last_mouse = QtCore.QPointF(0, 0)
        self._is_dragging = False

        self.setMinimumSize(400, 300)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

    def set_pose3d(self, pose: Pose3D):
        self._pose3d = pose
        self.update()

    def initializeGL(self):
        import OpenGL.GL as gl
        gl.glClearColor(0.15, 0.15, 0.15, 1.0)
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

    def resizeGL(self, w: int, h: int):
        import OpenGL.GL as gl
        gl.glViewport(0, 0, w, h)

    def paintGL(self):
        import OpenGL.GL as gl
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)

        w = self.width()
        h = self.height()
        aspect = w / h if h > 0 else 1.0

        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()

        import OpenGL.GLU as glu
        glu.gluPerspective(45.0, aspect, 0.1, 100.0)

        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()

        # Camera transform
        rot = self._rotation.toEulerAngles()
        gl.glTranslatef(self._translation.x(), self._translation.y(), self._translation.z() * self._zoom)
        gl.glRotatef(rot.x(), 1, 0, 0)
        gl.glRotatef(rot.y(), 0, 1, 0)
        gl.glRotatef(rot.z(), 0, 0, 1)

        self._draw_ground_grid()
        self._draw_mannequin()

    def _draw_ground_grid(self):
        import OpenGL.GL as gl
        gl.glColor4f(0.3, 0.3, 0.3, 0.5)
        gl.glBegin(gl.GL_LINES)
        size = 2.0
        steps = 10
        for i in range(-steps, steps + 1):
            t = i / steps * size
            gl.glVertex3f(t, 0, -size)
            gl.glVertex3f(t, 0, size)
            gl.glVertex3f(-size, 0, t)
            gl.glVertex3f(size, 0, t)
        gl.glEnd()

    def _draw_mannequin(self):
        if self._pose3d is None:
            return
        import OpenGL.GL as gl

        joints = self._pose3d.joints
        # Draw mannequin as joint points + connections
        skeleton_3d = [
            ("pelvis", "lower_spine"), ("lower_spine", "upper_spine"),
            ("upper_spine", "neck"), ("neck", "head"),
            ("neck", "left_shoulder"), ("neck", "right_shoulder"),
            ("left_shoulder", "left_elbow"), ("right_shoulder", "right_elbow"),
            ("left_elbow", "left_wrist"), ("right_elbow", "right_wrist"),
            ("pelvis", "left_hip"), ("pelvis", "right_hip"),
            ("left_hip", "left_knee"), ("right_hip", "right_knee"),
            ("left_knee", "left_ankle"), ("right_knee", "right_ankle"),
            ("left_ankle", "left_foot"), ("right_ankle", "right_foot"),
        ]

        # Draw bones
        gl.glColor3f(1.0, 0.7, 0.3)
        gl.glLineWidth(3)
        gl.glBegin(gl.GL_LINES)
        for j1, j2 in skeleton_3d:
            p1 = joints.get(j1)
            p2 = joints.get(j2)
            if p1 and p2:
                gl.glVertex3f(p1.x, p1.y, p1.z)
                gl.glVertex3f(p2.x, p2.y, p2.z)
        gl.glEnd()

        # Draw joints
        gl.glPointSize(6)
        gl.glBegin(gl.GL_POINTS)
        for jid, joint in joints.items():
            if joint.state.value == "LOCKED":
                gl.glColor3f(0.0, 1.0, 1.0)
            elif joint.state.value == "MANUALLY_CORRECTED":
                gl.glColor3f(0.3, 0.7, 1.0)
            elif joint.state.value.startswith("DETECTED"):
                gl.glColor3f(0.3, 1.0, 0.3)
            else:
                gl.glColor3f(1.0, 1.0, 0.3)
            gl.glVertex3f(joint.x, joint.y, joint.z)
        gl.glEnd()

        # Draw volumetric body markers
        self._draw_body_volume()

    def _draw_body_volume(self):
        joints = self._pose3d.joints
        if not joints:
            return
        import OpenGL.GL as gl

        # Simple torso box
        neck = joints.get("neck")
        pelvis = joints.get("pelvis")
        ls = joints.get("left_shoulder")
        rs = joints.get("right_shoulder")

        if neck and pelvis and ls and rs:
            gl.glColor4f(1.0, 0.7, 0.3, 0.15)
            gl.glBegin(gl.GL_TRIANGLE_STRIP)
            shoulder_y = (neck.y + ls.y + rs.y) / 3
            hip_y = (pelvis.y + joints.get("left_hip", pelvis).y + joints.get("right_hip", pelvis).y) / 3
            shoulder_w = abs(ls.x - rs.x)
            hip_w = abs(joints.get("left_hip", pelvis).x - joints.get("right_hip", pelvis).x)

            # Front face
            gl.glVertex3f(-shoulder_w / 2, shoulder_y, 0.15)
            gl.glVertex3f(shoulder_w / 2, shoulder_y, 0.15)
            gl.glVertex3f(-hip_w / 2, hip_y, 0.15)
            gl.glVertex3f(hip_w / 2, hip_y, 0.15)
            gl.glEnd()

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        self._last_mouse = event.position()
        self._is_dragging = True

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if not self._is_dragging:
            return
        dx = event.position().x() - self._last_mouse.x()
        dy = event.position().y() - self._last_mouse.y()
        self._last_mouse = event.position()

        if event.buttons() == QtCore.Qt.LeftButton:
            # Orbit
            euler = self._rotation.toEulerAngles()
            self._rotation = QtGui.QQuaternion.fromEulerAngles(
                euler.x() + dy * 0.3, euler.y() + dx * 0.3, 0
            )
        elif event.buttons() == QtCore.Qt.MiddleButton:
            # Pan
            self._translation += QtGui.QVector3D(dx * 0.01, -dy * 0.01, 0)

        self.update()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        self._is_dragging = False

    def wheelEvent(self, event: QtGui.QWheelEvent):
        delta = event.angleDelta().y()
        self._zoom *= (1.1 if delta > 0 else 0.9)
        self._zoom = max(0.1, min(10.0, self._zoom))
        self.update()

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        if event.key() == QtCore.Qt.Key_R:
            self._rotation = QtGui.QQuaternion.fromEulerAngles(0, 0, 0)
            self._translation = QtGui.QVector3D(0, 0, -5)
            self._zoom = 1.0
            self.update()
