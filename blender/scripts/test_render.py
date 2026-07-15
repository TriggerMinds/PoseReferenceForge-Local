import bpy
import math
import sys

output_path = sys.argv[-1] if len(sys.argv) > 1 and sys.argv[-1].endswith('.png') else 'C:/Users/gewoo/New folder (124)/evidence/renders/blender_test.png'

# Clear scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# Camera
bpy.ops.object.camera_add(location=(0, -2.5, 0.5))
cam = bpy.context.active_object
cam.rotation_euler = (math.radians(10), 0, 0)
bpy.context.scene.camera = cam

# Light
bpy.ops.object.light_add(type='AREA', location=(1, -2, 3))
bpy.context.active_object.data.energy = 300

# Sphere
bpy.ops.mesh.primitive_uv_sphere_add(location=(0, 0, 0), radius=0.3)

# Render settings
bpy.context.scene.render.resolution_x = 256
bpy.context.scene.render.resolution_y = 256
bpy.context.scene.render.resolution_percentage = 100
bpy.context.scene.render.image_settings.file_format = 'PNG'
bpy.context.scene.render.filepath = output_path

# Background
world = bpy.context.scene.world
if world:
    world.use_nodes = True
    if world.node_tree and 'Background' in world.node_tree.nodes:
        bg = world.node_tree.nodes['Background']
        bg.inputs[0].default_value = (0.9, 0.9, 0.9, 1)

# Render
bpy.ops.render.render(write_still=True)
print(f'RENDER_OK: {output_path}')
