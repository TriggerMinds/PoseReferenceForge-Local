"""Benchmark the optimized fitting pipeline against heuristic baseline."""
import sys, os, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import cv2, numpy as np
import ultralytics

ULT_DIR = os.path.dirname(ultralytics.__file__)
ASSETS_DIR = os.path.join(ULT_DIR, "assets")
EVIDENCE_DIR = "evidence/benchmarks"
os.makedirs(EVIDENCE_DIR, exist_ok=True)
os.makedirs("evidence/camera_match", exist_ok=True)

FIXTURES = {
    "bus_front": os.path.join(ASSETS_DIR, "bus.jpg"),
    "zidane_front": os.path.join(ASSETS_DIR, "zidane.jpg"),
}


def load_image(path):
    if not os.path.exists(path):
        return None
    return cv2.imread(path)


def run_benchmark():
    from app.pose2d.detection_pipeline import run_detection
    from app.pose3d.lifting_pipeline import lift_to_3d
    from app.optimization.pose_fitter import ScipyPoseFitter
    from app.optimization.reprojection import evaluate_reprojection

    results = {}
    fitter = ScipyPoseFitter()

    for name, path in FIXTURES.items():
        img = load_image(path)
        if img is None:
            print(f"SKIP {name}: image not found")
            continue

        print(f"\n=== {name} ===")
        detection = run_detection(img)
        if not detection.pose2d.joints:
            print(f"  No joints detected")
            continue

        # Heuristic baseline
        t0 = time.time()
        heuristic_pose = lift_to_3d(detection.pose2d)
        t_heuristic = time.time() - t0

        # Optimized fit
        t0 = time.time()
        optimized_pose, fit_info = fitter.fit(detection.pose2d, heuristic_pose)
        t_optimized = time.time() - t0

        img_w = detection.pose2d.image_width or 1000
        img_h = detection.pose2d.image_height or 1000
        camera = {
            "focal_length": max(img_w, img_h) * 1.2,
            "cx": img_w / 2,
            "cy": img_h / 2,
            "azimuth": 0, "elevation": 0, "roll": 0,
            "tx": 0, "ty": 0,
            "tz": max(img_w, img_h) * 2.0,
        }

        heuristic_eval = evaluate_reprojection(detection.pose2d, heuristic_pose, camera)
        optimized_eval = evaluate_reprojection(detection.pose2d, optimized_pose, camera)

        rme_before = float(heuristic_eval["rme"])
        rme_after = float(optimized_eval["rme"])
        improvement_pct = ((rme_before - rme_after) / max(rme_before, 0.001)) * 100

        entry = {
            "fixture": name,
            "detected_joints": len([j for j in detection.pose2d.joints.values() if j.detected]),
            "heuristic": {
                "time_s": round(t_heuristic, 4),
                "rme_px": round(rme_before, 2),
                "joints": len(heuristic_pose.joints),
            },
            "optimized": {
                "time_s": round(t_optimized, 4),
                "rme_px": round(rme_after, 2),
                "joints": len(optimized_pose.joints),
                "iterations": fit_info.get("iterations", 0),
                "success": fit_info.get("success", False),
            },
            "improvement_pct": round(improvement_pct, 1),
        }
        results[name] = entry
        print(f"  Heuristic: RME={rme_before:.2f}px ({t_heuristic:.3f}s)")
        print(f"  Optimized: RME={rme_after:.2f}px ({t_optimized:.3f}s)")
        print(f"  Improvement: {improvement_pct:.1f}%")

    # Save results
    out_path = os.path.join(EVIDENCE_DIR, "recovery_03_reprojection.json")
    with open(out_path, "w") as f:
        json.dump({
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            "pipeline": "heuristic baseline → scipy constrained optimization",
            "fixtures": results,
            "summary": {
                "fixtures_tested": len(results),
                "fixtures_improved": sum(
                    1 for v in results.values() if v["improvement_pct"] > 0
                ),
            },
        }, f, indent=2)
    print(f"\nResults saved to {out_path}")

    # Also save a camera match visual test
    print("\nGenerating camera match overlay...")
    single_name = list(results.keys())[0] if results else None
    if single_name and single_name in results:
        import ultralytics
        img_path = FIXTURES[single_name]
        img = load_image(img_path)
        if img is not None:
            from app.pose2d.detection_pipeline import run_detection
            det = run_detection(img)
            heuristic = lift_to_3d(det.pose2d)
            fitter2 = ScipyPoseFitter()
            opt_pose, info = fitter2.fit(det.pose2d, heuristic)
            from PySide6 import QtWidgets, QtCore
            app = QtWidgets.QApplication(sys.argv)
            app.setApplicationName("Benchmark")
            from app.ui.camera_match_panel import CameraMatchPanel
            panel = CameraMatchPanel()
            panel.set_data(det.pose2d, opt_pose, img)
            panel._auto_fit()
            QtCore.QTimer.singleShot(1000, app.quit)
            QtCore.QTimer.singleShot(100, lambda: panel.grab().save(
                "evidence/camera_match/recovery_03_camera_match_overlay.png"
            ))
            app.exec()
            print("Camera match overlay saved")

    return results


if __name__ == "__main__":
    run_benchmark()
