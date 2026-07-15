import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

from app.domain.models import Pose2D, Joint2D, JointState, Pose3D, Joint3D
from app.config.settings import Settings


class ProjectRepository:
    def __init__(self):
        self.settings = Settings.get()

    def save_project(self, path: str | Path, data: dict) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        return p

    def load_project(self, path: str | Path) -> dict:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Project not found: {p}")
        with open(p, encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def serialize_pose2d(pose: Pose2D) -> dict:
        return {
            "schema_version": pose.schema_version,
            "image_width": pose.image_width,
            "image_height": pose.image_height,
            "detector_name": pose.detector_name,
            "detector_version": pose.detector_version,
            "joints": {
                jid: {
                    "joint_id": j.joint_id,
                    "x": j.x, "y": j.y,
                    "confidence": j.confidence,
                    "visibility": j.visibility,
                    "state": j.state.value,
                    "detected": j.detected,
                    "inferred": j.inferred,
                    "manually_corrected": j.manually_corrected,
                    "locked": j.locked,
                    "source_model": j.source_model,
                }
                for jid, j in pose.joints.items()
            },
        }

    @staticmethod
    def deserialize_pose2d(data: dict) -> Pose2D:
        pose = Pose2D(
            image_width=data.get("image_width", 0),
            image_height=data.get("image_height", 0),
            detector_name=data.get("detector_name", ""),
            detector_version=data.get("detector_version", ""),
            schema_version=data.get("schema_version", "1.0"),
        )
        for jid, jd in data.get("joints", {}).items():
            try:
                state = JointState(jd.get("state", "DETECTED_LOW_CONFIDENCE"))
            except ValueError:
                state = JointState.DETECTED_LOW_CONFIDENCE
            joint = Joint2D(
                joint_id=jd["joint_id"],
                x=jd["x"], y=jd["y"],
                confidence=jd.get("confidence", 0.0),
                visibility=jd.get("visibility", 1.0),
                state=state,
                detected=jd.get("detected", False),
                inferred=jd.get("inferred", False),
                manually_corrected=jd.get("manually_corrected", False),
                locked=jd.get("locked", False),
                source_model=jd.get("source_model", ""),
            )
            pose.set_joint(joint)
        return pose

    @staticmethod
    def serialize_pose3d(pose: Optional[Pose3D]) -> dict:
        if pose is None:
            return {}
        return {
            "schema_version": pose.schema_version,
            "root_x": pose.root_x, "root_y": pose.root_y, "root_z": pose.root_z,
            "joints": {
                jid: {
                    "joint_id": j.joint_id,
                    "x": j.x, "y": j.y, "z": j.z,
                    "confidence": j.confidence,
                    "state": j.state.value,
                    "locked": j.locked,
                    "manually_corrected": j.manually_corrected,
                }
                for jid, j in pose.joints.items()
            },
        }

    @staticmethod
    def deserialize_pose3d(data: dict) -> Optional[Pose3D]:
        if not data or "joints" not in data:
            return None
        pose = Pose3D(
            root_x=data.get("root_x", 0.0),
            root_y=data.get("root_y", 0.0),
            root_z=data.get("root_z", 0.0),
            schema_version=data.get("schema_version", "1.0"),
        )
        for jid, jd in data.get("joints", {}).items():
            try:
                state = JointState(jd.get("state", "INFERRED"))
            except ValueError:
                state = JointState.INFERRED
            joint = Joint3D(
                joint_id=jd["joint_id"],
                x=jd["x"], y=jd["y"], z=jd["z"],
                confidence=jd.get("confidence", 0.0),
                state=state,
                locked=jd.get("locked", False),
                manually_corrected=jd.get("manually_corrected", False),
            )
            pose.joints[jid] = joint
        return pose

    @staticmethod
    def create_project_data(
        project_name: str,
        source_path: str,
        image_hash: str,
        image_info: dict,
        pose2d: Optional[Pose2D] = None,
        pose3d: Optional[Pose3D] = None,
    ) -> dict:
        return {
            "project_name": project_name,
            "application_version": "1.0.0-dev",
            "schema_version": "1.0",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "source_path": source_path,
            "image_hash": image_hash,
            "image_info": image_info,
            "pose2d": ProjectRepository.serialize_pose2d(pose2d) if pose2d else {},
            "pose3d": ProjectRepository.serialize_pose3d(pose3d) if pose3d else {},
        }
