"""Debug Blender render path issues."""
import sys, os, json, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import ultralytics, cv2
from app.rendering.blender_renderer import BlenderRenderer
from app.exporters.render_profiles import RenderConfig
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

repo = ProjectRepository()
data = repo.serialize_pose3d(opt)

# Use temp dir without spaces
jpath = os.path.join(os.environ.get("TEMP", "C:/temp"), "test_pose_debug.json")
with open(jpath, "w") as f:
    json.dump(data, f)

out = os.path.abspath("evidence/practical_validation/standing/pose_primary.png")
os.makedirs(os.path.dirname(out), exist_ok=True)

renderer = BlenderRenderer()
print(f"Blender path: {renderer.blender_path}")
print(f"Available: {renderer.is_available()}")

config = RenderConfig(width=512, height=768, format="PNG", background_color=(240, 240, 240))
success, log = renderer.render_from_config(jpath, out, config, azimuth=0, elevation=15)
print(f"Success: {success}")
if not success:
    print(f"Log (first 1000 chars): {log[:1000]}")
else:
    print(f"Exists: {os.path.exists(out)}")
    if os.path.exists(out):
        print(f"Size: {os.path.getsize(out)} bytes")
