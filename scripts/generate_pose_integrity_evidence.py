"""Generate pose integrity evidence for Recovery 11."""
import sys, os, json, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import ultralytics, cv2
EVIDENCE = "evidence/pose_integrity"
os.makedirs(EVIDENCE, exist_ok=True)

ult_dir = os.path.dirname(ultralytics.__file__)
img = cv2.imread(os.path.join(ult_dir, "assets", "bus.jpg"))
h, w = img.shape[:2]

from app.pose2d.detection_pipeline import run_detection
from app.pose3d.lifting_pipeline import lift_to_3d
from app.optimization.pose_fitter import ScipyPoseFitter, compute_bone_lengths, is_skeleton_connected, has_finite_coords
from app.optimization.reprojection import evaluate_reprojection
from app.rendering.blender_renderer import BlenderRenderer
from app.exporters.export_request import ExportRequest, PackType, OverwritePolicy
from app.exporters.export_service import ExportService
from app.domain.json_sanitizer import sanitize
from app.persistence.project_repository import ProjectRepository

result = run_detection(img)
heuristic = lift_to_3d(result.pose2d)
fitter = ScipyPoseFitter()
accepted_pose, info = fitter.fit(result.pose2d, heuristic)

# Save initial pose
initial_data = ProjectRepository.serialize_pose3d(heuristic)
with open(os.path.join(EVIDENCE, "initial_pose.json"), "w") as f:
    json.dump(sanitize(initial_data), f, indent=2)

# Save accepted fit pose
accepted_data = ProjectRepository.serialize_pose3d(accepted_pose)
with open(os.path.join(EVIDENCE, "accepted_fitted_pose.json"), "w") as f:
    json.dump(sanitize(accepted_data), f, indent=2)

# Bone length report
bl = compute_bone_lengths(accepted_pose)
bl_report = {f"{b[0]}->{b[1]}": round(l, 4) for b, l in bl.items()}
connected, missing = is_skeleton_connected(accepted_pose)
finite, bad_coords = has_finite_coords(accepted_pose)

# Reprojection report
cam = {"focal_length": max(w, h) * 1.2, "cx": w/2, "cy": h/2,
       "azimuth": 0, "elevation": 0, "roll": 0, "tx": 0, "ty": 0, "tz": max(w, h) * 2.0}
reproj = evaluate_reprojection(result.pose2d, accepted_pose, cam)

# Rejected exploded metrics
info["initial_error"] = round(info.get("initial_error", 0), 2)
info["final_error"] = round(info.get("final_error", 0), 2)
info["reprojection_rme"] = round(info.get("reprojection_rme", 0), 2)
info["normalized_rme"] = round(info.get("normalized_rme", 0), 4)

with open(os.path.join(EVIDENCE, "bone_length_report.json"), "w") as f:
    json.dump({"bone_lengths": bl_report, "connected": connected, "finite": finite}, f, indent=2)

with open(os.path.join(EVIDENCE, "reprojection_report.json"), "w") as f:
    json.dump(sanitize({**reproj, "fit_info": info}), f, indent=2)

with open(os.path.join(EVIDENCE, "rejected_exploded_pose_metrics.json"), "w") as f:
    json.dump(sanitize(info), f, indent=2)

# Serialization validation
sn = sanitize({"test_bool": np.True_, "test_float": np.float32(1.5), "test_int": np.int64(42)})
with open(os.path.join(EVIDENCE, "serialization_validation.json"), "w") as f:
    json.dump(sn, f, indent=2)
assert isinstance(sn["test_bool"], bool), f"Expected bool, got {type(sn['test_bool'])}"
assert sn["test_bool"] is True
assert isinstance(sn["test_float"], float)
assert isinstance(sn["test_int"], int)
print("Serialization validation: OK")

# Render accepted pose
renderer = BlenderRenderer()
service = ExportService(renderer)
out = os.path.abspath(os.path.join(EVIDENCE, "accepted_pose_render.png"))
req = ExportRequest(profile_key="source_matched_clean", image_format="PNG",
    width=1024, height=1536, jpeg_quality=95, transparent=False,
    output_path=out, pack_type=PackType.NONE, overwrite=OverwritePolicy.OVERWRITE,
    source_width=w, source_height=h)
try:
    r = service.export(accepted_pose, result.pose2d, req, {})
    print(f"Render OK: {r.get('file_size',0)} bytes")
except Exception as e:
    print(f"Render failed: {e}")

# Create projected overlay
overlay = cv2.imread(os.path.join(ult_dir, "assets", "bus.jpg"))
for jid, j in result.pose2d.joints.items():
    if j.detected:
        cv2.circle(overlay, (int(j.x), int(j.y)), 3, (0, 255, 0), -1)
# Project 3D points
from app.optimization.reprojection import build_camera_matrix, project_points
joint_order = list(accepted_pose.joints.keys())
pts_3d = np.zeros((len(joint_order), 3))
for i, jid in enumerate(joint_order):
    j = accepted_pose.joints[jid]; pts_3d[i] = [j.x, j.y, j.z]
cam_mat = build_camera_matrix(cam)
proj = project_points(pts_3d, cam_mat)
for i, jid in enumerate(joint_order):
    px, py = int(proj[i,0]), int(proj[i,1])
    if 0 <= px < w and 0 <= py < h:
        cv2.circle(overlay, (px, py), 4, (255, 100, 0), 2)
# Draw bone connections
bones_2d = [("pelvis","neck"),("neck","head"),
    ("left_shoulder","right_shoulder"),
    ("left_shoulder","left_elbow"),("right_shoulder","right_elbow"),
    ("left_elbow","left_wrist"),("right_elbow","right_wrist"),
    ("left_hip","left_knee"),("right_hip","right_knee"),
    ("left_knee","left_ankle"),("right_knee","right_ankle")]
for j1, j2 in bones_2d:
    if j1 in joint_order and j2 in joint_order:
        i1 = joint_order.index(j1); i2 = joint_order.index(j2)
        p1x, p1y = int(proj[i1,0]), int(proj[i1,1])
        p2x, p2y = int(proj[i2,0]), int(proj[i2,1])
        if 0 <= p1x < w and 0 <= p1y < h and 0 <= p2x < w and 0 <= p2y < h:
            cv2.line(overlay, (p1x, p1y), (p2x, p2y), (255, 100, 0), 1)
cv2.imwrite(os.path.join(EVIDENCE, "projected_overlay.png"), overlay)
print(f"Projected overlay saved")

print(f"\nAll evidence in {EVIDENCE}/")
