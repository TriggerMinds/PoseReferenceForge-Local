"""Build PyInstaller distribution for PoseReferenceForge Local."""
import sys, os, shutil, subprocess
from pathlib import Path

REPO = Path(__file__).parent.parent
DIST = REPO / "dist"

if DIST.exists():
    shutil.rmtree(DIST)

# Ensure icon exists
icon = REPO / "assets" / "icons" / "app_icon.ico"
icon.parent.mkdir(parents=True, exist_ok=True)
if not icon.exists():
    from PIL import Image
    img = Image.new("RGBA", (64, 64), (200, 140, 80, 255))
    img.save(str(icon), format="ICO", sizes=[(64, 64)])

spec = f"""
# -*- mode: python ; coding: utf-8 -*-
import sys
a = Analysis(
    ['app/main.py'],
    pathex=[r'{REPO}'],
    datas=[
        (r'{REPO / "blender"}', 'blender'),
        (r'{REPO / "assets"}', 'assets'),
        (r'{REPO / "schemas"}', 'schemas'),
        (r'{REPO / "models/manifests"}', 'models/manifests'),
        (r'{REPO / "docs"}', 'docs'),
        (r'{REPO / "scripts"}', 'scripts'),
    ],
    hiddenimports=[
        'PySide6.QtOpenGL', 'PySide6.QtOpenGLWidgets',
        'OpenGL', 'OpenGL.GL', 'OpenGL.GLU',
        'ultralytics', 'mediapipe',
        'cv2', 'PIL', 'scipy.optimize',
        'requests', 'filetype', 'jsonschema', 'yaml',
        'packaging', 'psutil', 'trimesh',
    ],
    hookspath=[], hooksconfig={{}}, runtime_hooks=[], excludes=[],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [],
    name='PoseReferenceForge', debug=False, bootloader_ignore_signals=False,
    strip=True, upx=True, console=False, disable_windowed_traceback=False,
    icon=r'{icon}')
"""

with open(REPO / "PoseReferenceForge.spec", "w") as f:
    f.write(spec)

subprocess.run([
    str(REPO / ".venv" / "Scripts" / "pyinstaller.exe"),
    "PoseReferenceForge.spec",
    "--clean", "--noconfirm",
], cwd=str(REPO))

exe_path = DIST / "PoseReferenceForge" / "PoseReferenceForge.exe"
if exe_path.exists():
    size_mb = exe_path.stat().st_size / (1024*1024)
    total_mb = sum(f.stat().st_size for f in (DIST / "PoseReferenceForge").rglob("*")) / (1024*1024)
    print(f"EXE: {size_mb:.0f} MB")
    print(f"Total distribution: {total_mb:.0f} MB")
    print(f"Path: {exe_path}")
else:
    print("Build failed: executable not found")
    # List dist contents for debugging
    for p in DIST.rglob("*"):
        print(f"  {p.relative_to(DIST)}")
