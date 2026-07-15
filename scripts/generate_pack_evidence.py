"""Generate reference pack evidence for Recovery 05."""
import sys, os, cv2
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import ultralytics
from app.pose2d.detection_pipeline import run_detection
from app.pose3d.lifting_pipeline import lift_to_3d
from app.optimization.pose_fitter import ScipyPoseFitter
from app.exporters.pack_orchestrator import PackOrchestrator
from app.rendering.blender_renderer import BlenderRenderer

ULT_DIR = os.path.dirname(ultralytics.__file__)
img_path = os.path.join(ULT_DIR, "assets", "bus.jpg")
img = cv2.imread(img_path)

result = run_detection(img)
heuristic = lift_to_3d(result.pose2d)
fitter = ScipyPoseFitter()
pose3d, _ = fitter.fit(result.pose2d, heuristic)

renderer = BlenderRenderer()
orchestrator = PackOrchestrator(renderer)

project_data = {
    "application_version": "1.0.0-dev",
    "project_name": "Recovery05",
    "camera_match": {"azimuth": 0, "elevation": 15},
}

base = os.path.abspath("evidence/reference_packs")
camera = project_data["camera_match"]

# One-image
p1 = orchestrator.export_one_image(pose3d, result.pose2d, project_data, f"{base}/recovery_05_one_image", 1, camera)
print(f"One-image pack: {len(p1)} files")

# Two-image
p2 = orchestrator.export_two_image(pose3d, result.pose2d, project_data, f"{base}/recovery_05_two_image", 1, camera)
print(f"Two-image pack: {len(p2)} files")

# Three-image
p3 = orchestrator.export_three_image(pose3d, result.pose2d, project_data, f"{base}/recovery_05_three_image", 1, camera)
print(f"Three-image pack: {len(p3)} files")

# Full
p4 = orchestrator.export_full(pose3d, result.pose2d, project_data, f"{base}/recovery_05_full", 1, camera)
print(f"Full pack: {len(p4)} files")

# Library screenshot
from PySide6 import QtWidgets, QtCore
from app.ui.pose_library_dialog import PoseLibraryDialog
from app.library.pose_library import PoseLibrary

app = QtWidgets.QApplication(sys.argv)
lib = PoseLibrary()
lib.save(name="Standing Pose", pose3d=pose3d, tags="standing,front")
lib.save(name="Arms Raised", pose3d=pose3d, tags="dynamic,arms")
lib.save(name="Contrapposto", pose3d=pose3d, tags="fashion,contrapposto")

dialog = PoseLibraryDialog()
dialog.resize(700, 500)
dialog.show()
QtCore.QTimer.singleShot(500, lambda: None)
app.processEvents()
pixmap = dialog.grab()
pixmap.save("evidence/screenshots/recovery_05_pose_library.png")
print(f"Library screenshot: {pixmap.width()}x{pixmap.height()}")
dialog.close()
