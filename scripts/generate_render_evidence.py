"""Generate all render-recovery evidence images and metrics."""
import sys, os, json, tempfile, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import ultralytics, cv2
from PIL import Image
from app.pose2d.detection_pipeline import run_detection
from app.pose3d.lifting_pipeline import lift_to_3d
from app.optimization.pose_fitter import ScipyPoseFitter
from app.rendering.blender_renderer import BlenderRenderer
from app.exporters.export_request import ExportRequest, PackType, OverwritePolicy
from app.exporters.export_service import ExportService, ExportError, ContentValidationError
from app.persistence.project_repository import ProjectRepository

EVIDENCE = "evidence/render_recovery"
os.makedirs(EVIDENCE, exist_ok=True)

# Generate pose
ULT_DIR = os.path.dirname(ultralytics.__file__)
img = cv2.imread(os.path.join(ULT_DIR, "assets", "bus.jpg"))
result = run_detection(img)
heuristic = lift_to_3d(result.pose2d)
fitter = ScipyPoseFitter()
opt, _ = fitter.fit(result.pose2d, heuristic)

# Asymmetric pose for multiview testing
asym = opt
if "left_wrist" in asym.joints:
    j = asym.joints["left_wrist"]
    j.x += 200; j.y -= 100; j.z += 50

renderer = BlenderRenderer()
service = ExportService(renderer)
proj = {"application_version": "1.0.0-dev"}
img_info = {"width": result.pose2d.image_width, "height": result.pose2d.image_height}

profiles = [
    ("clean.png", "source_matched_clean", False, 1536, 2048),
    ("transparent.png", "transparent", True, 1536, 2048),
    ("depth_readable.png", "depth_readable", False, 1536, 2048),
    ("silhouette.png", "silhouette", False, 1536, 2048),
    ("structural.png", "structural", False, 1536, 2048),
]
metrics = {}

for fname, profile, transparent, w, h in profiles:
    out = os.path.abspath(os.path.join(EVIDENCE, fname))
    req = ExportRequest(
        profile_key=profile, image_format="PNG", width=w, height=h,
        jpeg_quality=95, transparent=transparent, output_path=out,
        pack_type=PackType.NONE, overwrite=OverwritePolicy.OVERWRITE,
        source_width=img_info["width"], source_height=img_info["height"],
    )
    try:
        r = service.export(asym, result.pose2d, req, proj)
        arr = np.array(Image.open(out))
        r_ch, g_ch, b_ch = arr[:,:,0], arr[:,:,1], arr[:,:,2]
        m = {
            "width": arr.shape[1], "height": arr.shape[0],
            "mode": str(Image.open(out).mode),
            "r_min": int(r_ch.min()), "r_max": int(r_ch.max()),
            "g_min": int(g_ch.min()), "g_max": int(g_ch.max()),
            "b_min": int(b_ch.min()), "b_max": int(b_ch.max()),
            "mean_luminance": round(float(np.mean(0.299*r_ch + 0.587*g_ch + 0.114*b_ch)), 1),
            "std_luminance": round(float(np.std(0.299*r_ch + 0.587*g_ch + 0.114*b_ch)), 1),
            "file_size": r.get("file_size", 0),
        }
        if transparent:
            alpha = arr[:,:,3]
            m["alpha_min"] = int(alpha.min()); m["alpha_max"] = int(alpha.max())
            m["alpha_nonzero"] = int((alpha > 0).sum())
        metrics[fname] = m
        print(f"OK {fname}: {m['mean_luminance']} lum, {m['r_max']} max")
    except Exception as e:
        print(f"FAIL {fname}: {e}")

# Multiview renders
for cam_name, az, el in [("front", 0, 15), ("left", -90, 15), ("rear", 180, 15), ("right", 90, 15)]:
    out = os.path.abspath(os.path.join(EVIDENCE, f"{cam_name}.png"))
    req = ExportRequest(
        profile_key="source_matched_clean", image_format="PNG", width=1024, height=1536,
        jpeg_quality=95, transparent=False, output_path=out,
        pack_type=PackType.NONE, overwrite=OverwritePolicy.OVERWRITE,
        camera_azimuth=az, camera_elevation=el,
        source_width=img_info["width"], source_height=img_info["height"],
    )
    try:
        r = service.export(asym, result.pose2d, req, proj)
        print(f"OK {cam_name}.png: {r['file_size']}")
    except Exception as e:
        print(f"FAIL {cam_name}.png: {e}")

# Multiview pixel comparison
mv_files = [("front", 0), ("left", -90), ("rear", 180), ("right", 90)]
pixels = {}
for name, _ in mv_files:
    p = os.path.join(EVIDENCE, f"{name}.png")
    if os.path.exists(p):
        arr = np.array(Image.open(p).convert("L"))
        pixels[name] = arr

mv_comparison = []
mv_names = list(pixels.keys())
for i in range(len(mv_names)):
    for j in range(i+1, len(mv_names)):
        diff = np.abs(pixels[mv_names[i]].astype(float) - pixels[mv_names[j]].astype(float))
        mean_diff = float(np.mean(diff))
        max_diff = int(diff.max())
        same = bool(np.array_equal(pixels[mv_names[i]], pixels[mv_names[j]]))
        mv_comparison.append({
            "a": mv_names[i], "b": mv_names[j],
            "mean_diff": round(mean_diff, 2),
            "max_diff": max_diff,
            "pixel_identical": same,
        })
        label = "IDENTICAL" if same else "DIFFERENT"
        print(f"  {mv_names[i]} vs {mv_names[j]}: mean_diff={mean_diff:.2f} max_diff={max_diff} {label}")

# Save metrics
with open(os.path.join(EVIDENCE, "render_content_metrics.json"), "w") as f:
    json.dump(metrics, f, indent=2)
with open(os.path.join(EVIDENCE, "multiview_pixel_comparison.json"), "w") as f:
    json.dump(mv_comparison, f, indent=2)

# Camera conversion test
cam = ExportRequest(
    profile_key="source_matched_clean", image_format="PNG", width=1536, height=2048,
    jpeg_quality=95, transparent=False, output_path="dummy.png",
    pack_type=PackType.NONE,
    camera_focal_length=1500,
    source_width=1536, source_height=2048,
).export_camera

camera_conv = {
    "focal_px": cam.focal_px,
    "source_width": cam.source_width,
    "sensor_width_mm": cam.sensor_width_mm,
    "blender_lens_mm": cam.blender_lens_mm,
    "expected_mm": round(1500 * 36.0 / 1536, 2),
}
with open(os.path.join(EVIDENCE, "camera_conversion.json"), "w") as f:
    json.dump(camera_conv, f, indent=2)
print(f"Camera: {camera_conv}")

# Content validation test
print("\nContent validation tests:")
# Test clean render
clean_path = os.path.join(EVIDENCE, "clean.png")
if os.path.exists(clean_path):
    errors = service.validate_content(clean_path, expect_alpha=False, bg_color=(240, 240, 240))
    print(f"  clean.png validation: {errors if errors else 'PASS'}")

# Test transparent
trans_path = os.path.join(EVIDENCE, "transparent.png")
if os.path.exists(trans_path):
    errors = service.validate_content(trans_path, expect_alpha=True, bg_color=(0, 0, 0))
    print(f"  transparent.png validation: {errors if errors else 'PASS'}")

# Verify clean is not black
clean_arr = np.array(Image.open(clean_path))
print(f"  clean max RGB: {clean_arr[:,:,:3].max()}, mean lum: {np.mean(0.299*clean_arr[:,:,0]+0.587*clean_arr[:,:,1]+0.114*clean_arr[:,:,2]):.1f}")

print(f"\nAll evidence in {EVIDENCE}/")
