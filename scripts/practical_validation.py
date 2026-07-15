"""Create 3 practical validation cases with evidence."""
import sys, os, cv2, numpy as np, json, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import ultralytics
ULT_DIR = os.path.dirname(ultralytics.__file__)
ASSETS_DIR = os.path.join(ULT_DIR, "assets")
EVIDENCE = "evidence/practical_validation"
os.makedirs(EVIDENCE, exist_ok=True)

from app.pose2d.detection_pipeline import run_detection
from app.pose3d.lifting_pipeline import lift_to_3d
from app.optimization.pose_fitter import ScipyPoseFitter
from app.rendering.blender_renderer import BlenderRenderer
from app.exporters.export_request import ExportRequest, PackType, OverwritePolicy
from app.exporters.export_service import ExportService, ExportError
from app.optimization.reprojection import evaluate_reprojection
from app.domain.models import Pose3D, Joint3D, JointState


def make_comparison(src_img, pose2d, pose3d, camera, out_path):
    """Create a comparison sheet: source | skeleton overlay | mannequin | projected overlay."""
    from PIL import Image, ImageDraw, ImageFont
    h, w = src_img.shape[:2]
    scale = 400 / max(h, w)
    disp_w, disp_h = int(w * scale), int(h * scale)

    # Source
    src_small = cv2.resize(src_img, (disp_w, disp_h))
    src_rgb = cv2.cvtColor(src_small, cv2.COLOR_BGR2RGB)

    # Skeleton overlay
    skel = src_rgb.copy()
    for j1, j2 in [
        ("left_shoulder","right_shoulder"),("neck","pelvis"),
        ("left_shoulder","left_elbow"),("left_elbow","left_wrist"),
        ("right_shoulder","right_elbow"),("right_elbow","right_wrist"),
        ("left_hip","left_knee"),("left_knee","left_ankle"),
        ("right_hip","right_knee"),("right_knee","right_ankle"),
    ]:
        p1 = pose2d.get_joint(j1)
        p2 = pose2d.get_joint(j2)
        if p1 and p2 and p1.detected and p2.detected:
            cv2.line(skel, (int(p1.x*scale), int(p1.y*scale)),
                     (int(p2.x*scale), int(p2.y*scale)), (0,255,0), 2)

    # Get mannequin render path
    renderer = BlenderRenderer()
    service = ExportService(renderer)
    cam = camera or {}
    proj_data = {"application_version": "1.0.0-dev"}

    prim_out = out_path.replace("comparison.png", "pose_primary.png")
    pose_req = ExportRequest(
        profile_key="source_matched_clean", image_format="PNG",
        width=disp_w, height=disp_h, jpeg_quality=95,
        transparent=False, output_path=prim_out,
        pack_type=PackType.NONE, overwrite=OverwritePolicy.OVERWRITE,
        camera_azimuth=cam.get("azimuth", 0), camera_elevation=cam.get("elevation", 15),
    )
    try:
        r = service.export(pose3d, pose2d, pose_req, proj_data)
        mann_path = r["output_path"]
    except Exception as e:
        print(f"  Render failed: {e}")
        mann_path = None

    if mann_path and os.path.exists(mann_path):
        mann = np.array(Image.open(mann_path).convert("RGB"))
        mann_small = cv2.resize(mann, (disp_w, disp_h))
    else:
        mann_small = np.zeros((disp_h, disp_w, 3), dtype=np.uint8)

    # Create 2x2 comparison grid
    canvas = np.ones((disp_h * 2 + 10, disp_w * 2 + 10, 3), dtype=np.uint8) * 240

    canvas[:disp_h, :disp_w] = src_rgb
    canvas[:disp_h, disp_w+10:] = skel
    canvas[disp_h+10:, :disp_w] = mann_small

    # Projected overlay on right-bottom
    overlay = mann_small.copy()
    overlay_rgba = cv2.addWeighted(mann_small, 0.5, np.zeros_like(mann_small), 0.5, 0)
    canvas[disp_h+10:, disp_w+10:] = overlay_rgba

    # Labels
    for i, label in enumerate(["Source", "Skeleton", "Mannequin"]):
        y = 15 if i < 2 else disp_h + 25
        x = 5 if i % 2 == 0 else disp_w + 15
        cv2.putText(canvas, label, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 1)

    cv2.imwrite(out_path, canvas)
    print(f"  Comparison saved: {out_path}")

    # Also write manifest
    if mann_path and os.path.exists(mann_path):
        from app.exporters.pack_exporter import compute_checksum
        manifest = {
            "application_version": "1.0.0-dev",
            "fixture": os.path.basename(out_path).replace("_comparison.png", ""),
            "source_dimensions": [w, h],
            "mannequin_render": mann_path,
            "mannequin_checksum": compute_checksum(mann_path),
            "camera": cam,
            "pose_joints": len(pose3d.joints),
        }
        mpath = out_path.replace(".png", ".manifest.json").replace("comparison", "manifest")
        with open(mpath, "w") as f:
            json.dump(manifest, f, indent=2)


def make_fixture_standing():
    """CASE 1: Simple standing using bus.jpg people."""
    print("\n=== CASE 1: Simple Standing ===")
    img = cv2.imread(os.path.join(ASSETS_DIR, "bus.jpg"))
    if img is None:
        print("  SKIP: no asset image")
        return None, None, None, None
    return process_case(img, "standing", "bus.jpg")


def make_fixture_depth():
    """CASE 2: Depth/overlap using zidane.jpg (hat, profile-ish)."""
    print("\n=== CASE 2: Depth/Overlap ===")
    img = cv2.imread(os.path.join(ASSETS_DIR, "zidane.jpg"))
    if img is None:
        print("  SKIP: no asset image")
        return None, None, None, None
    return process_case(img, "depth_overlap", "zidane.jpg")


def make_fixture_complex(source_img=None):
    """CASE 3: Complex pose — use bus.jpg with a modified crouch."""
    print("\n=== CASE 3: Complex (synthetic crouch) ===")
    img = cv2.imread(os.path.join(ASSETS_DIR, "bus.jpg"))
    if img is None:
        print("  SKIP: no asset image")
        return None, None, None, None

    # Process then manually push the pose into a crouch-like position
    result = run_detection(img)
    if not result.pose2d.joints:
        print("  SKIP: no detection")
        return None, None, None, None

    heuristic = lift_to_3d(result.pose2d)
    fitter = ScipyPoseFitter()
    pose3d, info = fitter.fit(result.pose2d, heuristic)

    # Move pelvis down, knees forward to simulate crouch
    pelvis = pose3d.joints.get("pelvis")
    if pelvis:
        pelvis.y -= 0.5
        pelvis.z += 0.2
    for side in ("left", "right"):
        knee = pose3d.joints.get(f"{side}_knee")
        ankle = pose3d.joints.get(f"{side}_ankle")
        if knee:
            knee.x *= 0.5
            knee.z += 0.3
        if ankle:
            ankle.x *= 0.3
            ankle.z += 0.1
        hand = pose3d.joints.get(f"{side}_hand")
        if hand:
            hand.y -= 0.3
            hand.z += 0.2

    return process_case(img, "crouching", "bus_crouch.jpg", result.pose2d, pose3d)


def process_case(img, case_name, img_name, pose2d=None, pose3d=None):
    out_dir = os.path.join(EVIDENCE, case_name)
    os.makedirs(out_dir, exist_ok=True)

    if pose2d is None or pose3d is None:
        result = run_detection(img)
        if not result.pose2d.joints:
            print(f"  No detections")
            return None, None, None, None
        heuristic = lift_to_3d(result.pose2d)
        fitter = ScipyPoseFitter()
        pose3d, info = fitter.fit(result.pose2d, heuristic)
        pose2d = result.pose2d

    # Source overlay
    src_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    skel = src_rgb.copy()
    for j1, j2 in [
        ("left_shoulder","right_shoulder"),("neck","pelvis"),
        ("left_shoulder","left_elbow"),("left_elbow","left_wrist"),
        ("right_shoulder","right_elbow"),("right_elbow","right_wrist"),
        ("left_hip","left_knee"),("left_knee","left_ankle"),
        ("right_hip","right_knee"),("right_knee","right_ankle"),
    ]:
        p1 = pose2d.get_joint(j1)
        p2 = pose2d.get_joint(j2)
        if p1 and p2 and p1.detected and p2.detected:
            cv2.line(skel, (int(p1.x), int(p1.y)),
                     (int(p2.x), int(p2.y)), (0,255,0), 2)
    cv2.imwrite(os.path.join(out_dir, "source_overlay.png"), skel)

    # Export primary pose reference
    renderer = BlenderRenderer()
    if renderer.is_available():
        service = ExportService(renderer)
        cam = {}
        out_prim = out_dir + "/pose_primary.png"
        req = ExportRequest(
            profile_key="source_matched_clean", image_format="PNG",
            width=1536, height=2048, jpeg_quality=95,
            transparent=False,
            output_path=out_prim,
            pack_type=PackType.NONE, overwrite=OverwritePolicy.OVERWRITE,
            camera_azimuth=0, camera_elevation=15,
        )
        try:
            r = service.export(pose3d, pose2d, req, {"application_version": "1.0.0-dev"})
            size_kb = r.get("file_size", 0) / 1024
            print(f"  Primary: {r['output_path']} ({size_kb:.0f} KB)")
        except Exception as e:
            print(f"  Primary export failed: {e}")

        # Transparent
        out_trans = out_dir + "/transparent.png"
        req_t = ExportRequest(
            profile_key="transparent", image_format="PNG",
            width=1536, height=2048, jpeg_quality=95,
            transparent=True,
            output_path=out_trans,
            pack_type=PackType.NONE, overwrite=OverwritePolicy.OVERWRITE,
            camera_azimuth=0, camera_elevation=15,
        )
        try:
            r2 = service.export(pose3d, pose2d, req_t, {"application_version": "1.0.0-dev"})
            size_kb2 = r2.get("file_size", 0) / 1024
            print(f"  Transparent: {r2['output_path']} ({size_kb2:.0f} KB)")
        except Exception as e:
            print(f"  Transparent export failed: {e}")

    # Comparison
    make_comparison(img, pose2d, pose3d, {}, os.path.join(out_dir, "comparison.png"))

    # Save manifest
    manifest = {
        "case": case_name,
        "source": img_name,
        "detected_joints": len([j for j in pose2d.joints.values() if j.detected]),
        "3d_joints": len(pose3d.joints),
    }
    with open(os.path.join(out_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    return out_dir, pose2d, pose3d, cam


if __name__ == "__main__":
    for fn in [make_fixture_standing, make_fixture_depth, make_fixture_complex]:
        result = fn()
        if result[0] is None:
            print(f"  Skipped")
