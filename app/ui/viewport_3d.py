"""Interactive 3D viewport with joint picking, selection, rotation, and IK editing."""
from PySide6 import QtWidgets, QtCore, QtGui, QtOpenGL, QtOpenGLWidgets
import numpy as np
from typing import Optional

from app.domain.models import Pose3D, Joint3D, JointState
from app.domain.edit_commands import UndoRedoStack, IKSolver


EDITABLE_JOINTS = [
    "pelvis", "lower_spine", "upper_spine", "neck", "head",
    "left_shoulder", "right_shoulder",
    "left_elbow", "right_elbow",
    "left_wrist", "right_wrist",
    "left_hand", "right_hand",
    "left_hip", "right_hip",
    "left_knee", "right_knee",
    "left_ankle", "right_ankle",
    "left_foot", "right_foot",
]

SKELETON_3D = [
    ("pelvis", "lower_spine"), ("lower_spine", "upper_spine"),
    ("upper_spine", "neck"), ("neck", "head"),
    ("neck", "left_shoulder"), ("neck", "right_shoulder"),
    ("left_shoulder", "left_elbow"), ("right_shoulder", "right_elbow"),
    ("left_elbow", "left_wrist"), ("right_elbow", "right_wrist"),
    ("left_wrist", "left_hand"), ("right_wrist", "right_hand"),
    ("pelvis", "left_hip"), ("pelvis", "right_hip"),
    ("left_hip", "left_knee"), ("right_hip", "right_knee"),
    ("left_knee", "left_ankle"), ("right_knee", "right_ankle"),
    ("left_ankle", "left_foot"), ("right_ankle", "right_foot"),
]

# IK chain definitions
IK_CHAINS = {
    "left_hand": ["left_shoulder", "left_elbow", "left_wrist", "left_hand"],
    "right_hand": ["right_shoulder", "right_elbow", "right_wrist", "right_hand"],
    "left_foot": ["left_hip", "left_knee", "left_ankle", "left_foot"],
    "right_foot": ["right_hip", "right_knee", "right_ankle", "right_foot"],
}


class Viewport3D(QtOpenGLWidgets.QOpenGLWidget):
    joint_selected = QtCore.Signal(str)
    pose_edited = QtCore.Signal()

    def __init__(self):
        super().__init__()
        self._pose3d: Optional[Pose3D] = None
        self._rotation = QtGui.QQuaternion.fromEulerAngles(0, 0, 0)
        self._translation = QtGui.QVector3D(0, 0, -5)
        self._zoom = 1.0
        self._last_mouse = QtCore.QPointF(0, 0)
        self._is_dragging = False
        self._is_rotating = False
        self._selected_joint: Optional[str] = None
        self._edit_mode = "rotate"  # "rotate", "ik", "depth"
        self._ik_target: Optional[tuple[float, float, float]] = None
        self._undo_stack = UndoRedoStack()

        self.setMinimumSize(400, 300)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setMouseTracking(True)

    def set_pose3d(self, pose: Pose3D):
        self._pose3d = pose
        self.update()

    def get_pose3d(self) -> Optional[Pose3D]:
        return self._pose3d

    def set_edit_mode(self, mode: str):
        self._edit_mode = mode

    def get_selected_joint(self) -> Optional[str]:
        return self._selected_joint

    def select_joint(self, joint_id: str):
        self._selected_joint = joint_id
        self.joint_selected.emit(joint_id)
        self.update()

    def get_undo_stack(self) -> UndoRedoStack:
        return self._undo_stack

    def initializeGL(self):
        import OpenGL.GL as gl
        gl.glClearColor(0.15, 0.15, 0.15, 1.0)
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glEnable(gl.GL_POINT_SMOOTH)
        gl.glEnable(gl.GL_LINE_SMOOTH)

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

        rot = self._rotation.toEulerAngles()
        gl.glTranslatef(self._translation.x(), self._translation.y(), self._translation.z() * self._zoom)
        gl.glRotatef(rot.x(), 1, 0, 0)
        gl.glRotatef(rot.y(), 0, 1, 0)
        gl.glRotatef(rot.z(), 0, 0, 1)

        self._draw_ground_grid()
        self._draw_mannequin()
        if self._selected_joint:
            self._draw_selection_highlight()
        if self._ik_target:
            self._draw_ik_target()

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

        # Draw thick bones
        gl.glLineWidth(4)
        gl.glBegin(gl.GL_LINES)
        for j1, j2 in SKELETON_3D:
            p1 = joints.get(j1)
            p2 = joints.get(j2)
            if p1 and p2:
                is_selected = (j1 == self._selected_joint or j2 == self._selected_joint)
                if is_selected:
                    gl.glColor3f(1.0, 1.0, 0.0)
                else:
                    gl.glColor3f(1.0, 0.7, 0.3)
                gl.glVertex3f(p1.x, p1.y, p1.z)
                gl.glVertex3f(p2.x, p2.y, p2.z)
        gl.glEnd()

        # Draw volumetric cylinders for bones
        for j1, j2 in SKELETON_3D:
            p1 = joints.get(j1)
            p2 = joints.get(j2)
            if p1 and p2:
                self._draw_cylinder(p1, p2, 0.025)

        # Draw joints as spheres
        joint_radius = 0.035
        for jid, joint in joints.items():
            locked = joint.locked
            is_selected = (jid == self._selected_joint)
            if locked:
                gl.glColor3f(0.0, 1.0, 1.0)
            elif is_selected:
                gl.glColor3f(1.0, 1.0, 0.0)
            elif joint.state.value == "MANUALLY_CORRECTED":
                gl.glColor3f(0.3, 0.7, 1.0)
            elif joint.state.value.startswith("DETECTED"):
                gl.glColor3f(0.3, 1.0, 0.3)
            else:
                gl.glColor3f(1.0, 1.0, 0.3)

            r = joint_radius * 1.5 if is_selected else joint_radius
            self._draw_sphere(joint.x, joint.y, joint.z, r)

    def _draw_sphere(self, x, y, z, radius, slices=12):
        import OpenGL.GL as gl
        gl.glBegin(gl.GL_TRIANGLE_FAN)
        for i in range(slices + 1):
            lat = i * np.pi / slices
            for j in range(slices + 1):
                lon = j * 2 * np.pi / slices
                px = x + radius * np.sin(lat) * np.cos(lon)
                py = y + radius * np.cos(lat)
                pz = z + radius * np.sin(lat) * np.sin(lon)
                gl.glVertex3f(px, py, pz)
        gl.glEnd()

    def _draw_cylinder(self, p1, p2, radius, segments=8):
        import OpenGL.GL as gl
        dx = p2.x - p1.x
        dy = p2.y - p1.y
        dz = p2.z - p1.z
        length = np.sqrt(dx*dx + dy*dy + dz*dz)
        if length < 0.001:
            return
        nx, ny, nz = dx/length, dy/length, dz/length
        up = np.array([0, 1, 0])
        if abs(np.dot([nx, ny, nz], up)) > 0.99:
            up = np.array([1, 0, 0])
        right = np.cross([nx, ny, nz], up)
        right = right / np.linalg.norm(right)
        fwd = np.cross(right, [nx, ny, nz])

        gl.glBegin(gl.GL_TRIANGLE_STRIP)
        for i in range(segments + 1):
            a = i * 2 * np.pi / segments
            c, s = np.cos(a), np.sin(a)
            rx = right[0] * c * radius + fwd[0] * s * radius
            ry = right[1] * c * radius + fwd[1] * s * radius
            rz = right[2] * c * radius + fwd[2] * s * radius
            gl.glVertex3f(p1.x + rx, p1.y + ry, p1.z + rz)
            gl.glVertex3f(p2.x + rx, p2.y + ry, p2.z + rz)
        gl.glEnd()

    def _draw_selection_highlight(self):
        if not self._pose3d or not self._selected_joint:
            return
        j = self._pose3d.joints.get(self._selected_joint)
        if not j:
            return
        import OpenGL.GL as gl
        gl.glColor4f(1.0, 1.0, 0.0, 0.3)
        self._draw_sphere(j.x, j.y, j.z, 0.07)

    def _draw_ik_target(self):
        if not self._ik_target:
            return
        import OpenGL.GL as gl
        tx, ty, tz = self._ik_target
        gl.glColor4f(0.0, 1.0, 0.5, 0.8)
        self._draw_sphere(tx, ty, tz, 0.04)
        gl.glColor4f(0.0, 1.0, 0.5, 0.3)
        gl.glBegin(gl.GL_LINE_LOOP)
        for i in range(20):
            a = i * 2 * np.pi / 20
            gl.glVertex3f(tx + 0.06 * np.cos(a), ty + 0.06 * np.sin(a), tz)
        gl.glEnd()

    def _mouse_to_ray(self, mouse_x: float, mouse_y: float):
        w = self.width()
        h = self.height()
        aspect = w / h if h > 0 else 1.0

        import OpenGL.GL as gl
        import OpenGL.GLU as glu

        # Get projection and modelview matrices
        proj = (gl.GLfloat * 16)()
        mv = (gl.GLfloat * 16)()
        viewport = (gl.GLint * 4)()
        gl.glGetFloatv(gl.GL_PROJECTION_MATRIX, proj)
        gl.glGetFloatv(gl.GL_MODELVIEW_MATRIX, mv)
        gl.glGetIntegerv(gl.GL_VIEWPORT, viewport)

        # Unproject mouse
        near_x, near_y, near_z = glu.gluUnProject(
            mouse_x, viewport[3] - mouse_y, 0.0, mv, proj, viewport
        )
        far_x, far_y, far_z = glu.gluUnProject(
            mouse_x, viewport[3] - mouse_y, 1.0, mv, proj, viewport
        )
        return (near_x, near_y, near_z), (far_x, far_y, far_z)

    def _pick_joint(self, mouse_x: float, mouse_y: float) -> Optional[str]:
        if self._pose3d is None:
            return None
        ray_origin, ray_end = self._mouse_to_ray(mouse_x, mouse_y)
        ray_dir = (
            ray_end[0] - ray_origin[0],
            ray_end[1] - ray_origin[1],
            ray_end[2] - ray_origin[2],
        )
        ray_len = np.sqrt(ray_dir[0]**2 + ray_dir[1]**2 + ray_dir[2]**2)
        if ray_len < 0.001:
            return None
        ray_dir = (ray_dir[0]/ray_len, ray_dir[1]/ray_len, ray_dir[2]/ray_len)

        best_dist = 0.08
        best_joint = None
        for jid in EDITABLE_JOINTS:
            j = self._pose3d.joints.get(jid)
            if j is None:
                continue
            to_joint = (j.x - ray_origin[0], j.y - ray_origin[1], j.z - ray_origin[2])
            t = to_joint[0]*ray_dir[0] + to_joint[1]*ray_dir[1] + to_joint[2]*ray_dir[2]
            if t < 0:
                continue
            closest = (
                ray_origin[0] + t * ray_dir[0],
                ray_origin[1] + t * ray_dir[1],
                ray_origin[2] + t * ray_dir[2],
            )
            dist = np.sqrt(
                (closest[0] - j.x)**2 + (closest[1] - j.y)**2 + (closest[2] - j.z)**2
            )
            if dist < best_dist:
                best_dist = dist
                best_joint = jid
        return best_joint

    def _apply_rotation(self, joint_id: str, axis: str, angle_deg: float):
        if self._pose3d is None:
            return
        j = self._pose3d.joints.get(joint_id)
        if j is None or j.locked:
            return

        old = (j.x, j.y, j.z)
        angle = np.radians(angle_deg)
        if axis == "x":
            y, z = j.y, j.z
            j.y = float(y * np.cos(angle) - z * np.sin(angle))
            j.z = float(y * np.sin(angle) + z * np.cos(angle))
        elif axis == "y":
            x, z = j.x, j.z
            j.x = float(x * np.cos(angle) + z * np.sin(angle))
            j.z = float(-x * np.sin(angle) + z * np.cos(angle))
        elif axis == "z":
            x, y = j.x, j.y
            j.x = float(x * np.cos(angle) - y * np.sin(angle))
            j.y = float(x * np.sin(angle) + y * np.cos(angle))

        self._undo_stack.record_change(joint_id, old[0], old[1], old[2], j.x, j.y, j.z)
        j.state = JointState.MANUALLY_CORRECTED
        self.pose_edited.emit()
        self.update()

    def _apply_ik(self, chain_end: str, target_x: float, target_y: float, target_z: float):
        if self._pose3d is None:
            return
        chain = IK_CHAINS.get(chain_end)
        if not chain or len(chain) < 3:
            return
        # Check if any joint in chain is locked
        for jid in chain:
            j = self._pose3d.joints.get(jid)
            if j and j.locked:
                return

        joints = [self._pose3d.joints.get(jid) for jid in chain]
        if any(j is None for j in joints):
            return

        # Record undo for all joints in chain
        for jid in chain:
            j = self._pose3d.joints[jid]
            self._undo_stack.record_change(
                jid, j.x, j.y, j.z, j.x, j.y, j.z,
                new_state=JointState.MANUALLY_CORRECTED,
            )

        # Solve 2-bone IK for each pair in the chain
        target = (target_x, target_y, target_z)
        for i in range(len(joints) - 2):
            root = joints[i]
            mid = joints[i + 1]
            tip = joints[i + 2]
            new_mid, new_tip = IKSolver.solve_2bone(
                (root.x, root.y, root.z),
                (mid.x, mid.y, mid.z),
                (tip.x, tip.y, tip.z),
                target,
            )
            mid.x, mid.y, mid.z = new_mid
            tip.x, tip.y, tip.z = new_tip
            target = new_tip  # propagate down the chain

        for jid in chain:
            j = self._pose3d.joints[jid]
            j.state = JointState.MANUALLY_CORRECTED

        self.pose_edited.emit()
        self.update()

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        self._last_mouse = event.position()
        self._is_dragging = True

        if event.button() == QtCore.Qt.LeftButton:
            # Try joint picking first
            picked = self._pick_joint(event.position().x(), event.position().y())
            if picked:
                self.select_joint(picked)
                self._is_rotating = True
                return
            self._is_rotating = False
        elif event.button() == QtCore.Qt.RightButton:
            picked = self._pick_joint(event.position().x(), event.position().y())
            if picked:
                self.select_joint(picked)
                # Start IK drag
                self._edit_mode = "ik"
                j = self._pose3d.joints.get(picked)
                if j:
                    self._ik_target = (j.x, j.y, j.z)
                return

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if not self._is_dragging:
            return
        dx = event.position().x() - self._last_mouse.x()
        dy = event.position().y() - self._last_mouse.y()
        self._last_mouse = event.position()

        if event.buttons() == QtCore.Qt.LeftButton and self._is_rotating and self._selected_joint:
            # Rotate selected joint
            self._apply_rotation(self._selected_joint, "y", dx * 0.5)
            self._apply_rotation(self._selected_joint, "x", -dy * 0.5)
        elif event.buttons() == QtCore.Qt.LeftButton and not self._is_rotating:
            # Orbit
            euler = self._rotation.toEulerAngles()
            self._rotation = QtGui.QQuaternion.fromEulerAngles(
                euler.x() + dy * 0.3, euler.y() + dx * 0.3, 0
            )
            self.update()
        elif event.buttons() == QtCore.Qt.MiddleButton:
            self._translation += QtGui.QVector3D(dx * 0.01, -dy * 0.01, 0)
            self.update()
        elif event.buttons() == QtCore.Qt.RightButton and self._selected_joint and self._edit_mode == "ik":
            # IK: move target and solve
            ray_origin, ray_end = self._mouse_to_ray(
                event.position().x(), event.position().y()
            )
            j = self._pose3d.joints.get(self._selected_joint)
            if j:
                # Project target at same depth as selected joint
                dir_x = ray_end[0] - ray_origin[0]
                dir_y = ray_end[1] - ray_origin[1]
                dir_z = ray_end[2] - ray_origin[2]
                d = np.sqrt(dir_x**2 + dir_y**2 + dir_z**2)
                if d > 0.001:
                    t = (j.z - ray_origin[2]) / (dir_z / d)
                    target = (
                        ray_origin[0] + t * dir_x / d,
                        ray_origin[1] + t * dir_y / d,
                        j.z,
                    )
                    self._ik_target = target
                    chain = IK_CHAINS.get(self._selected_joint)
                    if chain:
                        self._apply_ik(self._selected_joint, *target)
                    else:
                        j.x = float(target[0])
                        j.y = float(target[1])

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        self._is_dragging = False
        self._is_rotating = False
        if self._edit_mode == "ik":
            self._ik_target = None

    def wheelEvent(self, event: QtGui.QWheelEvent):
        delta = event.angleDelta().y()
        if self._selected_joint:
            # Depth adjustment on selected joint
            j = self._pose3d.joints.get(self._selected_joint) if self._pose3d else None
            if j and not j.locked:
                old = (j.x, j.y, j.z)
                dz = 0.02 if delta > 0 else -0.02
                j.z += dz
                self._undo_stack.record_change(
                    self._selected_joint, old[0], old[1], old[2], j.x, j.y, j.z
                )
                j.state = JointState.MANUALLY_CORRECTED
                self.pose_edited.emit()
        else:
            self._zoom *= (1.1 if delta > 0 else 0.9)
            self._zoom = max(0.1, min(10.0, self._zoom))
        self.update()

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        if event.key() == QtCore.Qt.Key_R:
            self._rotation = QtGui.QQuaternion.fromEulerAngles(0, 0, 0)
            self._translation = QtGui.QVector3D(0, 0, -5)
            self._zoom = 1.0
            self.update()
        elif event.key() == QtCore.Qt.Key_Z and event.modifiers() & QtCore.Qt.ControlModifier:
            if event.modifiers() & QtCore.Qt.ShiftModifier:
                self._undo_stack.redo(self._pose3d)
            else:
                self._undo_stack.undo(self._pose3d)
            self.update()
            self.pose_edited.emit()
        elif event.key() == QtCore.Qt.Key_Delete:
            if self._selected_joint:
                self.select_joint(None)
        elif event.key() == QtCore.Qt.Key_L:
            if self._selected_joint and self._pose3d:
                j = self._pose3d.joints.get(self._selected_joint)
                if j:
                    j.locked = not j.locked
                    self.pose_edited.emit()
                    self.update()
