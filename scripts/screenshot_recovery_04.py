"""Generate interactive editing evidence screenshots."""
import sys, os, cv2
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6 import QtWidgets, QtCore
import ultralytics

ULT_DIR = os.path.dirname(ultralytics.__file__)
img_path = os.path.join(ULT_DIR, "assets", "bus.jpg")
img = cv2.imread(img_path)
rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

from app.pose2d.detection_pipeline import run_detection
from app.pose3d.lifting_pipeline import lift_to_3d
from app.optimization.pose_fitter import ScipyPoseFitter
from app.ui.viewport_3d import Viewport3D

result = run_detection(img)
heuristic = lift_to_3d(result.pose2d)
fitter = ScipyPoseFitter()
optimized, info = fitter.fit(result.pose2d, heuristic)

app = QtWidgets.QApplication(sys.argv)
app.setApplicationName("PoseReferenceForge")

# Create viewport with pose
viewport = Viewport3D()
viewport.set_pose3d(optimized)
viewport.resize(700, 600)

# Process events to render
QtCore.QTimer.singleShot(300, lambda: None)
app.processEvents()

# Screenshot 1: Joint selection
viewport.select_joint("left_knee")
app.processEvents()
pixmap = viewport.grab()
pixmap.save("evidence/screenshots/recovery_04_joint_selection.png")
print(f"Joint selection: {pixmap.width()}x{pixmap.height()}")

# Screenshot 2: After IK edit (move left hand)
viewport.select_joint("left_hand")
from app.domain.edit_commands import IKSolver
viewport._apply_ik("left_hand", 0.8, 0.2, 0.3)
app.processEvents()
pixmap = viewport.grab()
pixmap.save("evidence/screenshots/recovery_04_ik_edit.png")
print(f"IK edit: {pixmap.width()}x{pixmap.height()}")

# Screenshot 3: Depth edit
viewport.select_joint("right_elbow")
j = optimized.joints.get("right_elbow")
if j:
    j.z += 0.3
viewport.update()
app.processEvents()
pixmap = viewport.grab()
pixmap.save("evidence/screenshots/recovery_04_depth_edit.png")
print(f"Depth edit: {pixmap.width()}x{pixmap.height()}")

# Render corrected pose with Blender
from app.exporters.export_request import ExportRequest, PackType
from app.exporters.export_service import ExportService
from app.rendering.blender_renderer import BlenderRenderer

renderer = BlenderRenderer()
service = ExportService(renderer)
out = os.path.abspath("evidence/renders/recovery_04_corrected_pose.png")
req = ExportRequest(
    profile_key="source_matched_clean", image_format="PNG",
    width=1024, height=1536, jpeg_quality=95,
    transparent=False, output_path=out,
    pack_type=PackType.NONE,
)
project_data = {"application_version": "1.0.0-dev", "project_name": "Recovery04"}
r = service.export(optimized, result.pose2d, req, project_data)
print(f"Corrected pose render: {out} ({r['file_size']/1024:.0f} KB)")
