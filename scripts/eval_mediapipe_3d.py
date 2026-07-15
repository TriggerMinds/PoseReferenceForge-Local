"""Evaluate MediaPipe Pose Landmarker for 3D world coordinates."""
import sys, os, time, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import mediapipe as mp
print(f"MediaPipe version: {mp.__version__}")
print(f"tasks available: {hasattr(mp, 'tasks')}")

from mediapipe.tasks import BaseOptions
from mediapipe.tasks.python.vision import pose_landmarker
from mediapipe import Image as MpImage, ImageFormat as MpImageFormat

model_path = "models/pose_landmarker_lite.task"
if not os.path.exists(model_path):
    import requests
    url = (
        "https://storage.googleapis.com/mediapipe-models/"
        "pose_landmarker/pose_landmarker_lite/float16/latest/"
        "pose_landmarker_lite.task"
    )
    print(f"Downloading MediaPipe pose landmarker model...")
    r = requests.get(url, timeout=30)
    with open(model_path, "wb") as f:
        f.write(r.content)
    print(f"Downloaded: {os.path.getsize(model_path)} bytes")
else:
    print(f"Model exists: {os.path.getsize(model_path)} bytes")

import cv2, ultralytics
ult_dir = os.path.dirname(ultralytics.__file__)
img_path = os.path.join(ult_dir, "assets", "bus.jpg")
img = cv2.imread(img_path)
rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
h, w = img.shape[:2]

base_options = BaseOptions(model_asset_path=model_path)
options = pose_landmarker.PoseLandmarkerOptions(
    base_options=base_options,
    running_mode=pose_landmarker.RunningMode.IMAGE,
    min_pose_detection_confidence=0.5,
    output_segmentations=False,
)
detector = pose_landmarker.PoseLandmarker.create_from_options(options)

mp_image = MpImage(image_format=MpImageFormat.SRGB, data=np.ascontiguousarray(rgb))
start = time.time()
result = detector.detect(mp_image)
elapsed = time.time() - start
detector.close()

print(f"Inference: {elapsed:.3f}s")
print(f"Detected: {len(result.pose_landmarks) if result.pose_landmarks else 0} pose(s)")

if result.pose_landmarks:
    landmarks = result.pose_landmarks[0]
    world = result.pose_world_landmarks[0] if result.pose_world_landmarks else None
    print(f"Landmarks: {len(landmarks)}")
    if world is not None:
        print(f"World landmarks: {len(world)}")
        print("Sample world coords (first 5):")
        for i in range(min(5, len(world))):
            print(f"  {i}: ({world[i].x:.3f}, {world[i].y:.3f}, {world[i].z:.3f})")
        z_vals = [w.z for w in world if abs(w.z) < 10]
        if z_vals:
            print(f"Z range: {min(z_vals):.3f} to {max(z_vals):.3f}, mean: {np.mean(z_vals):.3f}")
        print("All world landmarks:")
        for i, wl in enumerate(world):
            print(f"  {i}: x={wl.x:.4f} y={wl.y:.4f} z={wl.z:.4f}")
    else:
        print("No world landmarks (use pose_landmarker_full or heavy model)")
else:
    print("No pose detected")
