
# -*- mode: python ; coding: utf-8 -*-
import sys
a = Analysis(
    ['app/main.py'],
    pathex=[r'C:\Users\gewoo\New folder (124)'],
    datas=[
        (r'C:\Users\gewoo\New folder (124)\blender', 'blender'),
        (r'C:\Users\gewoo\New folder (124)\assets', 'assets'),
        (r'C:\Users\gewoo\New folder (124)\schemas', 'schemas'),
        (r'C:\Users\gewoo\New folder (124)\models\manifests', 'models/manifests'),
        (r'C:\Users\gewoo\New folder (124)\docs', 'docs'),
        (r'C:\Users\gewoo\New folder (124)\scripts', 'scripts'),
    ],
    hiddenimports=[
        'PySide6.QtOpenGL', 'PySide6.QtOpenGLWidgets',
        'OpenGL', 'OpenGL.GL', 'OpenGL.GLU',
        'ultralytics', 'mediapipe',
        'cv2', 'PIL', 'scipy.optimize',
        'requests', 'filetype', 'jsonschema', 'yaml',
        'packaging', 'psutil', 'trimesh',
    ],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [],
    name='PoseReferenceForge', debug=False, bootloader_ignore_signals=False,
    strip=True, upx=True, console=False, disable_windowed_traceback=False,
    icon=r'C:\Users\gewoo\New folder (124)\assets\icons\app_icon.ico')
