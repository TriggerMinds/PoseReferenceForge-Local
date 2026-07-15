"""
Blender Python script — procedural joint-driven pose mannequin.

Each limb is built directly from Pose3D joint coordinates.
No static mesh loading. No armature. Pure procedural geometry.

Usage:
  blender --background --python render_mannequin.py -- \
    --pose_json <path> --output <path> --width 1536 --height 2048
"""
import bpy, math, json, sys, os
from mathutils import Vector


def parse_args():
    args = {}
    argv = sys.argv
    if "--" in argv:
        i = argv.index("--") + 1
        while i < len(argv):
            if argv[i].startswith("--"):
                k = argv[i][2:]
                if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
                    args[k] = argv[i + 1]
                    i += 2
                else:
                    args[k] = True
                    i += 1
            else:
                i += 1
    return args


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for obj in bpy.data.objects:
        bpy.data.objects.remove(obj, do_unlink=True)


def make_mat(name, color, rough=0.6, alpha=1.0):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    n = mat.node_tree.nodes
    n.clear()
    p = n.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (*color, alpha)
    p.inputs["Roughness"].default_value = rough
    out = n.new("ShaderNodeOutputMaterial")
    mat.node_tree.links.new(p.outputs["BSDF"], out.inputs["Surface"])
    return mat


def cyl(p1, p2, r1, r2, color, name):
    """Tapered cylinder from p1 to p2 with radius r1 at p1, r2 at p2."""
    v1, v2 = Vector(p1), Vector(p2)
    mid = (v1 + v2) / 2
    d = v2 - v1
    length = d.length
    if length < 0.002:
        return None
    d.normalize()
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=1, depth=1, location=mid)
    obj = bpy.context.active_object
    obj.name = name
    up = Vector((0, 0, 1))
    q = up.rotation_difference(d)
    obj.rotation_euler = q.to_euler()
    obj.scale = (r1, r1 if abs(r1 - r2) < 0.001 else (r1 + r2) / 2, length)
    mat = make_mat(f"{name}_mat", color)
    obj.data.materials.append(mat)
    return obj


def sphere(pos, radius, color, name):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=pos)
    obj = bpy.context.active_object
    obj.name = name
    mat = make_mat(f"{name}_mat", color)
    obj.data.materials.append(mat)
    return obj


def box(pos, scale, color, name):
    bpy.ops.mesh.primitive_cube_add(size=1, location=pos)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    mat = make_mat(f"{name}_mat", color)
    obj.data.materials.append(mat)
    return obj


def ellipsoid(pos, scale, color, name):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=pos)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    mat = make_mat(f"{name}_mat", color)
    obj.data.materials.append(mat)
    return obj


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


def build_mannequin(j):
    """Build a clean volumetric pose mannequin from joint coordinates."""
    grey = (0.65, 0.62, 0.60)
    dark = (0.50, 0.48, 0.45)
    light_grey = (0.75, 0.72, 0.70)

    # --- TORSO ---
    neck_p = j.get("neck")
    pelvis_p = j.get("pelvis")
    ls = j.get("left_shoulder")
    rs = j.get("right_shoulder")
    lh = j.get("left_hip")
    rh = j.get("right_hip")

    # Tapered torso cylinder
    if neck_p and pelvis_p:
        shoulder_w = abs(ls[0] - rs[0]) * 0.5 if ls and rs else 0.2
        hip_w = abs(lh[0] - rh[0]) * 0.5 if lh and rh else 0.18
        cyl(neck_p, pelvis_p, shoulder_w, hip_w, grey, "Torso")

    # Neck
    head_p = j.get("head")
    if neck_p and head_p:
        cyl(neck_p, head_p, 0.06, 0.04, grey, "Neck")

    # Head (ellipsoid with subtle nose direction)
    if head_p:
        nose = j.get("nose")
        nose_dir = 0.06
        if nose and head_p:
            nd = math.atan2(nose[0] - head_p[0], nose[1] - head_p[1])
            nose_dir = 0.08
        ellipsoid(head_p, (0.10, 0.08, 0.10), light_grey, "Head")

    # --- ARMS ---
    for side, shoulder, elbow, wrist, hand in [
        ("L", "left_shoulder", "left_elbow", "left_wrist", "left_hand"),
        ("R", "right_shoulder", "right_elbow", "right_wrist", "right_hand"),
    ]:
        sp = j.get(shoulder)
        ep = j.get(elbow)
        wp = j.get(wrist)
        hp = j.get(hand)

        if sp and ep:
            cyl(sp, ep, 0.055, 0.04, grey, f"UpperArm_{side}")
        if ep and wp:
            cyl(ep, wp, 0.04, 0.03, grey, f"Forearm_{side}")

        # Simple hand (box oriented toward wrist → forward direction)
        if wp and hp:
            d = (hp[0] - wp[0], hp[1] - wp[1], hp[2] - wp[2])
            hlen = math.sqrt(d[0]**2 + d[1]**2 + d[2]**2)
            if hlen > 0.01:
                box(hp, (0.03, 0.04, 0.015), grey, f"Hand_{side}")

    # --- LEGS ---
    for side, hip, knee, ankle, foot in [
        ("L", "left_hip", "left_knee", "left_ankle", "left_foot"),
        ("R", "right_hip", "right_knee", "right_ankle", "right_foot"),
    ]:
        hp = j.get(hip)
        kp = j.get(knee)
        ap = j.get(ankle)
        fp = j.get(foot)

        if hp and kp:
            cyl(hp, kp, 0.07, 0.05, grey, f"Thigh_{side}")
        if kp and ap:
            cyl(kp, ap, 0.05, 0.035, grey, f"Shin_{side}")

        # Simple foot (oriented forward from ankle)
        if ap and fp:
            d = (fp[0] - ap[0], fp[1] - ap[1], fp[2] - ap[2])
            flen = math.sqrt(d[0]**2 + d[1]**2 + d[2]**2)
            if flen > 0.01:
                box(fp, (0.035, 0.05, 0.025), grey, f"Foot_{side}")

    # --- PELVIS VOLUME ---
    if lh and rh and pelvis_p:
        pw = abs(rh[0] - lh[0]) * 0.3
        pd = abs(rh[2] - lh[2]) * 0.3 if abs(rh[2] - lh[2]) > 0.001 else pw
        ellipsoid(pelvis_p, (pw, 0.04, pd), grey, "Pelvis")


def setup_camera(azimuth, elevation, distance):
    bpy.ops.object.camera_add()
    cam = bpy.context.active_object
    az_r, el_r = math.radians(azimuth), math.radians(elevation)
    x = distance * math.cos(el_r) * math.sin(az_r)
    y = distance * math.cos(el_r) * math.cos(az_r)
    z = distance * math.sin(el_r)
    cam.location = (x, y, z + 0.3)
    cam.rotation_euler = (math.radians(90 + elevation), 0, math.radians(azimuth))
    bpy.context.scene.camera = cam
    return cam


def setup_lighting():
    bpy.ops.object.light_add(type="AREA", location=(0.5, -1.5, 2.0))
    bpy.context.active_object.data.energy = 300
    bpy.context.active_object.data.size = 1.5
    bpy.ops.object.light_add(type="AREA", location=(-0.8, 1.0, 0.5))
    bpy.context.active_object.data.energy = 150
    bpy.context.active_object.data.size = 1.5


def setup_world(bg):
    world = bpy.context.scene.world
    if world and world.node_tree and "Background" in world.node_tree.nodes:
        world.node_tree.nodes["Background"].inputs[0].default_value = (*bg, 1)


def main():
    args = parse_args()
    pose_path = args.get("pose_json", "")
    output_path = args.get("output", "output.png")
    width = int(args.get("width", "1536"))
    height = int(args.get("height", "2048"))
    bg_r = float(args.get("background_r", "240")) / 255
    bg_g = float(args.get("background_g", "240")) / 255
    bg_b = float(args.get("background_b", "240")) / 255
    transparent = bool(int(args.get("transparent", "0")))
    jpeg = bool(int(args.get("jpeg", "0")))
    jpeg_quality = int(args.get("quality", "95"))
    azimuth = float(args.get("azimuth", "0"))
    elevation = float(args.get("elevation", "15"))
    distance = float(args.get("distance", "2.5"))
    roll = float(args.get("roll", "0"))
    focal_arg = float(args.get("focal", "0"))

    # Load pose
    joints = {}
    if pose_path and os.path.exists(pose_path):
        with open(pose_path) as f:
            pose_data = json.load(f)
        joints = pose_data.get("joints", pose_data)

    # Convert to Blender coordinates: y-up, z-depth
    bl_joints = {}
    for jid, jdata in joints.items():
        if isinstance(jdata, dict):
            x, y, z = jdata.get("x", 0), jdata.get("y", 0), jdata.get("z", 0)
        elif isinstance(jdata, list) and len(jdata) >= 3:
            x, y, z = jdata[0], jdata[1], jdata[2]
        else:
            continue
        scale = 0.002
        bl_joints[jid] = (x * scale, z * scale, y * scale)

    if not bl_joints:
        print("ERROR: No joints to render")
        return

    # Build scene — ALWAYS procedural, no static mesh
    clear_scene()
    build_mannequin(bl_joints)
    cam = setup_camera(azimuth, elevation, distance)

    # Apply roll (convert degrees to Blender local Z rotation)
    if abs(roll) > 0.1:
        cam.rotation_euler.z += math.radians(roll)

    # Apply focal length if specified (>0 means passed from app)
    if focal_arg > 0:
        cam.data.lens = focal_arg

    setup_lighting()
    setup_world((bg_r, bg_g, bg_b))

    # Render
    bpy.context.scene.render.resolution_x = width
    bpy.context.scene.render.resolution_y = height
    bpy.context.scene.render.resolution_percentage = 100

    if jpeg:
        bpy.context.scene.render.image_settings.file_format = "JPEG"
        bpy.context.scene.render.image_settings.quality = jpeg_quality
        bpy.context.scene.render.image_settings.color_mode = "RGB"
    else:
        bpy.context.scene.render.image_settings.file_format = "PNG"
        if transparent:
            bpy.context.scene.render.image_settings.color_mode = "RGBA"
            bpy.context.scene.render.film_transparent = True
        else:
            bpy.context.scene.render.image_settings.color_mode = "RGB"
            bpy.context.scene.render.film_transparent = False

    bpy.context.scene.render.filepath = output_path
    bpy.ops.render.render(write_still=True)
    print(f"RENDER_OK: {output_path}")
    print(f"JOINTS_USED: {len(bl_joints)}")


if __name__ == "__main__":
    main()
