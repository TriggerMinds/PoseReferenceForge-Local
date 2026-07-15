"""Check MediaPipe API availability."""
import sys
sys.path.insert(0, "C:\\Users\\gewoo\\New folder (124)")

# Check what's actually in the tasks package
import mediapipe.tasks as t
print("BaseOptions in dir:", "BaseOptions" in dir(t))
print("BaseOptions type:", type(t.BaseOptions))

# Check python subpackage
try:
    import mediapipe.tasks.python as mp_py
    print("python subpackage: OK")
    print("python.vision:", hasattr(mp_py, "vision"))
except Exception as e:
    print(f"python subpackage FAIL: {e}")

# Check vision subpackage  
try:
    import mediapipe.tasks.python.vision as mpv
    print("python.vision subpackage: OK")
    print(dir(mpv)[:10])
except Exception as e:
    print(f"python.vision subpackage FAIL: {e}")
