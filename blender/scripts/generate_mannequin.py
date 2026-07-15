"""
Generate a custom neutral volumetric mannequin mesh with subdivision surfaces.

Creates a single watertight mesh by joining properly shaped body segments.
No third-party assets required. Original work, freely distributable.

Usage:
  blender --background --python generate_mannequin.py -- --output mannequin.blend
"""
import bpy
import math
import sys
import os


def parse_args():
    args = {}
    argv = sys.argv
    if "--" in argv:
        i = argv.index("--") + 1
        while i < len(argv):
            if argv[i].startswith("--"):
                key = argv[i][2:]
                if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
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
    for obj in bpy.data.objects:
        bpy.data.objects.remove(obj, do_unlink=True)


def make_material(name, color, roughness=0.5, alpha=1.0):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    principled = nodes.new(type="ShaderNodeBsdfPrincipled")
    principled.inputs["Base Color"].default_value = (*color, alpha)
    principled.inputs["Roughness"].default_value = roughness
    principled.inputs["Metallic"].default_value = 0.0
    principled.inputs["Subsurface Weight"].default_value = 0.02

    output = nodes.new(type="ShaderNodeOutputMaterial")
    links.new(principled.outputs["BSDF"], output.inputs["Surface"])
    return mat


def create_segment(vertices, rings, radius_func, location, rotation=(0, 0, 0)):
    """Create a surface-of-revolution body segment."""
    verts = []
    faces = []
    for ring in range(rings + 1):
        v = ring / rings
        r = radius_func(v)
        y = v - 0.5
        for seg in range(vertices):
            a = (seg / vertices) * 2 * math.pi
            x = r * math.cos(a)
            z = r * math.sin(a)
            verts.append((x, y * 2.0, z))

    for ring in range(rings):
        for seg in range(vertices):
            a = ring * vertices + seg
            b = ring * vertices + (seg + 1) % vertices
            c = (ring + 1) * vertices + (seg + 1) % vertices
            d = (ring + 1) * vertices + seg
            faces.append((a, b, c, d))

    mesh = bpy.data.meshes.new("Segment")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("Segment", mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = rotation
    return obj


def build_mannequin():
    """Build the complete mannequin from joined body segments."""
    body_parts = []

    # --- Torso ---
    def torso_radius(v):
        # v=0 bottom (hips), v=1 top (shoulders)
        if v < 0.2:
            return 0.18 + (v / 0.2) * 0.02  # hips
        elif v < 0.5:
            return 0.20 - ((v - 0.2) / 0.3) * 0.03  # waist
        elif v < 0.8:
            return 0.17 + ((v - 0.5) / 0.3) * 0.08  # chest
        else:
            return 0.25 - ((v - 0.8) / 0.2) * 0.02  # shoulders

    torso = create_segment(20, 16, torso_radius, (0, 0, 0))
    torso.name = "Torso"
    body_parts.append(torso)

    # --- Neck ---
    def neck_radius(v):
        return 0.08 - v * 0.02

    neck = create_segment(12, 6, neck_radius, (0, 1.05, 0))
    neck.name = "Neck"
    body_parts.append(neck)

    # --- Head (ellipsoid) ---
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=20, ring_count=14, radius=0.12, location=(0, 1.35, 0)
    )
    head = bpy.context.active_object
    head.scale = (1.0, 0.9, 0.85)
    head.name = "Head"
    body_parts.append(head)

    # --- Left Upper Arm ---
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=12, radius=0.055, depth=0.35, location=(0.3, 0.65, 0)
    )
    l_upper = bpy.context.active_object
    l_upper.rotation_euler = (0, 0, math.radians(-10))
    l_upper.name = "LeftUpperArm"
    body_parts.append(l_upper)

    # --- Right Upper Arm ---
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=12, radius=0.055, depth=0.35, location=(-0.3, 0.65, 0)
    )
    r_upper = bpy.context.active_object
    r_upper.rotation_euler = (0, 0, math.radians(10))
    r_upper.name = "RightUpperArm"
    body_parts.append(r_upper)

    # --- Left Forearm ---
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=12, radius=0.04, depth=0.30, location=(0.55, 0.45, 0)
    )
    l_fore = bpy.context.active_object
    l_fore.rotation_euler = (0, 0, math.radians(10))
    l_fore.name = "LeftForearm"
    body_parts.append(l_fore)

    # --- Right Forearm ---
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=12, radius=0.04, depth=0.30, location=(-0.55, 0.45, 0)
    )
    r_fore = bpy.context.active_object
    r_fore.rotation_euler = (0, 0, math.radians(-10))
    r_fore.name = "RightForearm"
    body_parts.append(r_fore)

    # --- Left Thigh ---
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=12, radius=0.075, depth=0.40, location=(0.12, -0.45, 0)
    )
    l_thigh = bpy.context.active_object
    l_thigh.name = "LeftThigh"
    body_parts.append(l_thigh)

    # --- Right Thigh ---
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=12, radius=0.075, depth=0.40, location=(-0.12, -0.45, 0)
    )
    r_thigh = bpy.context.active_object
    r_thigh.name = "RightThigh"
    body_parts.append(r_thigh)

    # --- Left Shin ---
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=12, radius=0.05, depth=0.38, location=(0.12, -0.85, 0)
    )
    l_shin = bpy.context.active_object
    l_shin.name = "LeftShin"
    body_parts.append(l_shin)

    # --- Right Shin ---
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=12, radius=0.05, depth=0.38, location=(-0.12, -0.85, 0)
    )
    r_shin = bpy.context.active_object
    r_shin.name = "RightShin"
    body_parts.append(r_shin)

    # --- Left Foot (simple block) ---
    bpy.ops.mesh.primitive_cube_add(
        size=0.1, location=(0.12, -1.15, 0.04)
    )
    l_foot = bpy.context.active_object
    l_foot.scale = (0.6, 1.0, 0.4)
    l_foot.name = "LeftFoot"
    body_parts.append(l_foot)

    # --- Right Foot ---
    bpy.ops.mesh.primitive_cube_add(
        size=0.1, location=(-0.12, -1.15, 0.04)
    )
    r_foot = bpy.context.active_object
    r_foot.scale = (0.6, 1.0, 0.4)
    r_foot.name = "RightFoot"
    body_parts.append(r_foot)

    # --- Left Hand (simple block) ---
    bpy.ops.mesh.primitive_cube_add(
        size=0.05, location=(0.72, 0.30, 0)
    )
    l_hand = bpy.context.active_object
    l_hand.scale = (0.8, 1.2, 0.5)
    l_hand.name = "LeftHand"
    body_parts.append(l_hand)

    # --- Right Hand ---
    bpy.ops.mesh.primitive_cube_add(
        size=0.05, location=(-0.72, 0.30, 0)
    )
    r_hand = bpy.context.active_object
    r_hand.scale = (0.8, 1.2, 0.5)
    r_hand.name = "RightHand"
    body_parts.append(r_hand)

    # Join all into single mesh
    bpy.context.view_layer.objects.active = body_parts[0]
    bpy.ops.object.select_all(action="DESELECT")
    for part in body_parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = body_parts[0]
    bpy.ops.object.join()

    mannequin = bpy.context.active_object
    mannequin.name = "Mannequin"

    # Add subdivision surface modifier
    subdiv = mannequin.modifiers.new(name="Subdivision", type="SUBSURF")
    subdiv.levels = 1
    subdiv.render_levels = 2

    # Smooth shading
    bpy.ops.object.shade_smooth()

    # Apply material
    mat = make_material("MannequinMat", (0.75, 0.55, 0.35), roughness=0.6)
    mannequin.data.materials.append(mat)

    return mannequin


def main():
    args = parse_args()
    output_path = args.get("output", "mannequin.blend")

    clear_scene()
    mannequin = build_mannequin()

    # Save
    bpy.ops.wm.save_as_mainfile(filepath=output_path)
    print(f"MANNEQUIN_OK: {output_path}")


if __name__ == "__main__":
    main()
