"""Low-level helpers that create mesh objects without needing the Blender UI."""

import bmesh
import bpy


def _link(film, obj, parent):
    film.collection.objects.link(obj)
    if parent is not None:
        obj.parent = parent


def empty(film, name, location=(0, 0, 0), parent=None):
    """An invisible pivot. Characters use these as joints."""
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_size = 0.1
    _link(film, obj, parent)
    obj.location = location
    return obj


def _object(film, name, bm, location, scale, rotation, mat, parent, smooth):
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    if smooth:
        for poly in mesh.polygons:
            poly.use_smooth = True
    if mat is not None:
        mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    _link(film, obj, parent)
    obj.location = location
    obj.scale = scale
    obj.rotation_euler = rotation
    return obj


def sphere(film, name, radius=1.0, location=(0, 0, 0), scale=(1, 1, 1), mat=None,
           parent=None, cut_below=None, segments=32, rings=16):
    """A smooth ball. scale stretches it into an egg/capsule shape.
    cut_below (-1..1) removes the bottom part, e.g. 0.3 keeps only a cap (hair)."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=radius)
    if cut_below is not None:
        doomed = [v for v in bm.verts if v.co.z < cut_below * radius]
        bmesh.ops.delete(bm, geom=doomed, context="VERTS")
    return _object(film, name, bm, location, scale, (0, 0, 0), mat, parent, True)


def box(film, name, size=(1, 1, 1), location=(0, 0, 0), rotation=(0, 0, 0), mat=None,
        parent=None, bevel=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= size[0]
        v.co.y *= size[1]
        v.co.z *= size[2]
    obj = _object(film, name, bm, location, (1, 1, 1), rotation, mat, parent, False)
    if bevel > 0:
        mod = obj.modifiers.new("Bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 3
        for poly in obj.data.polygons:
            poly.use_smooth = True
    return obj


def cylinder(film, name, radius=0.5, depth=1.0, location=(0, 0, 0), rotation=(0, 0, 0),
             mat=None, parent=None, top_radius=None, segments=24):
    """A cylinder standing on its base (location is the center). top_radius makes a cone."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments,
                          radius1=radius, radius2=radius if top_radius is None else top_radius,
                          depth=depth)
    obj = _object(film, name, bm, location, (1, 1, 1), rotation, mat, parent, True)
    # keep the flat caps crisp
    for poly in obj.data.polygons:
        if abs(poly.normal.z) > 0.9:
            poly.use_smooth = False
    return obj
