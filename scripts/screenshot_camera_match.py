"""Screenshot the Camera Match panel for evidence."""
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
from app.ui.camera_match_panel import CameraMatchPanel

result = run_detection(img)
heuristic = lift_to_3d(result.pose2d)
fitter = ScipyPoseFitter()
optimized, info = fitter.fit(result.pose2d, heuristic)
print(f"Fit: {info['initial_error']:.1f} → {info['final_error']:.1f}")

app = QtWidgets.QApplication(sys.argv)
app.setApplicationName("PoseReferenceForge")

panel = CameraMatchPanel()
panel.set_data(result.pose2d, optimized, rgb)
panel._auto_fit()
panel.resize(900, 700)

QtCore.QTimer.singleShot(300, lambda: None)
app.processEvents()

pixmap = panel.grab()
pixmap.save("evidence/screenshots/recovery_03_camera_match.png")
print(f"Screenshot saved: evidence/screenshots/recovery_03_camera_match.png ({pixmap.width()}x{pixmap.height()})")
