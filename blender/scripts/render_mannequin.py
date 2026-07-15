"""
Blender Python script to render a mannequin pose.

Usage:
  blender --background --python render_mannequin.py -- \
    --pose_json <path> \
    --output <path> \
    --width 1536 --height 2048 \
    --background 240 240 240 \
    --transparent 0 \
    --azimuth 0 --elevation 0 \
    --distance 2.5

Arguments after `--` are parsed as pose data and render settings.
"""

import bpy
import math
import json
import sys
import os
from pathlib import Path


def parse_args():
    args = {}
    argv = sys.argv
    if '--' in argv:
        idx = argv.index('--')
        i = idx + 1
        while i < len(argv):
            if argv[i].startswith('--'):
                key = argv[i][2:]
                if i + 1 < len(argv) and not argv[i + 1].startswith('--'):
                    args[key] = argv[i + 1]
                    i += 2
                else:
                    args[key] = True
                    i += 1
            else:
                i += 1
    return args


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # Remove default objects
    for obj in bpy.data.objects:
        bpy.data.objects.remove(obj, do_unlink=True)


def create_material(name, color, alpha=1.0):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    principled.inputs['Base Color'].default_value = (*color, alpha)
    principled.inputs['Roughness'].default_value = 0.6
    principled.inputs['Metallic'].default_value = 0.0
    principled.inputs['Subsurface Weight'].default_value = 0.05
    principled.inputs['Subsurface Radius'].default_value = (0.2, 0.1, 0.05)

    output = nodes.new(type='ShaderNodeOutputMaterial')
    links.new(principled.outputs['BSDF'], output.inputs['Surface'])

    if alpha < 1.0:
        mat.blend_method = 'BLEND'
        principled.inputs['Alpha'].default_value = alpha

    return mat


def create_torso(hips_width, shoulders_width, height, location, color):
    """Create a simplified torso from a tapered cylinder."""
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=16,
        radius1=shoulders_width / 2,
        radius2=hips_width / 2,
        depth=height,
        location=location,
    )
    obj = bpy.context.active_object
    obj.name = "Torso"
    mat = create_material("torso_mat", color)
    obj.data.materials.append(mat)
    return obj


def create_limb(p1, p2, radius, color, name="Limb"):
    """Create a cylinder between two 3D points."""
    from mathutils import Vector

    v1 = Vector(p1)
    v2 = Vector(p2)
    mid = (v1 + v2) / 2
    direction = v2 - v1
    length = direction.length

    if length < 0.005:
        return None

    direction.normalize()
    up = Vector((0, 0, 1))

    bpy.ops.mesh.primitive_cylinder_add(
        vertices=8,
        radius=radius,
        depth=length,
        location=mid,
    )
    obj = bpy.context.active_object
    obj.name = name

    rot = up.rotation_difference(direction)
    obj.rotation_euler = rot.to_euler()

    mat = create_material(f"{name}_mat", color)
    obj.data.materials.append(mat)
    return obj


def create_sphere(location, radius, color, name="Joint"):
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=radius,
        location=location,
    )
    obj = bpy.context.active_object
    obj.name = name
    mat = create_material(f"{name}_mat", color)
    obj.data.materials.append(mat)
    return obj


def build_mannequin(joints):
    """Build a volumetric mannequin from joint positions."""
    body_color = (0.75, 0.55, 0.35)    # Warm skin tone
    joint_color = (0.60, 0.40, 0.25)   # Darker for joints
    limb_radius = 0.04
    joint_radius = 0.035

    skeleton = [
        ("pelvis", "lower_spine"), ("lower_spine", "upper_spine"),
        ("upper_spine", "neck"), ("neck", "head"),
        ("neck", "left_shoulder"), ("neck", "right_shoulder"),
        ("left_shoulder", "left_elbow"), ("right_shoulder", "right_elbow"),
        ("left_elbow", "left_wrist"), ("right_elbow", "right_wrist"),
        ("left_wrist", "left_hand"), ("right_wrist", "right_hand"),
        ("pelvis", "left_hip"), ("pelvis", "right_hip"),
        ("left_hip", "left_knee"), ("right_hip", "right_knee"),
        ("left_knee", "left_ankle"), ("right_knee", "right_ankle"),
    ]

    # Create all limb cylinders
    for j1, j2 in skeleton:
        if j1 in joints and j2 in joints:
            p1 = joints[j1]
            p2 = joints[j2]
            create_limb(p1, p2, limb_radius, body_color, f"Bone_{j1}_{j2}")

    # Create joint spheres
    for jid, pos in joints.items():
        vis = True
        if jid in ("left_hand", "right_hand"):
            create_sphere(pos, joint_radius * 1.2, joint_color, f"Joint_{jid}")
        elif jid in ("head",):
            create_sphere(pos, 0.08, (0.78, 0.58, 0.38), f"Joint_{jid}")
        else:
            create_sphere(pos, joint_radius, joint_color, f"Joint_{jid}")

    # Head marker (slightly larger)
    if "head" in joints:
        h = joints["head"]
        create_sphere((h[0], h[1], h[2] + 0.02), 0.07, joint_color, "Head_marker")


def setup_camera(azimuth, elevation, distance, roll=0):
    """Set up the render camera."""
    bpy.ops.object.camera_add()
    cam = bpy.context.active_object
    cam.name = "RenderCamera"

    # Convert to radians
    az_rad = math.radians(azimuth)
    el_rad = math.radians(elevation)

    # Spherical coordinates
    x = distance * math.cos(el_rad) * math.sin(az_rad)
    y = distance * math.cos(el_rad) * math.cos(az_rad)
    z = distance * math.sin(el_rad)

    cam.location = (x, y, z + 0.3)
    cam.rotation_euler = (math.radians(90 + elevation), 0, math.radians(azimuth))
    bpy.context.scene.camera = cam
    return cam


def setup_lighting():
    """Set up three-point lighting."""
    # Key light
    bpy.ops.object.light_add(type='AREA', location=(0.5, -1.5, 2.0))
    key = bpy.context.active_object
    key.data.energy = 300
    key.data.size = 1.5

    # Fill light
    bpy.ops.object.light_add(type='AREA', location=(-0.8, 1.0, 0.5))
    fill = bpy.context.active_object
    fill.data.energy = 150
    fill.data.size = 1.5

    # Rim light
    bpy.ops.object.light_add(type='AREA', location=(0.0, 1.5, 1.5))
    rim = bpy.context.active_object
    rim.data.energy = 100
    rim.data.size = 1.0


def setup_world(background_color):
    world = bpy.context.scene.world
    if world:
        world.use_nodes = True
        if world.node_tree and 'Background' in world.node_tree.nodes:
            bg = world.node_tree.nodes['Background']
            bg.inputs[0].default_value = (*background_color, 1)


def main():
    args = parse_args()

    pose_path = args.get('pose_json', '')
    output_path = args.get('output', 'render_output.png')
    width = int(args.get('width', '1536'))
    height = int(args.get('height', '2048'))
    bg_r = float(args.get('background_r', '240')) / 255
    bg_g = float(args.get('background_g', '240')) / 255
    bg_b = float(args.get('background_b', '240')) / 255
    transparent = bool(int(args.get('transparent', '0')))
    jpeg = bool(int(args.get('jpeg', '0')))
    jpeg_quality = int(args.get('quality', '95'))
    azimuth = float(args.get('azimuth', '0'))
    elevation = float(args.get('elevation', '0'))
    distance = float(args.get('distance', '2.5'))

    # Load pose
    joints = {}
    if pose_path and os.path.exists(pose_path):
        with open(pose_path) as f:
            pose_data = json.load(f)
        joints = pose_data.get('joints', pose_data)

    # Convert to (x, z*0.5, y) for Blender coordinates
    bl_joints = {}
    for jid, jdata in joints.items():
        if isinstance(jdata, dict):
            x, y, z = jdata.get('x', 0), jdata.get('y', 0), jdata.get('z', 0)
        elif isinstance(jdata, list) and len(jdata) >= 3:
            x, y, z = jdata[0], jdata[1], jdata[2]
        else:
            continue
        # Scale down and convert: y-up in Blender
        scale = 0.002
        bl_joints[jid] = (x * scale, z * scale, y * scale)

    # Build scene
    clear_scene()

    # Try to load custom mannequin mesh; fallback to procedural
    mannequin_blend = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "mannequins", "mannequin_base.blend")
    mannequin_loaded = False
    if os.path.exists(mannequin_blend):
        try:
            with bpy.data.libraries.load(mannequin_blend) as (data_from, data_to):
                if data_from.objects:
                    data_to.objects = data_from.objects[:]
            for obj in data_to.objects:
                if obj is not None:
                    bpy.context.collection.objects.link(obj)
            mannequin_loaded = len([o for o in bpy.context.scene.objects if o.type == "MESH"]) > 0
        except Exception as e:
            print(f"Could not load mannequin blend: {e}")

    if mannequin_loaded:
        # Position mannequin at pose center
        for obj in bpy.context.scene.objects:
            if obj.type == "MESH":
                # Estimate pose center from joints
                center = [0.0, 0.0, 0.0]
                count = 0
                for jid, pos in bl_joints.items():
                    center = (center[0] + pos[0], center[1] + pos[1], center[2] + pos[2])
                    count += 1
                if count > 0:
                    center = (center[0]/count, center[1]/count, center[2]/count)
                obj.location = center
                # Scale to roughly match pose size
                if bl_joints:
                    xs = [p[0] for p in bl_joints.values()]
                    zs = [p[1] for p in bl_joints.values()]
                    ys = [p[2] for p in bl_joints.values()]
                    size = max(max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs))
                    obj.scale = (size * 2, size * 2, size * 2)
    else:
        print("Custom mannequin not available, using procedural fallback")
        build_mannequin(bl_joints)

    setup_camera(azimuth, elevation, distance)
    setup_lighting()
    setup_world((bg_r, bg_g, bg_b))

    # Render settings
    bpy.context.scene.render.resolution_x = width
    bpy.context.scene.render.resolution_y = height
    bpy.context.scene.render.resolution_percentage = 100

    if jpeg:
        bpy.context.scene.render.image_settings.file_format = 'JPEG'
        bpy.context.scene.render.image_settings.quality = jpeg_quality
        bpy.context.scene.render.image_settings.color_mode = 'RGB'
    else:
        bpy.context.scene.render.image_settings.file_format = 'PNG'
        if transparent:
            bpy.context.scene.render.image_settings.color_mode = 'RGBA'
            bpy.context.scene.render.film_transparent = True
        else:
            bpy.context.scene.render.image_settings.color_mode = 'RGB'
            bpy.context.scene.render.film_transparent = False

    bpy.context.scene.render.filepath = output_path

    # Render
    bpy.ops.render.render(write_still=True)
    print(f'RENDER_OK: {output_path}')


if __name__ == '__main__':
    main()
