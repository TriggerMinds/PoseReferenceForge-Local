# Architecture

## Overview

PoseReferenceForge Local is a modular desktop application built in Python with PySide6.

The application converts a pose photograph into a neutral 3D mannequin in the same pose, then exports clean pose-reference images.

## Core Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Main Window (PySide6)                        │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │  Source Panel │  │  3D Viewport     │  │  Properties Panel    │  │
│  │  - Image      │  │  - Mannequin     │  │  - Joint info        │  │
│  │  - 2D skeleton│  │  - Gizmos        │  │  - Locks             │  │
│  │  - Joint edit │  │  - Camera        │  │  - Warnings          │  │
│  └──────────────┘  └──────────────────┘  └──────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Bottom Status Bar                          │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Layer Architecture

### 1. Infrastructure Layer
- `app/config/` — Application configuration
- `app/persistence/` — Project save/load, SQLite library
- `app/diagnostics/` — Logging, diagnostics, error handling
- `app/workers/` — Background task management

### 2. Domain Layer
- `app/domain/` — Core domain models (Joint, Pose, Person, Project)
- `app/schemas/` — JSON schemas for data validation

### 3. Detection Layer
- `app/detectors/` — Person and pose detection interfaces and implementations
- `app/pose2d/` — 2D pose representation, editing, schema conversion

### 4. 3D Layer
- `app/pose3d/` — 3D pose initialization and lifting
- `app/optimization/` — IK optimization, anatomical constraints
- `app/camera/` — Camera estimation and matching
- `app/rigging/` — Rig mapping and transform application
- `app/mannequin/` — Mannequin assets and generation

### 5. Presentation Layer
- `app/viewport/` — 3D viewport backend
- `app/rendering/` — Blender-based rendering
- `app/exporters/` — Export profiles and packs
- `app/preflight/` — Export validation
- `app/ui/` — PySide6 UI components

### 6. Services Layer
- `app/services/` — Orchestration services connecting all layers

## Key Interfaces

```python
class PersonDetector(ABC):
    def detect(self, image: np.ndarray) -> list[Person]: ...

class PoseDetector(ABC):
    def detect(self, image: np.ndarray, person: Person) -> Pose2D: ...

class PoseLifter(ABC):
    def lift(self, pose2d: Pose2D, camera: Camera) -> Pose3D: ...

class RigPoseOptimizer:
    def optimize(self, pose3d: Pose3D, constraints: Constraints) -> RigPose: ...

class ViewportBackend(ABC):
    def render_scene(self, scene: Scene): ...
    def get_camera(self) -> Camera: ...
    def set_gizmo(self, joint: Joint): ...

class RenderBackend(ABC):
    def render(self, scene: Scene, profile: RenderProfile) -> RenderResult: ...
```

## Data Flow (Daily Workflow)

```
Image → PersonDetector → Person → PoseDetector → Pose2D → [2D Correction]
→ PoseLifter → Pose3D → RigPoseOptimizer → RigPose → [3D Correction]
→ CameraEstimator → CameraMatch → [Camera Adjustment]
→ Scene → ViewportBackend | RenderBackend → Export
```

## Models Directory

```
models/
  yolov8n-pose.pt    — Person + pose detection (ultralytics)
  yolov8s-pose.pt    — Higher accuracy variant
```

Models are documented in `models/manifests/` with checksums and license info.
