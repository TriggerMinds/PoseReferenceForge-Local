"""Undo/redo command stack for 3D pose editing."""
from typing import Optional
from dataclasses import dataclass, field
from app.domain.models import Pose3D, Joint3D, JointState


@dataclass
class PoseEditCommand:
    joint_id: str
    old_x: float
    old_y: float
    old_z: float
    new_x: float
    new_y: float
    new_z: float
    old_state: JointState
    new_state: JointState


class UndoRedoStack:
    def __init__(self, max_size: int = 50):
        self._undo: list[PoseEditCommand] = []
        self._redo: list[PoseEditCommand] = []
        self._max_size = max_size
        self._saved_state_id = 0
        self._current_state_id = 0

    def push(self, command: PoseEditCommand):
        self._undo.append(command)
        if len(self._undo) > self._max_size:
            self._undo.pop(0)
        self._redo.clear()
        self._current_state_id += 1

    def undo(self, pose: Optional[Pose3D] = None) -> Optional[PoseEditCommand]:
        if not self._undo:
            return None
        cmd = self._undo.pop()
        self._redo.append(cmd)
        self._current_state_id -= 1
        if pose and cmd.joint_id in pose.joints:
            j = pose.joints[cmd.joint_id]
            j.x, j.y, j.z = cmd.old_x, cmd.old_y, cmd.old_z
            j.state = cmd.old_state
        return cmd

    def redo(self, pose: Optional[Pose3D] = None) -> Optional[PoseEditCommand]:
        if not self._redo:
            return None
        cmd = self._redo.pop()
        self._undo.append(cmd)
        self._current_state_id += 1
        if pose and cmd.joint_id in pose.joints:
            j = pose.joints[cmd.joint_id]
            j.x, j.y, j.z = cmd.new_x, cmd.new_y, cmd.new_z
            j.state = cmd.new_state
        return cmd

    def can_undo(self) -> bool:
        return len(self._undo) > 0

    def can_redo(self) -> bool:
        return len(self._redo) > 0

    def record_change(
        self, joint_id: str,
        old_x: float, old_y: float, old_z: float,
        new_x: float, new_y: float, new_z: float,
        old_state: JointState = JointState.INFERRED,
        new_state: JointState = JointState.MANUALLY_CORRECTED,
    ):
        self.push(PoseEditCommand(
            joint_id=joint_id,
            old_x=old_x, old_y=old_y, old_z=old_z,
            new_x=new_x, new_y=new_y, new_z=new_z,
            old_state=old_state, new_state=new_state,
        ))

    def is_modified(self) -> bool:
        return self._current_state_id != self._saved_state_id

    def mark_saved(self):
        self._saved_state_id = self._current_state_id


from app.optimization.reprojection import project_points, build_camera_matrix


class IKSolver:
    """Simple 2-bone CCD IK solver for limbs."""

    @staticmethod
    def solve_2bone(
        root_pos: tuple[float, float, float],
        mid_pos: tuple[float, float, float],
        tip_pos: tuple[float, float, float],
        target_pos: tuple[float, float, float],
        bone1_len: Optional[float] = None,
        bone2_len: Optional[float] = None,
    ) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        import numpy as np

        r = np.array(root_pos, dtype=np.float64)
        m = np.array(mid_pos, dtype=np.float64)
        t = np.array(tip_pos, dtype=np.float64)
        target = np.array(target_pos, dtype=np.float64)

        if bone1_len is None:
            bone1_len = float(np.linalg.norm(m - r))
        if bone2_len is None:
            bone2_len = float(np.linalg.norm(t - m))

        total_len = bone1_len + bone2_len
        d = float(np.linalg.norm(target - r))

        if d > total_len * 0.99:
            direction = (target - r) / d
            new_mid = r + direction * bone1_len
            new_tip = r + direction * total_len
            return (float(new_mid[0]), float(new_mid[1]), float(new_mid[2])), \
                   (float(new_tip[0]), float(new_tip[1]), float(new_tip[2]))

        d = max(d, 1e-6)
        cos_angle = (bone1_len**2 + d**2 - bone2_len**2) / (2 * bone1_len * d)
        cos_angle = max(-1.0, min(1.0, cos_angle))
        angle = np.arccos(cos_angle)

        direction = (target - r) / d
        up = np.array([0, 1, 0], dtype=np.float64)
        if abs(np.dot(direction, up)) > 0.99:
            up = np.array([1, 0, 0], dtype=np.float64)

        right = np.cross(direction, up)
        right = right / np.linalg.norm(right)
        perp = np.cross(right, direction)

        mid_offset = (direction * np.cos(angle) + perp * np.sin(angle)) * bone1_len
        new_mid = r + mid_offset
        new_tip_dir = target - new_mid
        new_tip_dir = new_tip_dir / np.linalg.norm(new_tip_dir) * bone2_len
        new_tip = new_mid + new_tip_dir

        return (float(new_mid[0]), float(new_mid[1]), float(new_mid[2])), \
               (float(new_tip[0]), float(new_tip[1]), float(new_tip[2]))
