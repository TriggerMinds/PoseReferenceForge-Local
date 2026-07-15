"""Debug zidane.jpg detection and render."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import ultralytics, cv2
from app.rendering.blender_renderer import BlenderRenderer
from app.exporters.export_request import ExportRequest, PackType, OverwritePolicy
from app.exporters.export_service import ExportService
from app.pose2d.detection_pipeline import run_detection
from app.pose3d.lifting_pipeline import lift_to_3d
from app.optimization.pose_fitter import ScipyPoseFitter

ULT_DIR = os.path.dirname(ultralytics.__file__)
img = cv2.imread(os.path.join(ULT_DIR, "assets", "zidane.jpg"))
print(f"Image: {img.shape[1]}x{img.shape[0]}")

result = run_detection(img)
print(f"Detected persons: {len(result.persons)}")
print(f"2D joints: {len(result.pose2d.joints)}")

heuristic = lift_to_3d(result.pose2d)
fitter = ScipyPoseFitter()
opt, info = fitter.fit(result.pose2d, heuristic)
print(f"3D joints: {len(opt.joints)}")

renderer = BlenderRenderer()
service = ExportService(renderer)

out = os.path.abspath("evidence/practical_validation/depth_overlap/pose_primary.png")
os.makedirs(os.path.dirname(out), exist_ok=True)

req = ExportRequest(
    profile_key="source_matched_clean", image_format="PNG",
    width=1536, height=2048, jpeg_quality=95, transparent=False,
    output_path=out, pack_type=PackType.NONE, overwrite=OverwritePolicy.OVERWRITE,
)
try:
    r = service.export(opt, result.pose2d, req, {"application_version": "1.0.0-dev"})
    size_kb = r.get("file_size", 0) / 1024
    print(f"OK: {r['output_path']} ({size_kb:.0f} KB)")
except Exception as e:
    print(f"FAIL: {e}")
    import traceback
    traceback.print_exc()
