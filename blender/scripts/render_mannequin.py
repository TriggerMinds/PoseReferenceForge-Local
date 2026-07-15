"""
Blender Python script — procedural joint-driven pose mannequin.

Features:
- Explicit world creation with configurable background
- Aimed studio lighting toward the mannequin
- Look-at camera with proper focal-length conversion (px → mm)
- Profile-aware rendering (clean, transparent, depth, silhouette, structural)
- Automatic framing with safe margins
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
    for world in bpy.data.worlds:
        bpy.data.worlds.remove(world)


def make_world(bg_color, strength=1.0):
    world = bpy.data.worlds.new("RenderWorld")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg is None:
        bg = world.node_tree.nodes.new(type="ShaderNodeBackground")
    bg.inputs["Color"].default_value = (*bg_color, 1)
    bg.inputs["Strength"].default_value = strength
    out = world.node_tree.nodes.get("World Output")
    if out is None:
        out = world.node_tree.nodes.new(type="ShaderNodeOutputWorld")
    world.node_tree.links.new(bg.outputs["Background"], out.inputs["Surface"])


def make_mat(name, color, rough=0.6, alpha=1.0, emission=0.0):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    n = mat.node_tree.nodes
    n.clear()
    p = n.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (*color, alpha)
    p.inputs["Roughness"].default_value = rough
    if emission > 0:
        p.inputs["Emission Strength"].default_value = emission
        p.inputs["Emission Color"].default_value = (*color, 1)
    out = n.new("ShaderNodeOutputMaterial")
    mat.node_tree.links.new(p.outputs["BSDF"], out.inputs["Surface"])
    if alpha < 1.0 or alpha > 1.0:
        mat.blend_method = "BLEND"
    return mat


def cyl(p1, p2, r1, r2, color, name, alpha=1.0, emission=0.0):
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
    mat = make_mat(f"{name}_mat", color, alpha=alpha, emission=emission)
    obj.data.materials.append(mat)
    return obj


def sphere(pos, radius, color, name, alpha=1.0):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=pos)
    obj = bpy.context.active_object
    obj.name = name
    mat = make_mat(f"{name}_mat", color, alpha=alpha)
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


def build_mannequin(j, grey=(0.65, 0.62, 0.60), dark=(0.50, 0.48, 0.45),
                    light_grey=(0.75, 0.72, 0.70), emission=0.0, alpha=1.0):
    neck_p = j.get("neck")
    pelvis_p = j.get("pelvis")
    ls = j.get("left_shoulder")
    rs = j.get("right_shoulder")
    lh = j.get("left_hip")
    rh = j.get("right_hip")
    head_p = j.get("head")

    if neck_p and pelvis_p:
        shoulder_w = abs(ls[0] - rs[0]) * 0.5 if ls and rs else 0.2
        hip_w = abs(lh[0] - rh[0]) * 0.5 if lh and rh else 0.18
        cyl(neck_p, pelvis_p, shoulder_w, hip_w, grey, "Torso", alpha, emission)
    if neck_p and head_p:
        cyl(neck_p, head_p, 0.06, 0.04, grey, "Neck", alpha, emission)
    if head_p:
        ellipsoid(head_p, (0.10, 0.08, 0.10), light_grey, "Head")

    for side, shoulder, elbow, wrist, hand in [
        ("L", "left_shoulder", "left_elbow", "left_wrist", "left_hand"),
        ("R", "right_shoulder", "right_elbow", "right_wrist", "right_hand"),
    ]:
        sp = j.get(shoulder); ep = j.get(elbow); wp = j.get(wrist); hp = j.get(hand)
        if sp and ep:
            cyl(sp, ep, 0.055, 0.04, grey, f"UpperArm_{side}", alpha, emission)
        if ep and wp:
            cyl(ep, wp, 0.04, 0.03, grey, f"Forearm_{side}", alpha, emission)
        if wp and hp:
            d = (hp[0]-wp[0], hp[1]-wp[1], hp[2]-wp[2])
            hlen = math.sqrt(d[0]**2 + d[1]**2 + d[2]**2)
            if hlen > 0.01:
                box(hp, (0.03, 0.04, 0.015), grey, f"Hand_{side}")

    for side, hip, knee, ankle, foot in [
        ("L", "left_hip", "left_knee", "left_ankle", "left_foot"),
        ("R", "right_hip", "right_knee", "right_ankle", "right_foot"),
    ]:
        hp = j.get(hip); kp = j.get(knee); ap = j.get(ankle); fp = j.get(foot)
        if hp and kp:
            cyl(hp, kp, 0.07, 0.05, grey, f"Thigh_{side}", alpha, emission)
        if kp and ap:
            cyl(kp, ap, 0.05, 0.035, grey, f"Shin_{side}", alpha, emission)
        if ap and fp:
            d = (fp[0]-ap[0], fp[1]-ap[1], fp[2]-ap[2])
            flen = math.sqrt(d[0]**2 + d[1]**2 + d[2]**2)
            if flen > 0.01:
                box(fp, (0.035, 0.05, 0.025), grey, f"Foot_{side}")

    if lh and rh and pelvis_p:
        pw = abs(rh[0]-lh[0]) * 0.3
        pd = abs(rh[2]-lh[2]) * 0.3 if abs(rh[2]-lh[2]) > 0.001 else pw
        ellipsoid(pelvis_p, (pw, 0.04, pd), grey, "Pelvis")


def compute_bbox(joints):
    xs, ys, zs = [], [], []
    for p in joints.values():
        xs.append(p[0]); ys.append(p[1]); zs.append(p[2])
    if not xs:
        return (0, 0, 0), 1.0
    center = ((max(xs)+min(xs))/2, (max(ys)+min(ys))/2, (max(zs)+min(zs))/2)
    size = max(max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs), 0.5)
    return center, size


def setup_camera_lookat(azimuth, elevation, roll, focal_px, source_w, source_h,
                        target_center, joints, shift_x=0, shift_y=0, sensor_mm=36.0):
    az_r = math.radians(azimuth)
    el_r = math.radians(elevation)

    # Convert focal px to Blender lens mm
    blender_lens = focal_px * sensor_mm / max(source_w, 1)

    # Distance based on actual joint bounding box size
    xs = [p[0] for p in joints.values()]
    ys = [p[1] for p in joints.values()]
    zs = [p[2] for p in joints.values()]
    bbox_size = max(max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs), 0.3)
    distance = max(bbox_size * 4.5, 2.5)

    # Spherical camera position
    cx = distance * math.cos(el_r) * math.sin(az_r)
    cy = distance * math.cos(el_r) * math.cos(az_r)
    cz = distance * math.sin(el_r)

    bpy.ops.object.camera_add()
    cam = bpy.context.active_object
    cam.name = "RenderCamera"
    bpy.context.scene.camera = cam

    cam.location = (cx, cy, cz + target_center[2])
    cam.data.lens = blender_lens
    cam.data.sensor_width = sensor_mm
    cam.data.shift_x = shift_x / max(source_w, 1)
    cam.data.shift_y = shift_y / max(source_h, 1)

    # Look at target center
    direction = Vector(target_center) - cam.location
    rot = direction.to_track_quat("-Z", "Y")
    cam.rotation_euler = rot.to_euler()

    # Apply roll around view direction
    if abs(roll) > 0.1:
        cam.rotation_euler.z += math.radians(roll)

    # Clipping
    cam.data.clip_start = 0.01
    cam.data.clip_end = 100.0

    return cam, blender_lens, distance


def setup_lighting(target_center):
    for label, loc, energy in [
        ("Key", (0.8, -1.5, 2.0), 400),
        ("Fill", (-0.6, 1.0, 0.5), 200),
        ("Rim", (0.0, 1.5, 1.0), 150),
    ]:
        bpy.ops.object.light_add(type="AREA", location=loc)
        light = bpy.context.active_object
        light.name = f"Light_{label}"
        light.data.energy = energy
        light.data.size = 2.0
        direction = Vector(target_center) - Vector(loc)
        light.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def setup_low_world(bg_color=(0.15, 0.15, 0.15)):
    make_world(bg_color, strength=0.3)


def main():
    args = parse_args()
    pose_path = args.get("pose_json", "")
    output_path = args.get("output", "output.png")
    width = int(args.get("width", "1536"))
    height = int(args.get("height", "2048"))
    bg_r = float(args.get("background_r", "0.94"))
    bg_g = float(args.get("background_g", "0.94"))
    bg_b = float(args.get("background_b", "0.94"))
    transparent = bool(int(args.get("transparent", "0")))
    jpeg = bool(int(args.get("jpeg", "0")))
    jpeg_quality = int(args.get("quality", "95"))
    azimuth = float(args.get("azimuth", "0"))
    elevation = float(args.get("elevation", "15"))
    roll = float(args.get("roll", "0"))
    focal_px = float(args.get("focal", "1500"))
    distance_arg = float(args.get("distance", "0"))
    source_w = int(args.get("source_w", str(width)))
    source_h = int(args.get("source_h", str(height)))
    shift_x = float(args.get("shift_x", "0"))
    shift_y = float(args.get("shift_y", "0"))
    profile = args.get("profile", "source_matched_clean")
    sensor_mm = 36.0

    # Load pose
    joints = {}
    if pose_path and os.path.exists(pose_path):
        with open(pose_path) as f:
            pose_data = json.load(f)
        joints = pose_data.get("joints", pose_data)

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

    target_center, _ = compute_bbox(bl_joints)

    clear_scene()

    # Determine material based on profile
    if profile == "silhouette":
        mannequin_color = (0.05, 0.05, 0.05)
        bg_color = (1, 1, 1)
        world_strength = 0.5
        emission_val = 0
    elif profile == "structural":
        mannequin_color = (0.55, 0.50, 0.45)
        bg_color = (bg_r, bg_g, bg_b)
        world_strength = 1.0
        emission_val = 0
    elif profile == "depth_readable":
        mannequin_color = (0.70, 0.55, 0.35)
        bg_color = (0.78, 0.78, 0.82)
        world_strength = 0.5
        emission_val = 0
    else:
        mannequin_color = (0.65, 0.62, 0.60)
        bg_color = (bg_r, bg_g, bg_b)
        world_strength = 1.0
        emission_val = 0

    build_mannequin(bl_joints, grey=mannequin_color, emission=emission_val,
                    alpha=0.0 if transparent else 1.0)

    # Setup camera with look-at and proper focal conversion
    cam, blender_lens, distance = setup_camera_lookat(
        azimuth, elevation, roll, focal_px,
        source_w or width, source_h or height,
        target_center, bl_joints, shift_x, shift_y, sensor_mm,
    )

    # Lighting
    if profile == "silhouette":
        make_world(bg_color, strength=0.5)
    elif profile == "structural":
        setup_lighting(target_center)
        setup_low_world(bg_color)
    else:
        setup_lighting(target_center)
        make_world(bg_color, world_strength)

    # Render
    bpy.context.scene.render.resolution_x = width
    bpy.context.scene.render.resolution_y = height
    bpy.context.scene.render.resolution_percentage = 100

    if transparent:
        bpy.context.scene.render.image_settings.color_mode = "RGBA"
        bpy.context.scene.render.image_settings.file_format = "PNG"
        bpy.context.scene.render.film_transparent = True
    elif jpeg:
        bpy.context.scene.render.image_settings.file_format = "JPEG"
        bpy.context.scene.render.image_settings.quality = jpeg_quality
        bpy.context.scene.render.image_settings.color_mode = "RGB"
        bpy.context.scene.render.film_transparent = False
    else:
        bpy.context.scene.render.image_settings.file_format = "PNG"
        bpy.context.scene.render.image_settings.color_mode = "RGB"
        bpy.context.scene.render.film_transparent = False

    bpy.context.scene.render.filepath = output_path
    bpy.ops.render.render(write_still=True)
    print(f"RENDER_OK: {output_path}")
    print(f"BLENDER_LENS: {blender_lens:.2f}")
    print(f"DISTANCE: {distance:.2f}")
    print(f"PROFILE: {profile}")


if __name__ == "__main__":
    main()
