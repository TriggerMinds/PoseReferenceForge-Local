"""Debug ExportService export."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import ultralytics, cv2
from app.rendering.blender_renderer import BlenderRenderer
from app.exporters.export_request import ExportRequest, PackType, OverwritePolicy
from app.exporters.export_service import ExportService
from app.persistence.project_repository import ProjectRepository
from app.pose2d.detection_pipeline import run_detection
from app.pose3d.lifting_pipeline import lift_to_3d
from app.optimization.pose_fitter import ScipyPoseFitter

ULT_DIR = os.path.dirname(ultralytics.__file__)
img = cv2.imread(os.path.join(ULT_DIR, "assets", "bus.jpg"))
result = run_detection(img)
heuristic = lift_to_3d(result.pose2d)
fitter = ScipyPoseFitter()
opt, _ = fitter.fit(result.pose2d, heuristic)

renderer = BlenderRenderer()
service = ExportService(renderer)

out = os.path.abspath("evidence/practical_validation/standing/pose_primary.png")
os.makedirs(os.path.dirname(out), exist_ok=True)

req = ExportRequest(
    profile_key="source_matched_clean", image_format="PNG",
    width=1536, height=2048, jpeg_quality=95,
    transparent=False, output_path=out,
    pack_type=PackType.NONE, overwrite=OverwritePolicy.OVERWRITE,
)

try:
    r = service.export(opt, result.pose2d, req, {"application_version": "1.0.0-dev"})
    print(f"OK: {r['output_path']} ({r['file_size']/1024:.0f} KB) sha256={r['checksum'][:16]}...")
except Exception as e:
    print(f"FAIL: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
