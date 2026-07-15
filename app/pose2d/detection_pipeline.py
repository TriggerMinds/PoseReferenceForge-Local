from dataclasses import dataclass
import numpy as np

from app.domain.models import Person, Pose2D
from app.detectors.yolo_detector import YOLOPersonDetector, YOLOPoseDetector
from app.config.settings import Settings


@dataclass
class DetectionResult:
    persons: list[Person]
    pose2d: Pose2D
    detector_name: str
    elapsed: float


def run_detection(image: np.ndarray) -> DetectionResult:
    import time
    start = time.time()

    settings = Settings.get()
    model_path = settings.models_dir / (settings.get_val("default_model", "yolov8n-pose.pt"))

    if not model_path.exists():
        model_path = __import__("pathlib").Path.cwd() / "models" / settings.get_val("default_model", "yolov8n-pose.pt")

    if not model_path.exists():
        raise FileNotFoundError(f"Pose model not found: {model_path}")

    device = "cuda:0" if settings.get_val("gpu_enabled", True) else "cpu"

    # Person detection
    person_detector = YOLOPersonDetector(str(model_path), device=device)
    persons = person_detector.detect(image)

    if not persons:
        # Fallback: treat entire image as one person
        h, w = image.shape[:2]
        persons = [Person(person_id=0, confidence=0.5, bbox=(0, 0, w, h), is_primary=True)]

    # Pose detection on primary person
    pose_detector = YOLOPoseDetector(str(model_path), device=device)
    pose2d = pose_detector.detect(image, persons[0])

    elapsed = time.time() - start

    return DetectionResult(
        persons=persons,
        pose2d=pose2d,
        detector_name=pose_detector.name(),
        elapsed=elapsed,
    )
