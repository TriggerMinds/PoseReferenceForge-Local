# Troubleshooting

## Detection fails

- Ensure the source image clearly shows a person
- Try a different pose (profile/back views may have lower confidence)
- Run `scripts\verify_environment.ps1` to check dependencies
- Try CPU fallback: disable GPU in Settings

## Blender not found

- Install Blender 5.1 or later
- Configure the path in Settings → General → Blender Path
- Verify with `scripts\verify_environment.ps1`

## CUDA out of memory

- Close other GPU-intensive applications
- Use a smaller model (YOLOv8n-pose uses ~300 MB VRAM)
- Disable GPU acceleration in Settings (CPU fallback)

## Application won't start

- Run `scripts\verify_environment.ps1`
- Check `%USERPROFILE%\.posereferenceforge\` for log files
- Ensure Python 3.12 is installed and venv is active
- Re-run `scripts\setup_windows.ps1`

## Render output is blank

- Check Blender path in Settings
- Ensure pose data exists (run detection first)
- Check the Blender script at `blender\scripts\render_mannequin.py`

## Exported image looks wrong

- Use the source-matched camera for primary export
- Check the pose in the 3D viewport before exporting
- Use the preflight checker before final export
