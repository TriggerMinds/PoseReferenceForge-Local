# Viewport Decision

## Evaluated Approaches

### 1. PySide6 + Qt OpenGL (Selected)
- **Approach:** QOpenGLWidget with PyOpenGL
- **Status:** Implemented and functional
- **Pros:**
  - Native PySide6 integration
  - No additional dependencies beyond PyOpenGL
  - Full control over rendering pipeline
  - Direct joint picking via OpenGL selection
  - Works with all Qt layouts and widgets
- **Cons:**
  - Custom rendering code required for skinned mesh
  - No built-in animation system
  - Manual gizmo implementation needed
- **Performance:** Good for wireframe, joint markers, basic volumes

### 2. PyGFX (Evaluated, Not Selected)
- Modern wgpu-based renderer
- Qt integration available but less mature
- Requires additional dependency and wgpu-native
- Not production-tested on Windows 10/11

### 3. Panda3D (Not Selected)
- Full game engine, heavy dependency
- Qt embedding is possible but fragile
- 200+ MB install size
- Overkill for static pose viewing

### 4. VTK/PyVista (Not Selected)
- Excellent for scientific visualization
- Poor for character animation and rig manipulation
- Transform gizmos not built in

## Architecture Decision

Use **QOpenGLWidget + PyOpenGL** for the interactive 3D viewport.

Blender will be used for high-quality final renders (PNG/JPG output).

The viewport provides:
- Orbital camera navigation
- Joint selection and highlighting
- FK rotation gizmos
- IK target manipulation via handles
- Mannequin display (wireframe + simple volumes)
- Camera match overlay

For Phase 4, the viewport will gain:
- Improved mannequin rendering (cylinder/skeleton based)
- Transform gizmos (rotation, translation)
- Joint locking with visual feedback
- Undo/redo for joint edits
