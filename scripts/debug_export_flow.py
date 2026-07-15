"""Debug the full export flow. Cleans temp files before each test."""
import sys, os, json, tempfile, cv2
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import ultralytics
from app.domain.models import Pose3D, Joint3D, JointState
from app.pose2d.detection_pipeline import run_detection
from app.pose3d.lifting_pipeline import lift_to_3d
from app.optimization.pose_fitter import ScipyPoseFitter
from app.rendering.blender_renderer import BlenderRenderer
from app.exporters.export_request import ExportRequest, PackType, OverwritePolicy
from app.exporters.export_service import ExportService
from app.config.settings import Settings

ult_dir = os.path.dirname(ultralytics.__file__)
img = cv2.imread(os.path.join(ult_dir, "assets", "bus.jpg"))
result = run_detection(img)
heuristic = lift_to_3d(result.pose2d)
fitter = ScipyPoseFitter()
opt, info = fitter.fit(result.pose2d, heuristic)

renderer = BlenderRenderer()
print(f"Blender available: {renderer.is_available()}")
if not renderer.is_available():
    print(f"Blender path: '{renderer.blender_path}'")
    sys.exit(1)

service = ExportService(renderer)

# Clean up any old test files
tmp = tempfile.gettempdir()
for f in ["prf_test_clean.png", "prf_test_clean.rendering.png"]:
    p = os.path.join(tmp, f)
    if os.path.exists(p): os.unlink(p)
import shutil
for d in ["prf_newdir_test"]:
    p = os.path.join(tmp, d)
    if os.path.exists(p): shutil.rmtree(p)

# Test 1: Export to temp dir
out1 = os.path.join(tmp, "prf_test_clean.png")
req1 = ExportRequest(
    profile_key="source_matched_clean", image_format="PNG",
    width=512, height=768, jpeg_quality=95, transparent=False,
    output_path=out1, pack_type=PackType.NONE, overwrite=OverwritePolicy.OVERWRITE,
)
try:
    r1 = service.export(opt, result.pose2d, req1, {})
    exists = os.path.exists(out1)
    print(f"Test 1 - clean PNG: path={r1['output_path']} size={r1['file_size']} file_exists={exists}")
except Exception as e:
    print(f"Test 1 FAILED: {e}")

# Test 2: Export to default settings export dir
s = Settings.get()
default_dir = s.get_val("export_dir", str(os.path.join(os.path.expanduser("~"), "PoseReferenceForge", "exports")))
out2 = os.path.join(default_dir, "prf_test_from_settings.png")
req2 = ExportRequest(
    profile_key="source_matched_clean", image_format="PNG",
    width=512, height=768, jpeg_quality=95, transparent=False,
    output_path=out2, pack_type=PackType.NONE, overwrite=OverwritePolicy.OVERWRITE,
)
try:
    r2 = service.export(opt, result.pose2d, req2, {})
    exists2 = os.path.exists(out2)
    print(f"Test 2 - settings dir: path={out2} file_exists={exists2} dir_exists={os.path.exists(os.path.dirname(out2))}")
except Exception as e:
    print(f"Test 2 FAILED: {e}")

# Test 3: Export to a brand new directory that doesn't exist
out3 = os.path.join(tmp, "prf_newdir_test", "subdir", "output.png")
req3 = ExportRequest(
    profile_key="source_matched_clean", image_format="PNG",
    width=512, height=768, jpeg_quality=95, transparent=False,
    output_path=out3, pack_type=PackType.NONE, overwrite=OverwritePolicy.OVERWRITE,
)
try:
    r3 = service.export(opt, result.pose2d, req3, {})
    exists3 = os.path.exists(out3)
    print(f"Test 3 - new dir: path={out3} file_exists={exists3} dir_exists={os.path.exists(os.path.dirname(out3))}")
except Exception as e:
    print(f"Test 3 FAILED: {e}")

print("Done")
