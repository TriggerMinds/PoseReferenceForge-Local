"""Generate evidence renders for Recovery 02."""
import sys, os, json, cv2
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import ultralytics

ult_dir = os.path.dirname(ultralytics.__file__)
img_path = os.path.join(ult_dir, "assets", "bus.jpg")
img = cv2.imread(img_path)

from app.pose2d.detection_pipeline import run_detection
result = run_detection(img)

from app.pose3d.lifting_pipeline import lift_to_3d
pose3d = lift_to_3d(result.pose2d)

from app.exporters.export_request import ExportRequest, PackType, OverwritePolicy
from app.exporters.export_service import ExportService
from app.rendering.blender_renderer import BlenderRenderer

renderer = BlenderRenderer()
service = ExportService(renderer)

project_data = {
    "application_version": "1.0.0-dev",
    "project_name": "Recovery02",
    "image_hash": "test",
    "image_info": {"width": 810, "height": 1080},
}

evidence_dir = "evidence/renders"
os.makedirs(evidence_dir, exist_ok=True)

profiles = [
    ("source_matched_clean", "recovery_02_clean_1536x2048.png", 1536, 2048, False, "PNG", 95),
    ("transparent", "recovery_02_transparent_1536x2048.png", 1536, 2048, True, "PNG", 95),
    ("depth_readable", "recovery_02_depth_readable_1536x2048.png", 1536, 2048, False, "PNG", 95),
    ("source_matched_clean", "recovery_02_reference.jpg", 1024, 1536, False, "JPEG", 90),
]

for profile_key, filename, w, h, transparent, fmt, quality in profiles:
    out = os.path.abspath(os.path.join(evidence_dir, filename))
    print(f"Exporting {filename}: profile={profile_key} {w}x{h} fmt={fmt} transparent={transparent}")
    sys.stdout.flush()
    req = ExportRequest(
        profile_key=profile_key, image_format=fmt,
        width=w, height=h, jpeg_quality=quality,
        transparent=transparent, output_path=out,
        pack_type=PackType.NONE,
        overwrite=OverwritePolicy.OVERWRITE,
    )
    try:
        r = service.export(pose3d, result.pose2d, req, project_data)
        size_kb = r["file_size"] / 1024
        print(f"OK {filename}: {size_kb:.0f} KB sha256={r['checksum'][:16]}...")
    except Exception as e:
        import traceback
        print(f"FAIL {filename}: {e}")
        traceback.print_exc()

print("Evidence generation complete.")
