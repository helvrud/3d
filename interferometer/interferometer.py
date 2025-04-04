import bpy
import bmesh
import mathutils
import math

# Reset scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# Set units to millimeters
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 0.001
scene.unit_settings.use_separate = True
scene.unit_settings.length_unit = 'MILLIMETERS'

# Dimensions in mm
leg1 = 216
leg2 = 88
height = 10
frame_thickness_ab = 9
frame_thickness_bc = 9
frame_thickness_ca = 18

# Create triangle prism
mesh = bpy.data.meshes.new("TrianglePrismMesh")
obj = bpy.data.objects.new("TrianglePrism", mesh)
bpy.context.collection.objects.link(obj)
bpy.context.view_layer.objects.active = obj
obj.select_set(True)

bm = bmesh.new()
v1 = bm.verts.new((0, 0, 0))
v2 = bm.verts.new((leg1, 0, 0))
v3 = bm.verts.new((0, leg2, 0))
v4 = bm.verts.new((0, 0, height))
v5 = bm.verts.new((leg1, 0, height))
v6 = bm.verts.new((0, leg2, height))

bm.faces.new((v1, v2, v3))
bm.faces.new((v6, v5, v4))
bm.faces.new((v1, v2, v5, v4))
bm.faces.new((v2, v3, v6, v5))
bm.faces.new((v3, v1, v4, v6))

bm.to_mesh(mesh)
bm.free()

frame = obj

# Create inner triangle prism with custom thickness per side
def create_inset_triangle_prism(thickness_ab, thickness_bc, thickness_ca, height):
    mesh = bpy.data.meshes.new("InsetPrismMesh")
    obj = bpy.data.objects.new("InsetPrism", mesh)
    bpy.context.collection.objects.link(obj)

    A = mathutils.Vector((0, 0))
    B = mathutils.Vector((leg1, 0))
    C = mathutils.Vector((0, leg2))

    def offset(p1, p2, d):
        edge = (p2 - p1).normalized()
        normal = mathutils.Vector((-edge.y, edge.x))
        return p1 + normal * d, p2 + normal * d

    ab1, ab2 = offset(A, B, thickness_ab)
    bc1, bc2 = offset(B, C, thickness_bc)
    ca1, ca2 = offset(C, A, thickness_ca)

    def intersect(p1, p2, p3, p4):
        a1 = p2 - p1
        a2 = p4 - p3
        b = p3 - p1
        denom = a1.cross(a2)
        if abs(denom) < 1e-6:
            return p1
        t = b.cross(a2) / denom
        return p1 + a1 * t

    i1 = intersect(ab1, ab2, ca2, ca1)
    i2 = intersect(ab2, ab1, bc1, bc2)
    i3 = intersect(ca1, ca2, bc2, bc1)

    bm = bmesh.new()
    v1 = bm.verts.new((i1.x, i1.y, 0))
    v2 = bm.verts.new((i2.x, i2.y, 0))
    v3 = bm.verts.new((i3.x, i3.y, 0))
    v4 = bm.verts.new((i1.x, i1.y, height))
    v5 = bm.verts.new((i2.x, i2.y, height))
    v6 = bm.verts.new((i3.x, i3.y, height))

    bm.faces.new((v1, v2, v3))
    bm.faces.new((v6, v5, v4))
    bm.faces.new((v1, v2, v5, v4))
    bm.faces.new((v2, v3, v6, v5))
    bm.faces.new((v3, v1, v4, v6))

    bm.to_mesh(mesh)
    bm.free()
    return obj

inner_prism = create_inset_triangle_prism(frame_thickness_ab, frame_thickness_bc, frame_thickness_ca, height)

# Subtract inner prism from frame
def apply_modifier_background(obj, modifier_name):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mod = obj.modifiers.get(modifier_name)
    if mod:
        obj_eval = obj.evaluated_get(depsgraph)
        new_mesh = bpy.data.meshes.new_from_object(obj_eval)
        obj.modifiers.remove(mod)
        obj.data = new_mesh

mod = frame.modifiers.new(name="SubtractInner", type='BOOLEAN')
mod.operation = 'DIFFERENCE'
mod.object = inner_prism
apply_modifier_background(frame, "SubtractInner")
bpy.data.objects.remove(inner_prism, do_unlink=True)

# Corner cut cube
cut_size = 80
cut_height = 20
bpy.ops.mesh.primitive_cube_add(size=1)
cut_cube = bpy.context.selected_objects[0]
cut_cube.name = "CornerCutter"
cut_cube.scale = (cut_size, cut_size, cut_height)
cut_cube.location = (leg1, 0, height / 2)

mod = frame.modifiers.new(name="CutCorner", type='BOOLEAN')
mod.operation = 'DIFFERENCE'
mod.object = cut_cube
apply_modifier_background(frame, "CutCorner")
bpy.data.objects.remove(cut_cube, do_unlink=True)

# Create bow groove
outer_radius = 300
inner_radius = 295
arc_angle_deg = 10
arc_angle_rad = math.radians(arc_angle_deg)
depth = height * 1.2
bow_center_x = outer_radius + 2.5
bow_center_y = leg2 / 2
bow_center_z = height / 2

# Create outer arc mesh
bpy.ops.mesh.primitive_cylinder_add(vertices=128, radius=outer_radius, depth=depth,
    location=(bow_center_x, bow_center_y, bow_center_z))
outer_cyl = bpy.context.selected_objects[0]
outer_cyl.name = "BowOuter"

# Trim cylinder to arc shape
bpy.ops.mesh.primitive_cube_add(size=1)
arc_cutter = bpy.context.selected_objects[0]
arc_cutter.name = "ArcCutter"
arc_cutter.scale = (outer_radius * 2, outer_radius * 2, depth * 2)
arc_cutter.location = (bow_center_x - outer_radius * math.cos(arc_angle_rad / 2), bow_center_y, bow_center_z)
arc_cutter.rotation_euler[2] = arc_angle_rad / 2

mod = outer_cyl.modifiers.new(name="ArcTrim", type='BOOLEAN')
mod.operation = 'INTERSECT'
mod.object = arc_cutter
apply_modifier_background(outer_cyl, "ArcTrim")
bpy.data.objects.remove(arc_cutter, do_unlink=True)

# Inner cylinder for hollowing
bpy.ops.mesh.primitive_cylinder_add(vertices=128, radius=inner_radius, depth=depth * 1.2,
    location=(bow_center_x, bow_center_y, bow_center_z))
inner_cyl = bpy.context.selected_objects[0]
inner_cyl.name = "BowInner"

mod = outer_cyl.modifiers.new(name="HollowBow", type='BOOLEAN')
mod.operation = 'DIFFERENCE'
mod.object = inner_cyl
apply_modifier_background(outer_cyl, "HollowBow")
bpy.data.objects.remove(inner_cyl, do_unlink=True)
sector = outer_cyl.copy()
sector.data = outer_cyl.data.copy()
bpy.context.collection.objects.link(sector)

mod = sector.modifiers.new(name="BowIntersect", type='BOOLEAN')
mod.operation = 'INTERSECT'
mod.object = frame
apply_modifier_background(sector, "BowIntersect")
bpy.data.objects.remove(outer_cyl, do_unlink=True)

# Subtract sector from frame
mod = frame.modifiers.new(name="CutTheBow", type='BOOLEAN')
mod.operation = 'DIFFERENCE'
mod.object = sector
apply_modifier_background(frame, "CutTheBow")
bpy.data.objects.remove(sector, do_unlink=True)

# Save result
bpy.ops.wm.save_as_mainfile(filepath="palecha3.blend")
