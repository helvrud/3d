import bpy
import bmesh
import mathutils
import math


bpy.ops.wm.read_factory_settings(use_empty=True)

# Set to millimeters
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 0.001
scene.unit_settings.use_separate = True
scene.unit_settings.length_unit = 'MILLIMETERS'


# Safely set grid scale in all 3D View areas (if in UI context)
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.overlay.grid_scale = 0.001


# ------------------------------
# Dimensions in mm (converted to meters)
# ------------------------------
leg1 = 216    # mm
leg2 = 88     # mm
height = 10   # mm

# ------------------------------
# Create a triangular prism
# ------------------------------
mesh = bpy.data.meshes.new("TrianglePrismMesh")
obj = bpy.data.objects.new("TrianglePrism", mesh)
bpy.context.collection.objects.link(obj)
bpy.context.view_layer.objects.active = obj
obj.select_set(True)

bm = bmesh.new()

# Bottom triangle (XY plane)
v1 = bm.verts.new((0, 0, 0))
v2 = bm.verts.new((leg1, 0, 0))
v3 = bm.verts.new((0, leg2, 0))

# Top triangle (shifted in Z)
v4 = bm.verts.new((0, 0, height))
v5 = bm.verts.new((leg1, 0, height))
v6 = bm.verts.new((0, leg2, height))

# Create prism faces
bm.faces.new((v1, v2, v3))        # bottom
bm.faces.new((v6, v5, v4))        # top
bm.faces.new((v1, v2, v5, v4))    # side 1
bm.faces.new((v2, v3, v6, v5))    # side 2
bm.faces.new((v3, v1, v4, v6))    # side 3

bm.to_mesh(mesh)
bm.free()






# Assume 'obj' is your original object
original = bpy.data.objects["TrianglePrism"]  # or use a variable reference

# Create a full duplicate (object + mesh data)
duplicate = original.copy()
duplicate.data = original.data.copy()  # Important: duplicate the mesh too
bpy.context.collection.objects.link(duplicate)  # Add to the scene

# Scale the copy uniformly by 0.8
scale_factor =  60 / 88
duplicate.scale = (scale_factor, scale_factor, 2.)
# delta = (A - A') / cos(alpha) + 1 + tg(alpha)
hypotenuse = (leg1**2 + leg2**2)**0.5 # hypotenuse
delta = (leg2 - leg2*scale_factor) / (1+ leg1/hypotenuse + leg2/leg1)

duplicate.location += mathutils.Vector((delta, delta, -5.))  # Shift 50 mm on X
# duplicate.scale = (1, 1, 2)


# ------------------------------
# Boolean subtraction (GUI-safe)
# ------------------------------
bpy.context.view_layer.objects.active = original
original.select_set(True)

bool_mod = original.modifiers.new(name="SubtractInner", type='BOOLEAN')
bool_mod.operation = 'DIFFERENCE'
bool_mod.object = duplicate

# Apply the modifier (requires object mode + GUI context)
if bpy.ops.object.mode_set.poll():
    bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.modifier_apply(modifier=bool_mod.name)

# Optional: remove the small object after cutout
# bpy.data.objects.remove(duplicate, do_unlink=True)


frame = original






# ------------------------------
# Create cutting cube to trim the sharp corner
# ------------------------------

cut_size = 80  # mm (adjust for how much to cut off)
cut_height = 20  # mm (taller than the prism to ensure full cut)

# Create a cube that intersects the right-angle corner (0,0)
bpy.ops.mesh.primitive_cube_add(size=1)
cut_cube = bpy.context.active_object
cut_cube.name = "CornerCutter"

# Scale the cube to desired cut size
cut_cube.scale = (cut_size, cut_size, cut_height)

# Position it to trim the triangle tip
# Slightly shift it along X and Y to overlap the corner
prism_height = height
cut_cube.location = (leg1, 0, prism_height / 2)

# ------------------------------
# Boolean subtract: cut the corner
# ------------------------------

# Make the triangle prism active again
bpy.context.view_layer.objects.active = obj
obj.select_set(True)

# Add and apply Boolean modifier
corner_mod = obj.modifiers.new(name="CutCorner", type='BOOLEAN')
corner_mod.operation = 'DIFFERENCE'
corner_mod.object = cut_cube

# Ensure Object mode and apply modifier
if bpy.ops.object.mode_set.poll():
    bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.modifier_apply(modifier=corner_mod.name)

# Optional: remove the cutter cube
bpy.data.objects.remove(cut_cube, do_unlink=True)



# ------------------------------
# Parameters for the bow groove
# ------------------------------
outer_radius = 300  # mm
inner_radius = 295  # mm
depth = prism_height * 1.2  # how deep to cut into the prism
bow_center_x = outer_radius + 2.5      # center along X (long side)
bow_center_y = leg2/2     # center along Y (short side)
bow_center_z = prism_height / 2  # mid-height of triangle
print(bow_center_x, bow_center_y, bow_center_z)
# ------------------------------
# Outer cylinder (for the groove)
# ------------------------------
bpy.ops.mesh.primitive_cylinder_add(
    vertices=128,
    radius=outer_radius,
    depth=depth,
    location=(bow_center_x, bow_center_y, bow_center_z),
    rotation=(0, 0, 0)  # Z-axis cylinder = default
)
outer_cyl = bpy.context.active_object
outer_cyl.name = "BowOuter"

# ------------------------------
# Inner cylinder (to hollow the groove)
# ------------------------------
bpy.ops.mesh.primitive_cylinder_add(
    radius=inner_radius,
    vertices=128,
    depth=depth * 1.2,
    location=(bow_center_x, bow_center_y, bow_center_z),
    rotation=(0, 0, 0)
)
inner_cyl = bpy.context.active_object
inner_cyl.name = "BowInner"

# ------------------------------
# Subtract inner from outer to make ring segment
# ------------------------------
bpy.context.view_layer.objects.active = outer_cyl
outer_cyl.select_set(True)

mod_hollow = outer_cyl.modifiers.new(name="HollowBow", type='BOOLEAN')
mod_hollow.operation = 'DIFFERENCE'
mod_hollow.object = inner_cyl

if bpy.ops.object.mode_set.poll():
    bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.modifier_apply(modifier=mod_hollow.name)
bpy.data.objects.remove(inner_cyl, do_unlink=True)




duplicate.scale = (1.01, 1.01, 2)
# duplicate.location = (1/scale_factor, 1/scale_factor, 1)
duplicate.location += mathutils.Vector((-delta*6, 0, 0))  # Shift 50 mm on X


# ------------------------------
# Intersect bow with duplicate (keep only shared part)
# ------------------------------

# Make sure 'duplicate' is active and selected
bpy.context.view_layer.objects.active = duplicate
duplicate.select_set(True)

# Ensure we are in Object Mode
if bpy.ops.object.mode_set.poll():
    bpy.ops.object.mode_set(mode='OBJECT')

# Add Boolean INTERSECT modifier
inter_mod = duplicate.modifiers.new(name="BowIntersect", type='BOOLEAN')
inter_mod.operation = 'INTERSECT'
inter_mod.object = outer_cyl

# Apply the modifier
bpy.ops.object.modifier_apply(modifier=inter_mod.name)

# Optional: remove the bow object after intersection
bpy.data.objects.remove(outer_cyl, do_unlink=True)
sector = duplicate

# ------------------------------
# Subtract the bow sector from the frame
# ------------------------------
bpy.context.view_layer.objects.active = frame
frame.select_set(True)

mod_hollow = frame.modifiers.new(name="CutTheBow", type='BOOLEAN')
mod_hollow.operation = 'DIFFERENCE'
mod_hollow.object = sector

if bpy.ops.object.mode_set.poll():
    bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.modifier_apply(modifier=mod_hollow.name)
bpy.data.objects.remove(sector, do_unlink=True)








# ------------------------------
# Add camera and light
# ------------------------------

# Delete existing camera and lights if any
for obj_ in bpy.data.objects:
    if obj_.type in {'LIGHT', 'CAMERA'}:
        bpy.data.objects.remove(obj_, do_unlink=True)

# Add a new camera
bpy.ops.object.camera_add(
    location=(300, -400, 250),  # position in mm
    rotation=(math.radians(65), 0, math.radians(45))  # slight tilt
)
cam = bpy.context.active_object
cam.name = "AutoCamera"
scene.camera = cam

# Set camera focal length for a wider view
cam.data.lens = 35  # mm

# Add a soft point light
bpy.ops.object.light_add(
    type='AREA',
    location=(200, -200, 300)
)
light = bpy.context.active_object
light.name = "AutoLight"
light.data.energy = 5000  # adjust brightness
light.data.size = 100    # soft shadow area

# Optional: Look at the object (center view)
bpy.ops.object.empty_add(type='PLAIN_AXES', location=(leg1/2, leg2/2, height/2))
focus_target = bpy.context.active_object

# Add a "Track To" constraint to the camera
track = cam.constraints.new(type='TRACK_TO')
track.target = focus_target
track.track_axis = 'TRACK_NEGATIVE_Z'
track.up_axis = 'UP_Y'




# bpy.ops.object.modifier_apply(modifier=bool_mod.name)
bpy.ops.wm.save_as_mainfile(filepath="palecha3.blend")
