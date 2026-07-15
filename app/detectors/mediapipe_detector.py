import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe import Image as MpImage, ImageFormat as MpImageFormat

from app.domain.models import (
    Person, PersonDetectionConfidence, Pose2D, Joint2D, JointState,
)
from app.detectors.base import PersonDetector, PoseDetector
from app.detectors.yolo_detector import _infer_extended_joints


# MediaPipe Pose landmark mapping
MP_LANDMARKS = {
    "nose": 0,
    "left_eye_inner": 1, "left_eye": 2, "left_eye_outer": 3,
    "right_eye_inner": 4, "right_eye": 5, "right_eye_outer": 6,
    "left_ear": 7, "right_ear": 8,
    "mouth_left": 9, "mouth_right": 10,
    "left_shoulder": 11, "right_shoulder": 12,
    "left_elbow": 13, "right_elbow": 14,
    "left_wrist": 15, "right_wrist": 16,
    "left_pinky": 17, "right_pinky": 18,
    "left_index": 19, "right_index": 20,
    "left_thumb": 21, "right_thumb": 22,
    "left_hip": 23, "right_hip": 24,
    "left_knee": 25, "right_knee": 26,
    "left_ankle": 27, "right_ankle": 28,
    "left_heel": 29, "right_heel": 30,
    "left_foot_index": 31, "right_foot_index": 32,
}


class MediaPipePersonDetector(PersonDetector):
    def __init__(self):
        self._name = "MediaPipe-Pose"

    def name(self) -> str:
        return self._name

    def detect(self, image: np.ndarray) -> list[Person]:
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) if image.shape[2] == 3 else image
        h, w = image.shape[:2]
        pose = _get_pose_detector()

        mp_image = MpImage(image_format=MpImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        result = pose.detect(mp_image)
        persons = []

        if result and result.pose_landmarks:
            for det_idx, landmarks in enumerate(result.pose_landmarks):
                xs = [l.x * w for l in landmarks]
                ys = [l.y * h for l in landmarks]
                x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
                conf = float(np.mean([l.score for l in landmarks]))
                pconf = PersonDetectionConfidence.HIGH if conf > 0.7 else (
                    PersonDetectionConfidence.MEDIUM if conf > 0.4 else PersonDetectionConfidence.LOW
                )
                persons.append(Person(
                    person_id=det_idx, confidence=conf, bbox=(x1, y1, x2, y2), detection_confidence=pconf
                ))

        if persons:
            persons[0].is_primary = True

        pose.close()
        return persons


_pose_detector_instance = None


def _get_pose_detector():
    global _pose_detector_instance
    if _pose_detector_instance is None:
        model_path = "models/pose_landmarker_lite.task"
        if not os.path.exists(model_path):
            return None
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            min_pose_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        _pose_detector_instance = vision.PoseLandmarker.create_from_options(options)
    return _pose_detector_instance


import os

# Deferred import to avoid circular dependency
import cv2


class MediaPipePoseDetector(PoseDetector):
    def __init__(self):
        self._name = "MediaPipe-Pose"

    def name(self) -> str:
        return self._name

    def detect(self, image: np.ndarray, person: Person) -> Pose2D:
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) if image.shape[2] == 3 else image
        h, w = image.shape[:2]
        pose = _get_pose_detector()
        if pose is None:
            return Pose2D(image_width=w, image_height=h, detector_name=self._name)

        mp_image = MpImage(image_format=MpImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        result = pose.detect(mp_image)

        pose2d = Pose2D(
            image_width=w, image_height=h,
            detector_name=self._name, detector_version="0.10",
        )

        if result and result.pose_landmarks:
            for det_idx, landmarks in enumerate(result.pose_landmarks):
                if det_idx != person.person_id:
                    continue
                for name, idx in MP_LANDMARKS.items():
                    if idx >= len(landmarks):
                        continue
                    lm = landmarks[idx]
                    conf = float(lm.score)
                    state = JointState.DETECTED_HIGH_CONFIDENCE if conf > 0.5 else JointState.DETECTED_LOW_CONFIDENCE
                    joint = Joint2D(
                        joint_id=name,
                        x=float(lm.x * w), y=float(lm.y * h),
                        confidence=conf, state=state,
                        detected=conf > 0.3,
                        source_model=self._name,
                    )
                    pose2d.set_joint(joint)
                # Infer extended joints
                break

        pose.close()
        pose2d = _infer_extended_joints(pose2d, w, h)
        return pose2d
