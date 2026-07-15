import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.domain.models import (
    Joint2D, Joint3D, Pose2D, Pose3D, Person,
    JointState, PersonDetectionConfidence,
    COCO_KEYPOINTS, JOINT_ORDER, SKELETON_CONNECTIONS,
)


class TestJoint2D:
    def test_create_joint(self):
        j = Joint2D(joint_id="nose", x=100.0, y=200.0, confidence=0.95)
        assert j.joint_id == "nose"
        assert j.x == 100.0
        assert j.y == 200.0
        assert j.confidence == 0.95
        assert j.state == JointState.DETECTED_LOW_CONFIDENCE
        assert not j.locked

    def test_locked_joint(self):
        j = Joint2D(joint_id="neck", x=50, y=60, locked=True)
        assert j.locked


class TestPose2D:
    def test_empty_pose(self):
        pose = Pose2D()
        assert len(pose.joints) == 0

    def test_set_and_get(self):
        pose = Pose2D()
        j = Joint2D("nose", 100, 200)
        pose.set_joint(j)
        assert pose.get_joint("nose") == j
        assert pose.get_joint("missing") is None

    def test_to_array(self):
        pose = Pose2D()
        for i, name in enumerate(JOINT_ORDER[:5]):
            pose.set_joint(Joint2D(name, float(i * 10), float(i * 10 + 5)))
        arr = pose.to_array()
        assert arr.shape[1] == 3


class TestPose3D:
    def test_empty(self):
        p = Pose3D()
        assert len(p.joints) == 0

    def test_get_joint(self):
        p = Pose3D()
        j = Joint3D("nose", 1, 2, 3)
        p.joints["nose"] = j
        assert p.get_joint("nose") == j
        assert p.get_joint("missing") is None


class TestConstants:
    def test_coco_keypoints(self):
        assert len(COCO_KEYPOINTS) == 17
        assert "nose" in COCO_KEYPOINTS
        assert "left_elbow" in COCO_KEYPOINTS

    def test_joint_order(self):
        assert len(JOINT_ORDER) == 28

    def test_skeleton_connections(self):
        assert len(SKELETON_CONNECTIONS) >= 20
        assert ("neck", "left_shoulder") in SKELETON_CONNECTIONS
