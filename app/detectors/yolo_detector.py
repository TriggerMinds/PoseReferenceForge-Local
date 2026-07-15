import numpy as np
import torch
from ultralytics import YOLO
from app.domain.models import (
    Person, PersonDetectionConfidence, Pose2D, Joint2D, JointState,
    COCO_KEYPOINTS,
)
from app.detectors.base import PersonDetector, PoseDetector


class YOLOPersonDetector(PersonDetector):
    def __init__(self, model_path: str, conf_threshold: float = 0.3, device: str = ""):
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        self._device = device
        if device:
            self.model.to(device)
        elif torch.cuda.is_available():
            self.model.to("cuda")
        self._name = f"YOLO({model_path.split('/')[-1]})"

    def name(self) -> str:
        return self._name

    def detect(self, image: np.ndarray) -> list[Person]:
        results = self.model(image, verbose=False, conf=self.conf_threshold)
        persons = []
        for i, (box, conf) in enumerate(zip(results[0].boxes.xyxy, results[0].boxes.conf)):
            x1, y1, x2, y2 = box.tolist()
            conf_val = conf.item()
            if conf_val > 0.7:
                pconf = PersonDetectionConfidence.HIGH
            elif conf_val > 0.4:
                pconf = PersonDetectionConfidence.MEDIUM
            else:
                pconf = PersonDetectionConfidence.LOW
            persons.append(Person(
                person_id=i, confidence=conf_val, bbox=(x1, y1, x2, y2), detection_confidence=pconf
            ))
        if persons:
            persons[0].is_primary = True
        return persons


class YOLOPoseDetector(PoseDetector):
    def __init__(self, model_path: str, device: str = ""):
        self.model = YOLO(model_path)
        self._device = device
        if device:
            self.model.to(device)
        elif torch.cuda.is_available():
            self.model.to("cuda")
        self._name = f"YOLO-Pose({model_path.split('/')[-1]})"

    def name(self) -> str:
        return self._name

    def detect(self, image: np.ndarray, person: Person) -> Pose2D:
        results = self.model(image, verbose=False)
        pose = Pose2D(
            image_width=image.shape[1],
            image_height=image.shape[0],
            detector_name=self._name,
            detector_version="8.x",
        )

        for result in results:
            if result.keypoints is None or result.keypoints.data is None:
                continue
            kps = result.keypoints.data.cpu().numpy()
            confs = result.keypoints.conf.cpu().numpy() if result.keypoints.conf is not None else None

            for det_idx in range(len(kps)):
                if person.person_id != det_idx:
                    continue
                for kp_idx, kp_name in enumerate(COCO_KEYPOINTS):
                    if kp_idx >= kps.shape[1]:
                        break
                    x, y, vis = kps[det_idx, kp_idx]
                    conf = confs[det_idx, kp_idx] if confs is not None else vis / 2.0
                    state = JointState.DETECTED_HIGH_CONFIDENCE if conf > 0.5 else JointState.DETECTED_LOW_CONFIDENCE
                    joint = Joint2D(
                        joint_id=kp_name,
                        x=float(x), y=float(y),
                        confidence=float(conf),
                        visibility=float(vis),
                        state=state,
                        detected=conf > 0.3,
                        source_model=self._name,
                    )
                    pose.set_joint(joint)

                # Infer additional joints from COCO schema
                pose = _infer_extended_joints(pose, image.shape[1], image.shape[0])
                break
        return pose


def _infer_extended_joints(pose: Pose2D, img_w: int, img_h: int) -> Pose2D:
    ls = pose.get_joint("left_shoulder")
    rs = pose.get_joint("right_shoulder")
    lh = pose.get_joint("left_hip")
    rh = pose.get_joint("right_hip")
    le = pose.get_joint("left_elbow")
    re = pose.get_joint("right_elbow")
    lw = pose.get_joint("left_wrist")
    rw = pose.get_joint("right_wrist")
    lk = pose.get_joint("left_knee")
    rk = pose.get_joint("right_knee")
    la = pose.get_joint("left_ankle")
    ra = pose.get_joint("right_ankle")
    nose = pose.get_joint("nose")

    # Neck: midpoint of shoulders
    if ls and rs and not pose.get_joint("neck"):
        pose.set_joint(Joint2D(
            joint_id="neck",
            x=(ls.x + rs.x) / 2, y=(ls.y + rs.y) / 2,
            confidence=min(ls.confidence, rs.confidence) * 0.9,
            state=JointState.INFERRED, inferred=True, source_model="inference",
        ))

    # Pelvis: midpoint of hips
    if lh and rh and not pose.get_joint("pelvis"):
        pose.set_joint(Joint2D(
            joint_id="pelvis",
            x=(lh.x + rh.x) / 2, y=(lh.y + rh.y) / 2,
            confidence=min(lh.confidence, rh.confidence) * 0.9,
            state=JointState.INFERRED, inferred=True, source_model="inference",
        ))

    # Upper spine / lower spine interpolation
    neck = pose.get_joint("neck")
    pelvis = pose.get_joint("pelvis")
    if neck and pelvis:
        if not pose.get_joint("upper_spine"):
            pose.set_joint(Joint2D(
                joint_id="upper_spine",
                x=(neck.x * 0.6 + pelvis.x * 0.4),
                y=(neck.y * 0.6 + pelvis.y * 0.4),
                confidence=min(neck.confidence, pelvis.confidence) * 0.8,
                state=JointState.INFERRED, inferred=True,
            ))
        if not pose.get_joint("lower_spine"):
            pose.set_joint(Joint2D(
                joint_id="lower_spine",
                x=(neck.x * 0.3 + pelvis.x * 0.7),
                y=(neck.y * 0.3 + pelvis.y * 0.7),
                confidence=min(neck.confidence, pelvis.confidence) * 0.8,
                state=JointState.INFERRED, inferred=True,
            ))

    # Head: above nose
    if nose:
        head_y = nose.y - (neck.y - nose.y) * 0.5 if neck else nose.y - 30
        pose.set_joint(Joint2D(
            joint_id="head",
            x=nose.x, y=head_y,
            confidence=nose.confidence * 0.7,
            state=JointState.INFERRED, inferred=True,
        ))

    # Hands: wrist position as hand proxy
    if lw and not pose.get_joint("left_hand"):
        pose.set_joint(Joint2D(
            joint_id="left_hand", x=lw.x, y=lw.y,
            confidence=lw.confidence * 0.8, state=JointState.INFERRED, inferred=True,
        ))
    if rw and not pose.get_joint("right_hand"):
        pose.set_joint(Joint2D(
            joint_id="right_hand", x=rw.x, y=rw.y,
            confidence=rw.confidence * 0.8, state=JointState.INFERRED, inferred=True,
        ))

    # Heel/foot from ankle
    if la and not pose.get_joint("left_heel"):
        pose.set_joint(Joint2D(
            joint_id="left_heel", x=la.x - 5, y=la.y + 10,
            confidence=la.confidence * 0.6, state=JointState.INFERRED, inferred=True,
        ))
        pose.set_joint(Joint2D(
            joint_id="left_foot", x=la.x + 10, y=la.y + 15,
            confidence=la.confidence * 0.6, state=JointState.INFERRED, inferred=True,
        ))
    if ra and not pose.get_joint("right_heel"):
        pose.set_joint(Joint2D(
            joint_id="right_heel", x=ra.x + 5, y=ra.y + 10,
            confidence=ra.confidence * 0.6, state=JointState.INFERRED, inferred=True,
        ))
        pose.set_joint(Joint2D(
            joint_id="right_foot", x=ra.x - 10, y=ra.y + 15,
            confidence=ra.confidence * 0.6, state=JointState.INFERRED, inferred=True,
        ))

    return pose
