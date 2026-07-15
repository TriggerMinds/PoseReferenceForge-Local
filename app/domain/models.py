from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import numpy as np


class JointState(Enum):
    DETECTED_HIGH_CONFIDENCE = "DETECTED_HIGH_CONFIDENCE"
    DETECTED_LOW_CONFIDENCE = "DETECTED_LOW_CONFIDENCE"
    INFERRED = "INFERRED"
    MANUALLY_CORRECTED = "MANUALLY_CORRECTED"
    USER_CONFIRMED = "USER_CONFIRMED"
    LOCKED = "LOCKED"


class PersonDetectionConfidence(Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class Joint2D:
    joint_id: str
    x: float
    y: float
    confidence: float = 0.0
    visibility: float = 1.0
    state: JointState = JointState.DETECTED_LOW_CONFIDENCE
    detected: bool = False
    inferred: bool = False
    manually_corrected: bool = False
    occluded: bool = False
    locked: bool = False
    source_model: str = ""
    schema_version: str = "1.0"


@dataclass
class Person:
    person_id: int
    confidence: float
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2
    detection_confidence: PersonDetectionConfidence = PersonDetectionConfidence.LOW
    is_primary: bool = False


@dataclass
class Pose2D:
    joints: dict[str, Joint2D] = field(default_factory=dict)
    image_width: int = 0
    image_height: int = 0
    detector_name: str = ""
    detector_version: str = ""
    schema_version: str = "1.0"

    def get_joint(self, joint_id: str) -> Optional[Joint2D]:
        return self.joints.get(joint_id)

    def set_joint(self, joint: Joint2D):
        self.joints[joint.joint_id] = joint

    def to_array(self) -> np.ndarray:
        ordered = [self.joints.get(k) for k in JOINT_ORDER if k in self.joints]
        arr = np.zeros((len(ordered), 3), dtype=np.float32)
        for i, j in enumerate(ordered):
            arr[i] = [j.x, j.y, j.confidence]
        return arr


@dataclass
class Joint3D:
    joint_id: str
    x: float
    y: float
    z: float
    confidence: float = 0.0
    state: JointState = JointState.INFERRED
    locked: bool = False
    manually_corrected: bool = False

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)


@dataclass
class Pose3D:
    joints: dict[str, Joint3D] = field(default_factory=dict)
    root_x: float = 0.0
    root_y: float = 0.0
    root_z: float = 0.0
    schema_version: str = "1.0"

    def get_joint(self, joint_id: str) -> Optional[Joint3D]:
        return self.joints.get(joint_id)


# COCO keypoint order (17 keypoints) used by YOLOv8-pose
COCO_KEYPOINTS = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle",
]

# Extended keypoint order for PoseReferenceForge
JOINT_ORDER = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "neck",
    "left_shoulder", "right_shoulder",
    "left_elbow", "right_elbow",
    "left_wrist", "right_wrist",
    "left_hand", "right_hand",
    "upper_spine", "lower_spine",
    "pelvis",
    "left_hip", "right_hip",
    "left_knee", "right_knee",
    "left_ankle", "right_ankle",
    "left_heel", "right_heel",
    "left_foot", "right_foot",
    "head",
]

# Skeleton connections for 2D rendering
SKELETON_CONNECTIONS = [
    ("nose", "left_eye"), ("nose", "right_eye"),
    ("left_eye", "left_ear"), ("right_eye", "right_ear"),
    ("nose", "neck"),
    ("neck", "left_shoulder"), ("neck", "right_shoulder"),
    ("neck", "head"),
    ("left_shoulder", "left_elbow"), ("right_shoulder", "right_elbow"),
    ("left_elbow", "left_wrist"), ("right_elbow", "right_wrist"),
    ("left_wrist", "left_hand"), ("right_wrist", "right_hand"),
    ("neck", "upper_spine"), ("upper_spine", "lower_spine"),
    ("lower_spine", "pelvis"),
    ("pelvis", "left_hip"), ("pelvis", "right_hip"),
    ("left_shoulder", "left_hip"), ("right_shoulder", "right_hip"),
    ("left_hip", "left_knee"), ("right_hip", "right_knee"),
    ("left_knee", "left_ankle"), ("right_knee", "right_ankle"),
    ("left_ankle", "left_heel"), ("right_ankle", "right_heel"),
    ("left_heel", "left_foot"), ("right_heel", "right_foot"),
]
