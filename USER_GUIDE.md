# User Guide

## Getting Started

1. Launch PoseReferenceForge Local from START.bat or the Start Menu.
2. Click **New Project** and enter a project name.
3. Click **Import Image** and select a pose photograph (JPG, PNG, WEBP).

## Detecting a Pose

1. After importing an image, click **Detect Pose**.
2. The application detects all visible people and identifies the primary subject.
3. 2D skeleton joints are overlaid on the source image.
4. Green dots indicate high-confidence detections, yellow dots are inferred.

## Correcting 2D Joints

1. Click and drag any joint dot to adjust its position.
2. Use the Properties panel to view joint details.
3. Right-click to reset a joint.

## Generating a 3D Pose

1. After 2D detection, click **Generate 3D Pose**.
2. The application lifts the 2D skeleton to 3D and displays it in the viewport.
3. The mannequin is shown as a skeleton with colored joints.

## Navigating the 3D Viewport

- **Left-click + drag**: Orbit camera
- **Middle-click + drag**: Pan camera
- **Scroll wheel**: Zoom in/out
- **Press R**: Reset camera

## Exporting a Pose Reference

1. Click **Export Reference**.
2. Select a render profile:
   - **Source-Matched Clean**: Primary pose reference with neutral background
   - **Transparent PNG**: Pose with alpha transparency
   - **Depth-Readable**: Enhanced depth perception
   - **Silhouette**: Solid silhouette
   - **Structural**: Skeleton overlay
3. Select resolution and format.
4. Choose pack options (1-image, 2-image, 3-image, or full pack).
5. Click Export.

## Saving and Reopening Projects

- **Save**: Saves the project with all pose data (no rerunning detection needed)
- **Open**: Reopens a previously saved project

## Pose Presets

Saved poses can be reused without the original photograph. The pose library manages your presets.
