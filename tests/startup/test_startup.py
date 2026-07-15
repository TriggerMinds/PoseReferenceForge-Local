"""Startup smoke test: verify MainWindow and all UI components construct successfully."""
import sys, os, traceback
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6 import QtWidgets, QtCore


def test_module_imports():
    """Verify all critical UI modules import without error."""
    from app.ui import main_window
    from app.ui import source_panel
    from app.ui import viewport_3d
    from app.ui import properties_panel
    from app.ui import camera_match_panel
    from app.ui import dialogs
    from app.ui import pose_library_dialog
    assert hasattr(main_window, "MainWindow")
    assert hasattr(source_panel, "SourcePanel")
    assert hasattr(viewport_3d, "Viewport3D")
    assert hasattr(properties_panel, "PropertiesPanel")
    assert hasattr(camera_match_panel, "CameraMatchPanel")
    assert hasattr(dialogs, "ExportDialog")
    assert hasattr(pose_library_dialog, "PoseLibraryDialog")
    return True


def test_main_window_construction():
    """Verify MainWindow constructs without NameError/ImportError/AttributeError."""
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("StartupTest")

    from app.ui.main_window import MainWindow
    mw = MainWindow()
    assert mw is not None
    assert mw.windowTitle() != ""
    assert mw.source_panel is not None
    assert mw.viewport_3d is not None
    assert mw.properties_panel is not None

    # Verify toolbar, menus, status bar
    assert mw.menuBar() is not None
    assert mw.statusBar() is not None
    assert hasattr(mw, "act_quick_export")

    mw.show()
    QtCore.QTimer.singleShot(50, mw.close)
    QtCore.QTimer.singleShot(100, app.quit)
    app.exec()
    return True


def test_dialog_imports():
    """Verify dialogs can be constructed."""
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    from app.ui.dialogs import NewProjectDialog, SettingsDialog, ExportDialog
    nd = NewProjectDialog()
    assert nd is not None

    from app.config.settings import Settings
    sd = SettingsDialog(Settings.get())
    assert sd is not None

    ed = ExportDialog({})
    assert ed is not None
    return True


def test_pipeline_imports():
    """Verify the full pipeline modules import."""
    from app.pose2d import detection_pipeline
    from app.pose3d import lifting_pipeline
    from app.optimization import pose_fitter, reprojection
    from app.exporters import export_service, pack_orchestrator, pack_exporter
    from app.rendering import blender_renderer
    from app.preflight import validator
    from app.library import pose_library
    assert hasattr(detection_pipeline, "run_detection")
    assert hasattr(lifting_pipeline, "lift_to_3d")
    assert hasattr(pose_fitter, "ScipyPoseFitter")
    return True


if __name__ == "__main__":
    results = {}
    for name, fn in [
        ("module_imports", test_module_imports),
        ("main_window_construction", test_main_window_construction),
        ("dialog_imports", test_dialog_imports),
        ("pipeline_imports", test_pipeline_imports),
    ]:
        try:
            fn()
            results[name] = "PASS"
            print(f"  PASS: {name}")
        except Exception as e:
            results[name] = f"FAIL: {e}"
            traceback.print_exc()
            print(f"  FAIL: {name}: {e}")

    print()
    passed = sum(1 for v in results.values() if v == "PASS")
    print(f"Results: {passed}/{len(results)} passed")
    sys.exit(0 if passed == len(results) else 1)
